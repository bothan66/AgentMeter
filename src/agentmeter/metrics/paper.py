"""Manuscript AMS: USD budgets, zero-reward EFR, equal-stratum mean.

Input rows represent one evaluated configuration/condition and contain
task_id, stratum (Easy/Medium/Hard), reward, and cost_usd. Repeated runs must
be aggregated under an explicitly chosen protocol before calling this API.
"""

import math
from collections.abc import Iterable, Mapping
from typing import Any

CNY_TO_USD = 0.1471


def paper_ams(rows: Iterable[Mapping[str, Any]], calibration: Mapping[str, Any]) -> dict[str, Any]:
    """Score one condition with the manuscript's fixed USD calibration.

    For each difficulty stratum, combine mean task quality (TQ) with mean
    quality across the calibrated cost budgets (AUBQC), then discount by
    expensive zero-reward failures (EFR). AMS is the equal-stratum mean,
    not a task-weighted average. Output field names match the paper tables.
    """
    rows = list(rows)
    alpha = float(calibration["alpha"])
    if not 0 <= alpha <= 1:
        raise ValueError("alpha must be in [0, 1]")
    if calibration["currency"] != "USD":
        raise ValueError("Paper AMS requires USD")
    observations_by_stratum: dict[str, list[tuple[float, float]]] = {
        stratum: [] for stratum in calibration["strata"]
    }
    seen_tasks = set()
    for row in rows:
        task_id = row["task_id"]
        if task_id in seen_tasks:
            raise ValueError("Duplicate task: supply one configuration/condition at a time")
        seen_tasks.add(task_id)
        stratum = row["stratum"]
        if stratum not in observations_by_stratum:
            raise ValueError(f"Unknown stratum: {stratum}")
        reward, cost = float(row["reward"]), float(row["cost_usd"])
        if not math.isfinite(reward) or not 0 <= reward <= 1:
            raise ValueError("reward must be finite and in [0, 1]")
        if not math.isfinite(cost) or cost < 0:
            raise ValueError("cost_usd must be finite and nonnegative")
        observations_by_stratum[stratum].append((reward, cost))
    stratum_scores = {}
    for stratum, observations in observations_by_stratum.items():
        if not observations:
            raise ValueError(f"Missing stratum: {stratum}; do not silently change macro weights")
        stratum_calibration = calibration["strata"][stratum]
        budgets = [float(budget) for budget in stratum_calibration["budgets_usd"]]
        failure_cost_threshold = float(stratum_calibration["zero_reward_threshold_usd"])
        if not budgets or any(not math.isfinite(budget) or budget < 0 for budget in budgets):
            raise ValueError("budgets must be finite and nonnegative")
        if not math.isfinite(failure_cost_threshold) or failure_cost_threshold < 0:
            raise ValueError("threshold must be finite and nonnegative")
        task_count = len(observations)
        task_quality = sum(reward for reward, _ in observations) / task_count
        budgeted_quality = sum(
            sum(reward for reward, cost in observations if cost <= budget) / task_count
            for budget in budgets
        ) / len(budgets)
        expensive_failure_rate = (
            sum(reward == 0 and cost > failure_cost_threshold for reward, cost in observations)
            / task_count
        )
        score = (alpha * task_quality + (1 - alpha) * budgeted_quality) * (
            1 - expensive_failure_rate
        )
        stratum_scores[stratum] = dict(
            n=task_count,
            TQ=task_quality,
            AUBQC=budgeted_quality,
            EFR=expensive_failure_rate,
            AMS=score,
        )
    return dict(
        AMS=sum(scores["AMS"] for scores in stratum_scores.values()) / len(stratum_scores),
        strata=stratum_scores,
        calibration_precision=calibration.get("precision", "unspecified"),
    )
