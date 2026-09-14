"""Offline task validation."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from agentmeter.utils.io import read_json

from .schema import TaskMetadata


REQUIRED_FILES = ("instruction.md", "repo", "tests", "checker.sh", "metadata.json")


def validate_task_dir(task_dir: str | Path, dry_run_checker: bool = True) -> dict[str, Any]:
    root = Path(task_dir)
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f"missing required artifact: {rel}")
    metadata: TaskMetadata | None = None
    if (root / "metadata.json").exists():
        try:
            metadata = TaskMetadata.from_dict(read_json(root / "metadata.json"))
            errors.extend(metadata.validate(root))
        except Exception as exc:
            errors.append(f"invalid metadata.json: {exc}")
    checker_result: dict[str, Any] = {"ran": False}
    if dry_run_checker and (root / "checker.sh").exists():
        proc = subprocess.run(["bash", "checker.sh"], cwd=root, text=True, capture_output=True, check=False)
        checker_result = {
            "ran": True,
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-1000:],
            "stderr_tail": proc.stderr[-1000:],
        }
        if proc.returncode == 127:
            errors.append("checker command was not found")
    return {"task_dir": str(root), "ok": not errors, "errors": errors, "checker": checker_result}

