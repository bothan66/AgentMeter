"""Reference trace selection for public summaries."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from agentmeter.metrics.agentmeter import as_records, passed, total_tokens


def select_reference_trace(rows: Any) -> list[dict[str, Any]]:
    records = [row for row in as_records(rows) if passed(row)]
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_task[str(row.get("task_id", ""))].append(row)
    selected: list[dict[str, Any]] = []
    for task_id, task_rows in sorted(by_task.items()):
        best = min(task_rows, key=total_tokens)
        selected.append(
            {
                "task_id": task_id,
                "reference_model": best.get("model", ""),
                "reference_cli": best.get("cli", ""),
                "reference_tokens": int(total_tokens(best)),
                "reference_turns": int(best.get("turns") or 0),
                "reference_tool_calls": int(best.get("tool_calls") or 0),
                "reference_modified_files": int(best.get("modified_files") or 0),
            }
        )
    return selected

