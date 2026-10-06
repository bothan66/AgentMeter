"""Text, public-path, and output helpers used by the optimizer."""

from __future__ import annotations

import difflib
import re
import shutil
from pathlib import Path
from typing import Any

FILE_OR_PATH_RE = re.compile(r"/|[\w+-]+\.(?:csv|json|txt|md|py|sh|yaml|yml|toml|pdf|tsv)$", re.I)


def safe_name(value: str) -> str:
    name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value).strip("_")
    if name in {".", ".."}:
        raise ValueError("Output names cannot be '.' or '..'")
    return name or "item"


def compact(text: Any, limit: int = 600) -> str:
    raw = " ".join(str(text or "").split())
    if len(raw) <= limit:
        return raw
    return raw[: max(0, limit - 16)].rstrip() + " ... [truncated]"


def extract_paths(text: str) -> set[str]:
    matches = re.findall(
        r"`([^`]+)`|(/[\w./+-]+)|\b([\w./+-]+\.(?:csv|json|txt|md|py|sh|yaml|yml|toml|pdf|tsv))\b",
        text,
    )
    out: set[str] = set()
    for groups in matches:
        code_span, abs_path, file_name = groups
        if code_span and FILE_OR_PATH_RE.search(code_span):
            out.add(code_span.strip("`"))
        if abs_path:
            out.add(abs_path.strip("`"))
        if file_name:
            out.add(file_name.strip("`"))
    return out


def is_public_path_composition(path: str, original_paths: set[str]) -> bool:
    if "/" not in path:
        return False
    pieces = path.rstrip("/").rsplit("/", 1)
    if len(pieces) != 2:
        return False
    parent, name = pieces
    return name in original_paths and (parent in original_paths or parent + "/" in original_paths)


def diff_summary(original: str, rewritten: str) -> dict[str, Any]:
    original_lines = original.splitlines()
    rewritten_lines = rewritten.splitlines()
    diff = list(
        difflib.unified_diff(
            original_lines,
            rewritten_lines,
            fromfile="original/instruction.md",
            tofile="rewritten/instruction.md",
            lineterm="",
        )
    )
    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    return {
        "changed": " ".join(original.split()) != " ".join(rewritten.split()),
        "added_lines": added,
        "removed_lines": removed,
        "original_paths": sorted(extract_paths(original)),
        "rewritten_paths": sorted(extract_paths(rewritten)),
        "new_paths": sorted(
            path
            for path in extract_paths(rewritten)
            if path not in extract_paths(original)
            and not is_public_path_composition(path, extract_paths(original))
        ),
    }


def ensure_empty_dir(
    path: Path, overwrite: bool, *, output_root: Path, protected_paths: list[Path]
) -> None:
    """Prepare one run's output, never following links out of its output tree."""
    root, target = output_root.resolve(), path.resolve()
    if path.is_symlink() or target == root or not target.is_relative_to(root):
        raise ValueError("Run output must be a directory strictly inside the output root")
    for source in protected_paths:
        source = source.resolve()
        if source.is_relative_to(target) or (source.is_dir() and target.is_relative_to(source)):
            raise ValueError(f"Run output overlaps a protected input: {source}")
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise SystemExit(f"refusing to overwrite non-empty output dir: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
