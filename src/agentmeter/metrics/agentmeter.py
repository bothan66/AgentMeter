"""Pure Python AgentMeter metrics.

The functions accept either a list of dictionaries or a pandas DataFrame. Pandas
is never required at import time.
"""

from __future__ import annotations

from collections import defaultdict
from math import sqrt
from statistics import median
from typing import Any, Iterable

DEFAULT_TOKEN_BUDGETS = (100_000, 250_000, 500_000, 1_000_000, 2_000_000)
DEFAULT_IFR_TAU = 1_000_000


def as_records(rows: Any) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if hasattr(rows, "to_dict"):
        return list(rows.to_dict("records"))
    return [dict(row) for row in rows]


def num(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "passed", "success"}


def passed(row: dict[str, Any]) -> bool:
    if "passed" in row:
        return truthy(row["passed"])
    if "pass" in row:
        return truthy(row["pass"])
    if "success" in row:
        return truthy(row["success"])
    return num(row.get("reward"), 0.0) > 0


def reward(row: dict[str, Any]) -> float:
    if "reward" in row:
        return num(row.get("reward"))
    return 1.0 if passed(row) else 0.0


def total_tokens(row: dict[str, Any]) -> float:
    if "total_tokens" in row:
        return num(row.get("total_tokens"))
    return num(row.get("input_tokens")) + num(row.get("output_tokens"))


def total_cost(row: dict[str, Any]) -> float:
    for key in ("total_cost_cny", "cost_cny", "cost", "billable_cny"):
        if key in row:
            return num(row.get(key))
    return 0.0


def denominator(records: list[dict[str, Any]], denom: int | None = None) -> int:
    if denom is not None:
        return max(int(denom), 0)
    return len(records)


def pass_rate(rows: Any, denom: int | None = None) -> float:
    records = as_records(rows)
    d = denominator(records, denom)
    return sum(1 for row in records if passed(row)) / d if d else 0.0


def tokens_per_pass(rows: Any) -> float | None:
    records = as_records(rows)
    passes = sum(1 for row in records if passed(row))
    return sum(total_tokens(row) for row in records) / passes if passes else None


def cost_per_pass(rows: Any) -> float | None:
    records = as_records(rows)
    passes = sum(1 for row in records if passed(row))
    return sum(total_cost(row) for row in records) / passes if passes else None


def aubqc(rows: Any, budgets: Iterable[int] = DEFAULT_TOKEN_BUDGETS, denom: int | None = None) -> float:
    records = as_records(rows)
    d = denominator(records, denom)
    if not d:
        return 0.0
    values = []
    for budget in budgets:
        quality = sum(reward(row) for row in records if reward(row) > 0 and total_tokens(row) <= budget)
        values.append(quality / d)
    return sum(values) / len(values) if values else 0.0


def ifr_at_budget(rows: Any, tau: int = DEFAULT_IFR_TAU, denom: int | None = None) -> float:
    records = as_records(rows)
    d = denominator(records, denom)
    if not d:
        return 0.0
    inefficient_failures = 0
    for row in records:
        failed = not passed(row) and reward(row) <= 0
        if failed and total_tokens(row) > tau:
            inefficient_failures += 1
    return inefficient_failures / d


def agentmeter_score(
    rows: Any,
    budgets: Iterable[int] = DEFAULT_TOKEN_BUDGETS,
    ifr_tau: int = DEFAULT_IFR_TAU,
    denom: int | None = None,
) -> float:
    return aubqc(rows, budgets=budgets, denom=denom) * (1.0 - ifr_at_budget(rows, tau=ifr_tau, denom=denom))


def pmt(rows: Any) -> float | None:
    records = as_records(rows)
    tokens = sum(total_tokens(row) for row in records)
    passes = sum(1 for row in records if passed(row))
    return passes / (tokens / 1_000_000) if tokens else None


def summarize_agentmeter(
    rows: Any,
    group_by: tuple[str, ...] = ("model", "cli"),
    budgets: Iterable[int] = DEFAULT_TOKEN_BUDGETS,
    ifr_tau: int = DEFAULT_IFR_TAU,
    denom: int | None = None,
) -> list[dict[str, Any]]:
    records = as_records(rows)
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    if group_by:
        for row in records:
            groups[tuple(row.get(key, "") for key in group_by)].append(row)
    else:
        groups[()] = records

    summaries: list[dict[str, Any]] = []
    for key, subset in sorted(groups.items()):
        d = denom if denom is not None else len(subset)
        pass_count = sum(1 for row in subset if passed(row))
        tokens = sum(total_tokens(row) for row in subset)
        costs = sum(total_cost(row) for row in subset)
        turns = [num(row.get("turns")) for row in subset if row.get("turns") not in ("", None)]
        out = {name: value for name, value in zip(group_by, key)}
        out.update(
            {
                "tasks": d,
                "pass_count": pass_count,
                "pass_rate": pass_count / d if d else 0.0,
                "total_tokens": tokens,
                "total_cost_cny": costs,
                "tokens_per_pass": tokens / pass_count if pass_count else None,
                "cost_per_pass": costs / pass_count if pass_count else None,
                "pmt": pass_count / (tokens / 1_000_000) if tokens else None,
                "aubqc": aubqc(subset, budgets=budgets, denom=d),
                "ifr_at_1m": ifr_at_budget(subset, tau=ifr_tau, denom=d),
                "agentmeter_score": agentmeter_score(subset, budgets=budgets, ifr_tau=ifr_tau, denom=d),
                "median_turns": median(turns) if turns else None,
            }
        )
        summaries.append(out)
    return summaries


def population_std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / len(values))

