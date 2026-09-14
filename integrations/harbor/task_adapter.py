from __future__ import annotations

from pathlib import Path


def harbor_task_path(task_root: str | Path, relative_task_path: str) -> Path:
    root = Path(task_root).resolve()
    task = (root / relative_task_path).resolve()
    task.relative_to(root)
    return task


def validate_harbor_task(task_dir: str | Path) -> None:
    task = Path(task_dir)
    required = ["instruction.md", "task.toml", "environment", "tests"]
    missing = [name for name in required if not (task / name).exists()]
    if missing:
        raise ValueError(f"not a Harbor/SkillsBench task: {task}; missing {missing}")
