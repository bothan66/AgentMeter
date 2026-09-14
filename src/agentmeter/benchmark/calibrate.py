"""Calibration reports for generated tasks."""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any

from agentmeter.metrics.agentmeter import as_records, num, passed
from agentmeter.metrics.cli_sensitivity import compute_cli_sensitivity


def calibrate_tasks(rows: Any) -> list[dict[str, Any]]:
    records = as_records(rows)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_task[str(row.get("task_id", ""))].append(row)
    reports: list[dict[str, Any]] = []
    for task_id, task_rows in sorted(by_task.items()):
        successes = [row for row in task_rows if passed(row)]
        scored = [(str(row.get("cli", "")), num(row.get("score"))) for row in task_rows]
        best_cli = max(scored, key=lambda x: x[1])[0] if scored else ""
        worst_cli = min(scored, key=lambda x: x[1])[0] if scored else ""
        success_tokens = [num(row.get("total_tokens")) for row in successes if num(row.get("total_tokens")) > 0]
        scores = [num(row.get("score")) for row in task_rows]
        token_values = [num(row.get("total_tokens")) for row in task_rows if num(row.get("total_tokens")) > 0]
        sensitivity = compute_cli_sensitivity(task_rows)[0]["cli_sensitivity"] if task_rows else 0.0
        pass_count = len(successes)
        keep = pass_count > 0 and max(scores or [0]) > 0
        reason = "has at least one passing CLI" if keep else "drop: no public toy success"
        reports.append(
            {
                "task_id": task_id,
                "task_type": task_rows[0].get("task_type", ""),
                "difficulty": task_rows[0].get("difficulty", ""),
                "pass_count": pass_count,
                "best_cli": best_cli,
                "worst_cli": worst_cli,
                "min_tokens_success": min(success_tokens) if success_tokens else "",
                "median_tokens_success": median(success_tokens) if success_tokens else "",
                "token_gap": max(token_values) - min(token_values) if token_values else 0,
                "score_gap": max(scores) - min(scores) if scores else 0,
                "cli_sensitivity": sensitivity,
                "keep_or_drop": "keep" if keep else "drop",
                "reason": reason,
            }
        )
    return reports

