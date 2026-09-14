"""Cost-oriented AgentMeter helpers."""

from __future__ import annotations

from typing import Any, Iterable

from .agentmeter import as_records, num, passed, reward, total_cost


DEFAULT_COST_BUDGETS = (0.05, 0.10, 0.25, 0.50, 1.00)


def cost_aubqc(rows: Any, budgets: Iterable[float] = DEFAULT_COST_BUDGETS, denom: int | None = None) -> float:
    records = as_records(rows)
    d = len(records) if denom is None else max(int(denom), 0)
    if not d:
        return 0.0
    vals = []
    for budget in budgets:
        vals.append(sum(reward(row) for row in records if reward(row) > 0 and total_cost(row) <= budget) / d)
    return sum(vals) / len(vals) if vals else 0.0


def expensive_failure_rate(rows: Any, tau_cny: float = 1.0, denom: int | None = None) -> float:
    records = as_records(rows)
    d = len(records) if denom is None else max(int(denom), 0)
    if not d:
        return 0.0
    return sum(1 for row in records if not passed(row) and num(row.get("reward")) <= 0 and total_cost(row) > tau_cny) / d


def cost_aware_score(rows: Any, budgets: Iterable[float] = DEFAULT_COST_BUDGETS, tau_cny: float = 1.0) -> float:
    return cost_aubqc(rows, budgets=budgets) * (1.0 - expensive_failure_rate(rows, tau_cny=tau_cny))

