"""Mock/template blueprint generation."""

from __future__ import annotations

from .schema import TaskBlueprint


REFERENCE_TOKENS = {
    "single_file_bugfix": 45_000,
    "multi_file_edit": 70_000,
    "test_driven_repair": 85_000,
}


def generate_mock_blueprint(
    task_id: str,
    task_type: str,
    difficulty: str = "medium",
    domain: str = "toy",
    generation_model: str = "mock_generator",
) -> TaskBlueprint:
    required = {
        "single_file_bugfix": ["repo/calculator.py", "tests/test_calculator.py"],
        "multi_file_edit": ["repo/shapes.py", "repo/formatting.py", "tests/test_shapes.py"],
        "test_driven_repair": ["repo/normalizer.py", "tests/test_normalizer.py"],
    }[task_type]
    steps = {
        "single_file_bugfix": ["inspect failing arithmetic helper", "fix a one-line logic bug", "run tests"],
        "multi_file_edit": ["update implementation", "update formatting helper", "run tests"],
        "test_driven_repair": ["read tests first", "infer missing behavior", "repair implementation"],
    }[task_type]
    knobs = {
        "difficulty": difficulty,
        "files_to_modify": 1 if task_type != "multi_file_edit" else 2,
        "requires_test_reasoning": task_type == "test_driven_repair",
    }
    return TaskBlueprint(
        task_id=task_id,
        task_type=task_type,
        difficulty=difficulty,
        domain=domain,
        required_files=required,
        required_steps=steps,
        hidden_constraints=["keep public demo deterministic", "do not use network access"],
        control_knobs=knobs,
        expected_reference_tokens=REFERENCE_TOKENS[task_type],
        validator_type="pytest",
        generation_model=generation_model,
        reference_trace_path=f"generated_benchmark/references/examples/{task_id}.summary.json",
    )

