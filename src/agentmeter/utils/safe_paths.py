"""Path helpers that keep public examples relative."""

from __future__ import annotations

from pathlib import Path


def ensure_relative(path: str) -> str:
    p = Path(path)
    if p.is_absolute():
        raise ValueError(f"path must be relative for public artifacts: {path}")
    parts = p.parts
    if any(part == ".." for part in parts):
        raise ValueError(f"path must not escape the artifact root: {path}")
    return str(p)


def ensure_under(root: str | Path, child: str | Path) -> Path:
    root_path = Path(root).resolve()
    child_path = Path(child).resolve()
    child_path.relative_to(root_path)
    return child_path

