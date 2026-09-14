"""Report table helpers."""

from __future__ import annotations

from typing import Any


def markdown_table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    if columns is None:
        columns = list(rows[0].keys()) if rows else []
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)

