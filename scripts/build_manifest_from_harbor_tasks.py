#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
import tomllib
from pathlib import Path


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


def read_task_ids(path: str | None) -> list[str] | None:
    if not path:
        return None
    task_ids = []
    seen = set()
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line in seen:
            raise SystemExit(f"duplicate task_id in task list: {line}")
        seen.add(line)
        task_ids.append(line)
    return task_ids


def discover_task_dirs(task_root: Path) -> dict[str, Path]:
    task_dirs: dict[str, Path] = {}
    duplicates: dict[str, list[Path]] = {}
    for path in task_root.rglob("instruction.md"):
        task_dir = path.parent
        if not task_dir.is_dir():
            continue
        task_id = task_dir.name
        if task_id in task_dirs:
            duplicates.setdefault(task_id, [task_dirs[task_id]]).append(task_dir)
            continue
        task_dirs[task_id] = task_dir
    if duplicates:
        details = "; ".join(f"{task_id}: {', '.join(str(p.relative_to(task_root)) for p in paths)}" for task_id, paths in sorted(duplicates.items()))
        raise SystemExit(f"duplicate task_id directories under task root: {details}")
    return task_dirs


def task_row(task_dir: Path, task_root: Path, suite: str, eval_type: str, eval_command: str, default_timeout_sec: int) -> dict[str, str]:
    toml_path = task_dir / "task.toml"
    data = tomllib.loads(toml_path.read_text(encoding="utf-8")) if toml_path.exists() else {}
    metadata = data.get("metadata") or {}
    verifier = data.get("verifier") or {}
    tags = metadata.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    timeout = verifier.get("timeout_sec") or default_timeout_sec
    return {
        "task_id": task_dir.name,
        "suite": suite,
        "relative_task_path": str(task_dir.relative_to(task_root)),
        "difficulty": str(metadata.get("difficulty") or "unknown"),
        "domain": str(metadata.get("category") or "unknown"),
        "tags": ";".join(str(tag) for tag in tags),
        "eval_type": eval_type,
        "eval_command": eval_command,
        "timeout_sec": str(int(float(timeout))),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-root", required=True)
    parser.add_argument("--suite", required=True, choices=["core30", "full80", "smoke", "custom"])
    parser.add_argument("--out", required=True)
    parser.add_argument("--task-list", help="Optional newline-delimited task-id subset.")
    parser.add_argument("--eval-type", default="harbor")
    parser.add_argument("--eval-command", default="harbor run -p {task_dir} -a oracle")
    parser.add_argument("--default-timeout-sec", type=int, default=900)
    args = parser.parse_args()

    task_root = Path(args.task_root).resolve()
    wanted = read_task_ids(args.task_list)
    task_dirs = discover_task_dirs(task_root)
    rows = []
    if wanted:
        missing = [task_id for task_id in wanted if task_id not in task_dirs]
        if missing:
            print("missing tasks in task root:", file=sys.stderr)
            for task_id in missing:
                print(f"  {task_id}", file=sys.stderr)
            raise SystemExit(f"{len(missing)} tasks from {args.task_list} were not found under {task_root}")
        ordered_dirs = [task_dirs[task_id] for task_id in wanted]
    else:
        ordered_dirs = [task_dirs[task_id] for task_id in sorted(task_dirs)]

    for task_dir in ordered_dirs:
        rows.append(task_row(task_dir, task_root, args.suite, args.eval_type, args.eval_command, args.default_timeout_sec))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} tasks to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
