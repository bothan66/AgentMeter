"""Parse sanitized toy trajectories into summary statistics.

This parser accepts only public, reduced trajectory JSON. It does not preserve
raw prompts, raw responses, request headers, or user-authored private content.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_sanitized_trajectory(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    events = data.get("events", [])
    model_events = [event for event in events if event.get("type") == "model_call"]
    tool_events = [event for event in events if event.get("type") == "tool_call"]
    modified = set()
    for event in tool_events:
        rel_path = event.get("file_path")
        if rel_path and event.get("tool_kind") in {"edit", "write"}:
            modified.add(rel_path)
    input_tokens = sum(int(event.get("input_tokens") or 0) for event in model_events)
    output_tokens = sum(int(event.get("output_tokens") or 0) for event in model_events)
    return {
        "task_id": data.get("task_id", ""),
        "model": data.get("model", ""),
        "cli": data.get("cli", ""),
        "passed": int(bool(data.get("passed", False))),
        "turns": len(model_events),
        "tool_calls": len(tool_events),
        "modified_files": len(modified),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "raw_content_retained": False,
    }

