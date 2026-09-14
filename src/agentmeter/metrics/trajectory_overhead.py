"""Reference trajectory overhead metrics."""

from __future__ import annotations

from typing import Any

from .agentmeter import as_records, num, passed, total_tokens


def _ratio(actual: Any, reference: Any) -> float | None:
    ref = num(reference)
    if ref <= 0:
        return None
    return num(actual) / ref


def compute_trajectory_overhead(rows: Any, references: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    records = as_records(rows)
    references = references or {}
    out: list[dict[str, Any]] = []
    for row in records:
        task_id = str(row.get("task_id", ""))
        ref = references.get(task_id, {})
        success = passed(row)
        result = {
            "task_id": task_id,
            "model": row.get("model", ""),
            "cli": row.get("cli", ""),
            "passed": int(success),
            "status": "success" if success else "fail",
            "token_overhead": None,
            "turn_overhead": None,
            "tool_call_overhead": None,
            "modified_file_overhead": None,
        }
        if success:
            result["token_overhead"] = _ratio(total_tokens(row), ref.get("reference_tokens") or row.get("reference_tokens"))
            result["turn_overhead"] = _ratio(row.get("turns"), ref.get("reference_turns") or row.get("reference_turns"))
            result["tool_call_overhead"] = _ratio(row.get("tool_calls"), ref.get("reference_tool_calls") or row.get("reference_tool_calls"))
            result["modified_file_overhead"] = _ratio(
                row.get("modified_files"), ref.get("reference_modified_files") or row.get("reference_modified_files")
            )
        else:
            result["failure_reason"] = row.get("failure_reason", "not_passed")
        out.append(result)
    return out

