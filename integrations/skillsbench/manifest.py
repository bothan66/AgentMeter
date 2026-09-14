from __future__ import annotations

import csv
from pathlib import Path

from integrations.skillsbench.task_layout import discover_tasks


FIELDS = [
    "task_id",
    "suite",
    "relative_task_path",
    "difficulty",
    "domain",
    "tags",
    "eval_type",
    "eval_command",
    "timeout_sec",
]


def write_manifest(
    task_root: str | Path,
    out: str | Path,
    suite: str,
    eval_command: str,
    eval_type: str = "harbor",
    task_ids: set[str] | None = None,
) -> list[dict[str, str]]:
    root = Path(task_root).resolve()
    rows = []
    for task in discover_tasks(root, task_ids=task_ids):
        rows.append(
            {
                "task_id": task.task_id,
                "suite": suite,
                "relative_task_path": str(task.path.resolve().relative_to(root)),
                "difficulty": task.difficulty,
                "domain": task.domain,
                "tags": ";".join(task.tags),
                "eval_type": eval_type,
                "eval_command": eval_command,
                "timeout_sec": str(task.verifier_timeout_sec),
            }
        )

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows
