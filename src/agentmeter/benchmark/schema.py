"""Public benchmark schema objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


VALID_TASK_TYPES = {"single_file_bugfix", "multi_file_edit", "test_driven_repair"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


@dataclass
class TaskBlueprint:
    task_id: str
    task_type: str
    difficulty: str
    domain: str
    required_files: list[str] = field(default_factory=list)
    required_steps: list[str] = field(default_factory=list)
    hidden_constraints: list[str] = field(default_factory=list)
    control_knobs: dict[str, Any] = field(default_factory=dict)
    expected_reference_tokens: int = 0
    validator_type: str = "pytest"
    generation_model: str = "mock_generator"
    reference_trace_path: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.task_id:
            errors.append("task_id is required")
        if self.task_type not in VALID_TASK_TYPES:
            errors.append(f"task_type must be one of {sorted(VALID_TASK_TYPES)}")
        if self.difficulty not in VALID_DIFFICULTIES:
            errors.append(f"difficulty must be one of {sorted(VALID_DIFFICULTIES)}")
        if not self.domain:
            errors.append("domain is required")
        if self.expected_reference_tokens < 0:
            errors.append("expected_reference_tokens must be non-negative")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskBlueprint":
        return cls(
            task_id=str(data.get("task_id", "")),
            task_type=str(data.get("task_type", "")),
            difficulty=str(data.get("difficulty", "")),
            domain=str(data.get("domain", "")),
            required_files=list(data.get("required_files") or []),
            required_steps=list(data.get("required_steps") or []),
            hidden_constraints=list(data.get("hidden_constraints") or []),
            control_knobs=dict(data.get("control_knobs") or {}),
            expected_reference_tokens=int(data.get("expected_reference_tokens") or 0),
            validator_type=str(data.get("validator_type", "pytest")),
            generation_model=str(data.get("generation_model", "mock_generator")),
            reference_trace_path=str(data.get("reference_trace_path", "")),
        )


@dataclass
class TaskMetadata:
    task_id: str
    task_type: str
    difficulty: str
    domain: str
    required_files: list[str] = field(default_factory=list)
    required_steps: list[str] = field(default_factory=list)
    hidden_constraints: list[str] = field(default_factory=list)
    control_knobs: dict[str, Any] = field(default_factory=dict)
    expected_reference_tokens: int = 0
    validator_type: str = "pytest"
    generation_model: str = "mock_generator"
    reference_trace_path: str = ""
    materialized_from: str = ""

    def validate(self, task_dir: Path | None = None) -> list[str]:
        errors = TaskBlueprint(
            task_id=self.task_id,
            task_type=self.task_type,
            difficulty=self.difficulty,
            domain=self.domain,
            required_files=self.required_files,
            required_steps=self.required_steps,
            hidden_constraints=self.hidden_constraints,
            control_knobs=self.control_knobs,
            expected_reference_tokens=self.expected_reference_tokens,
            validator_type=self.validator_type,
            generation_model=self.generation_model,
            reference_trace_path=self.reference_trace_path,
        ).validate()
        if task_dir is not None:
            for rel in self.required_files:
                if not (task_dir / rel).exists():
                    errors.append(f"required file missing: {rel}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_blueprint(cls, bp: TaskBlueprint, materialized_from: str = "") -> "TaskMetadata":
        return cls(**bp.to_dict(), materialized_from=materialized_from)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskMetadata":
        bp = TaskBlueprint.from_dict(data)
        return cls(**bp.to_dict(), materialized_from=str(data.get("materialized_from", "")))

