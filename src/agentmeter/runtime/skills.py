"""Prepare external SkillsBench skills without redistributing their contents."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from agentmeter.paths import find_repository

MANIFEST_PATH = Path("integrations/skillsbench/skills_manifest.json")


def load_skill_manifest(repo: Path) -> dict[str, dict[str, str]]:
    """Read the file-level hashes of the historical task dependencies."""
    manifest = json.loads((repo / MANIFEST_PATH).read_text())
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported skills manifest version")
    tasks = manifest["tasks"]
    for task, files in tasks.items():
        if not task or task in {".", ".."} or "/" in task or "\\" in task:
            raise ValueError(f"Invalid skill task ID: {task}")
        for name, digest in files.items():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or len(path.parts) < 2:
                raise ValueError(f"Invalid skill file path: {name}")
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError(f"Invalid skill file digest: {name}")
    return tasks


def _dependency_path(root: Path, relative: str) -> Path:
    """Reject links within a dependency tree before reading or writing it."""
    path = root / relative
    for component in (path, *path.parents):
        if component == root:
            break
        if component.is_symlink():
            raise ValueError(f"Skill dependency must not be a symlink: {component}")
    return path


def _check_digest(path: Path, digest: str) -> bytes:
    if not path.is_file():
        raise ValueError(f"Missing external skill file: {path}")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError(f"Skill file differs from the recorded snapshot: {path}")
    return content


def prepare_skills(repo: Path, source_root: Path, task_ids: Sequence[str] = ()) -> int:
    """Copy verified files from a user-supplied task collection; never overwrite."""
    repo, source_root = repo.resolve(), source_root.expanduser().resolve()
    tasks = load_skill_manifest(repo)
    selected = list(dict.fromkeys(task_ids)) if task_ids else list(tasks)
    unknown = set(selected) - tasks.keys()
    if unknown:
        raise ValueError(f"No external skills recorded for: {', '.join(sorted(unknown))}")
    executables = json.loads((repo / MANIFEST_PATH).read_text()).get("executable_files", {})
    pending: list[tuple[Path, bytes, int]] = []
    # Validate the complete selection before creating any files.
    for task in selected:
        for name, digest in tasks[task].items():
            relative = f"{task}/environment/skills/{name}"
            source = _dependency_path(source_root, relative)
            content = _check_digest(source, digest)
            destination = _dependency_path(repo, f"benchmark_tasks/skillsbench/{relative}")
            if destination.exists():
                _check_digest(destination, digest)
            else:
                mode = 0o755 if name in executables.get(task, ()) else 0o644
                pending.append((destination, content, mode))
    for destination, content, mode in pending:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(content)
        destination.chmod(mode)
    return len(pending)


def verify_task_skills(task_dir: Path) -> None:
    """Fail before Harbor starts if a bundled task's external skills are absent."""
    task_dir = task_dir.resolve()
    for repo in task_dir.parents:
        if not (repo / MANIFEST_PATH).is_file():
            continue
        if task_dir != repo / "benchmark_tasks/skillsbench" / task_dir.name:
            return  # External task checkouts define their own dependencies.
        files = load_skill_manifest(repo).get(task_dir.name, {})
        try:
            for name, digest in files.items():
                path = _dependency_path(
                    repo, f"benchmark_tasks/skillsbench/{task_dir.name}/environment/skills/{name}"
                )
                _check_digest(path, digest)
        except ValueError as exc:
            raise ValueError(
                f"{exc}. Prepare this dependency with: agentmeter prepare-skills "
                f"--source-root /path/to/skillsbench/tasks --task {task_dir.name}"
            ) from exc
        return


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, help="AgentMeter checkout")
    parser.add_argument(
        "--source-root", type=Path, required=True, help="User-supplied SkillsBench tasks directory"
    )
    parser.add_argument("--task", action="append", default=[], help="Task ID; default: all seven")
    args = parser.parse_args(argv)
    count = prepare_skills(find_repository(args.repo_root), args.source_root, args.task)
    print(f"Verified skill dependencies; prepared {count} new files (Git-ignored).")
    return 0
