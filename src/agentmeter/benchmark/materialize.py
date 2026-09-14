"""Materialize toy generated benchmark tasks."""

from __future__ import annotations

import os
from pathlib import Path

from agentmeter.utils.io import write_json

from .schema import TaskBlueprint, TaskMetadata


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def materialize_task(blueprint: TaskBlueprint, out_dir: str | Path) -> Path:
    errors = blueprint.validate()
    if errors:
        raise ValueError("; ".join(errors))
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    templates = {
        "single_file_bugfix": _single_file_bugfix,
        "multi_file_edit": _multi_file_edit,
        "test_driven_repair": _test_driven_repair,
    }
    templates[blueprint.task_type](root, blueprint)
    metadata = TaskMetadata.from_blueprint(blueprint, materialized_from="mock_template").to_dict()
    write_json(root / "metadata.json", metadata)
    checker = root / "checker.sh"
    _write(checker, "#!/usr/bin/env bash\nset -euo pipefail\npython -m pytest tests\n")
    os.chmod(checker, 0o755)
    return root


def _single_file_bugfix(root: Path, bp: TaskBlueprint) -> None:
    _write(
        root / "instruction.md",
        "Fix the bug in `repo/calculator.py` so the public tests pass. Keep the API unchanged.\n",
    )
    _write(
        root / "repo/calculator.py",
        '''def add(a, b):\n    return a + b\n\n\ndef subtract(a, b):\n    return a + b\n''',
    )
    _write(
        root / "tests/test_calculator.py",
        '''from repo.calculator import add, subtract\n\n\ndef test_add():\n    assert add(2, 3) == 5\n\n\ndef test_subtract():\n    assert subtract(7, 4) == 3\n''',
    )


def _multi_file_edit(root: Path, bp: TaskBlueprint) -> None:
    _write(
        root / "instruction.md",
        "Update the shape helpers so area calculations and labels match the tests.\n",
    )
    _write(
        root / "repo/shapes.py",
        '''from .formatting import label\n\n\ndef rectangle_area(width, height):\n    return width + height\n\n\ndef describe_rectangle(width, height):\n    return label("rectangle", rectangle_area(width, height))\n''',
    )
    _write(
        root / "repo/formatting.py",
        '''def label(name, value):\n    return f"{name}: {value}"\n''',
    )
    _write(root / "repo/__init__.py", "")
    _write(
        root / "tests/test_shapes.py",
        '''from repo.shapes import describe_rectangle, rectangle_area\n\n\ndef test_area():\n    assert rectangle_area(4, 5) == 20\n\n\ndef test_label():\n    assert describe_rectangle(4, 5) == "rectangle area=20"\n''',
    )


def _test_driven_repair(root: Path, bp: TaskBlueprint) -> None:
    _write(
        root / "instruction.md",
        "Read the tests and repair `repo/normalizer.py`. Preserve the function name.\n",
    )
    _write(
        root / "repo/normalizer.py",
        '''def normalize_tags(tags):\n    return tags\n''',
    )
    _write(root / "repo/__init__.py", "")
    _write(
        root / "tests/test_normalizer.py",
        '''from repo.normalizer import normalize_tags\n\n\ndef test_normalize_tags():\n    assert normalize_tags([" Bug ", "bug", "Feature"]) == ["bug", "feature"]\n\n\ndef test_empty_values_are_removed():\n    assert normalize_tags(["", "  ", "Docs"]) == ["docs"]\n''',
    )

