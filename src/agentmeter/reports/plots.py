"""Plot-data helpers.

The public package intentionally avoids a plotting dependency. These helpers
return serializable series that callers can render with their preferred tool.
"""

from __future__ import annotations

from typing import Any


def bar_series(rows: list[dict[str, Any]], label_field: str, value_field: str) -> list[dict[str, Any]]:
    return [{"label": row.get(label_field, ""), "value": row.get(value_field, 0)} for row in rows]

