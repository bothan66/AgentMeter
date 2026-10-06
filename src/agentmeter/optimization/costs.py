"""Read recorded execution costs without estimating charges from token counts."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def _missing_cost(reason: str, *, source: str = "") -> dict[str, Any]:
    return {
        "available": False,
        "billable_cost_usd": None,
        "billable_cost_cny": None,
        "cost_currency": None,
        "cost_source": source,
        "reason": reason,
    }


def _recorded_amount(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("Recorded cost must be a finite nonnegative number")
    amount = float(value)
    if not math.isfinite(amount) or amount < 0:
        raise ValueError("Recorded cost must be a finite nonnegative number")
    return amount


def cost_summary_from_mapping(data: Mapping[str, Any], *, source: str = "record") -> dict[str, Any]:
    """Read currency-labelled totals from a cost file, runner summary, or Harbor result.

    Explicit zero is a recorded cost. Missing totals remain None. USD and CNY
    stay separate, even when both are supplied; no exchange rate is assumed.
    """
    containers = [(source, data)]
    for name in ("agent_result", "summary", "final_metrics"):
        nested = data.get(name)
        if isinstance(nested, Mapping):
            containers.append((f"{source}.{name}", nested))

    for container_source, container in containers:
        amounts: dict[str, float | None] = {"usd": None, "cny": None}
        amount_sources = []
        for currency in amounts:
            for key in (f"cost_{currency}", f"billable_cost_{currency}", f"total_cost_{currency}"):
                value = container.get(key)
                if isinstance(value, Mapping):
                    value = value.get("total")
                if value is None:
                    continue
                try:
                    amounts[currency] = _recorded_amount(value)
                except (TypeError, ValueError, OverflowError):
                    return _missing_cost(
                        "invalid_recorded_cost", source=f"{container_source}.{key}"
                    )
                amount_sources.append(f"{container_source}.{key}")
                break
        if all(amount is None for amount in amounts.values()):
            continue
        tokens = container.get("tokens")
        tokens = tokens if isinstance(tokens, Mapping) else {}
        return {
            "available": True,
            "billable_cost_usd": amounts["usd"],
            "billable_cost_cny": amounts["cny"],
            "cost_currency": "USD" if amounts["usd"] is not None else "CNY",
            "cost_source": ";".join(amount_sources),
            "input_pure_tokens": tokens.get("input_pure"),
            "cache_creation_tokens": tokens.get("cache_creation"),
            "cache_hit_tokens": tokens.get("cache_hit", tokens.get("cache_hit_observed")),
            "output_tokens": tokens.get("output"),
            "input_total_tokens": tokens.get("input_total"),
        }
    return _missing_cost("no_recorded_cost", source=source)


def load_cost_summary(path: Path | None) -> dict[str, Any]:
    """Prefer a trial's cost.json, then explicit totals recorded with its result.

    Token-only records do not establish a monetary cost. A malformed cost.json
    is reported as invalid instead of silently substituting another estimate.
    """
    if path is None or not path.exists():
        return _missing_cost("missing_result")
    trial_dir = path if path.is_dir() else path.parent
    if path.name == "trajectory.json" and path.parent.name == "agent":
        trial_dir = path.parent.parent
    cost_path = trial_dir / "cost.json"
    candidates = [cost_path]
    if path.is_file() and path.suffix.lower() == ".json":
        candidates.append(path)
    candidates.extend(
        trial_dir / name for name in ("result.json", "summary.json", "task_result.json")
    )
    missing = _missing_cost("no_recorded_cost")
    for candidate in dict.fromkeys(candidates):
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(data, Mapping):
                raise ValueError("Expected a JSON object")
            summary = cost_summary_from_mapping(data, source=candidate.name)
        except (OSError, ValueError):
            summary = _missing_cost("invalid_cost_record", source=candidate.name)
        summary["cost_path"] = str(candidate)
        if summary["available"] or summary.get("reason") != "no_recorded_cost":
            return summary
        if candidate == cost_path:
            return summary
        missing = summary
    return missing


def comparable_costs(
    baseline: Mapping[str, Any], current: Mapping[str, Any]
) -> tuple[float | None, float | None, str | None]:
    """Return recorded totals in a common currency, preferring USD when available."""
    for currency in ("USD", "CNY"):
        field = f"billable_cost_{currency.lower()}"
        baseline_amount = baseline.get(field)
        current_amount = current.get(field)
        if baseline_amount is not None and current_amount is not None:
            return float(baseline_amount), float(current_amount), currency
    return None, None, None
