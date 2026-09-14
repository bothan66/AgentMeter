from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillsBenchTask:
    task_id: str
    path: Path
    difficulty: str
    domain: str
    tags: tuple[str, ...]
    verifier_timeout_sec: int


def read_task_toml(task_dir: str | Path) -> dict[str, Any]:
    path = Path(task_dir) / "task.toml"
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def is_skillsbench_task(path: str | Path) -> bool:
    task_dir = Path(path)
    return (task_dir / "instruction.md").exists() and (task_dir / "task.toml").exists()


def load_task(task_dir: str | Path, default_timeout_sec: int = 900) -> SkillsBenchTask:
    task_path = Path(task_dir)
    data = read_task_toml(task_path)
    metadata = data.get("metadata") or {}
    verifier = data.get("verifier") or {}
    tags = metadata.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    timeout = verifier.get("timeout_sec") or default_timeout_sec
    return SkillsBenchTask(
        task_id=task_path.name,
        path=task_path,
        difficulty=str(metadata.get("difficulty") or "unknown"),
        domain=str(metadata.get("category") or "unknown"),
        tags=tuple(str(tag) for tag in tags),
        verifier_timeout_sec=int(float(timeout)),
    )


def discover_tasks(task_root: str | Path, task_ids: set[str] | None = None) -> list[SkillsBenchTask]:
    root = Path(task_root)
    tasks: list[SkillsBenchTask] = []
    for child in sorted(path for path in root.iterdir() if path.is_dir()):
        if task_ids and child.name not in task_ids:
            continue
        if is_skillsbench_task(child):
            tasks.append(load_task(child))
    return tasks
