import json
import sys
from types import SimpleNamespace

import pytest

from agentmeter.optimization.feedback import load_baseline_result
from agentmeter.optimization.optimize import main
from agentmeter.optimization.policy import (
    adaptation_policy_for_baseline,
    baseline_efficiency_friction,
    objective_for_mode,
)
from agentmeter.optimization.safety import (
    combo_adapted_instruction_safety_gate,
    instruction_safety_gate,
)


def test_safety_gate_pass_for_public_clarification():
    original = "Read input.csv and write result.csv with the required columns."
    rewritten = (
        "Read `input.csv` and write `result.csv`.\n"
        "Keep the required columns exactly as specified in the original task."
    )
    result = instruction_safety_gate(original, rewritten)
    assert result["status"] == "pass"


def test_safety_gate_fails_for_hidden_and_solver_hints():
    original = "Implement the task and write result.csv."
    rewritten = (
        "Implement the task and write result.csv.\n"
        "Check tests/test_outputs.py and use pandas groupby to match the hidden evaluator."
    )
    result = instruction_safety_gate(original, rewritten)
    assert result["status"] == "fail"


def test_safety_gate_fails_when_core_task_objective_is_removed():
    original = (
        "Identify the top fighters in each weight class and count how many remain undefeated. "
        "Write the result to undefeated.csv."
    )
    rewritten = "Count how many fighters remain undefeated in each weight class and write the result to undefeated.csv."
    result = combo_adapted_instruction_safety_gate(original, rewritten)
    assert result["status"] == "fail"
    assert "changed_core_task_objective" in result["violations"]


def test_safety_gate_reviews_unsupported_sorting_or_rounding_preferences():
    original = "Calculate totals by category and write result.csv following sample_result.csv."
    rewritten = (
        "Calculate totals by category and write result.csv following sample_result.csv. "
        "Round all values to 2 decimal places and sort the rows alphabetically."
    )
    result = combo_adapted_instruction_safety_gate(original, rewritten)
    assert result["status"] == "needs_manual_review"
    assert "unsupported_public_preference_addition" in result["violations"]


def test_safety_gate_fails_for_implementation_level_output_hint():
    original = "Calculate totals by category and write result.csv following sample_result.csv."
    rewritten = (
        "Calculate totals by category and write result.csv following sample_result.csv. "
        "Save the CSV without the pandas DataFrame index (`index=False`)."
    )
    result = combo_adapted_instruction_safety_gate(original, rewritten)
    assert result["status"] == "fail"
    assert "implementation_route" in result["violations"]


def test_combo_adapted_passes_public_output_contract_clarification():
    original = "Write result.csv following sample_result.csv."
    rewritten = (
        "Write result.csv following sample_result.csv. "
        "Use the exact column names and column order shown in sample_result.csv."
    )
    result = combo_adapted_instruction_safety_gate(original, rewritten)
    assert result["status"] == "pass"


def test_combo_adapted_passed_baseline_switches_to_efficiency_policy():
    policy = adaptation_policy_for_baseline(
        {"baseline_passed": True, "trajectory_evidence": {}},
        "combo_adapted",
    )
    objective = objective_for_mode("combo_adapted", baseline_passed=True)
    assert policy["baseline_mode"] == "passed_efficiency_only"
    assert "lower tokens/steps/tool calls" in policy["optimization_target"]
    assert "Do not add new task semantics" in policy["agent_efficiency_goal"]
    assert "already passes the task on the baseline run" in objective


def test_baseline_efficiency_friction_flags_high_cost_passed_routes():
    baseline = {
        "baseline_tokens": 250_000,
        "baseline_turns": 24,
        "baseline_tool_calls": 0,
        "trajectory_evidence": {
            "route_profile": {
                "repeated_reads": [],
                "repeated_commands": [],
                "high_token_events": [],
            }
        },
    }
    result = baseline_efficiency_friction(baseline)
    assert result["has_efficiency_friction"] is True
    assert "high_total_tokens" in result["reasons"]
    assert "long_route_steps" in result["reasons"]


def test_baseline_efficiency_friction_allows_smooth_passed_routes_to_noop():
    baseline = {
        "baseline_tokens": 50_000,
        "baseline_turns": 6,
        "baseline_tool_calls": 4,
        "trajectory_evidence": {
            "route_profile": {
                "repeated_reads": [],
                "repeated_commands": [],
                "high_token_events": [],
            }
        },
    }
    result = baseline_efficiency_friction(baseline)
    assert result["has_efficiency_friction"] is False


def test_load_baseline_result_reads_sibling_result_for_trajectory_json(tmp_path):
    trial_dir = tmp_path / "dm-csv-001__trial"
    agent_dir = trial_dir / "agent"
    verifier_dir = trial_dir / "verifier"
    agent_dir.mkdir(parents=True)
    verifier_dir.mkdir(parents=True)

    (agent_dir / "trajectory.json").write_text(
        """
        {
          "steps": [{"step_id": 1}, {"step_id": 2}],
          "final_metrics": {
            "total_prompt_tokens": 100,
            "total_completion_tokens": 20,
            "total_cached_tokens": 30
          }
        }
        """.strip(),
        encoding="utf-8",
    )
    (trial_dir / "result.json").write_text(
        """
        {
          "verifier_result": {
            "rewards": {
              "reward": 1.0
            }
          }
        }
        """.strip(),
        encoding="utf-8",
    )

    baseline = load_baseline_result(agent_dir / "trajectory.json", "dm-csv-001", "glm51_qwen_coder")
    assert baseline["baseline_passed"] is True
    assert baseline["baseline_reward"] == 1.0
    assert baseline["baseline_tokens"] == 150
    assert baseline["baseline_turns"] == 2


@pytest.mark.parametrize("task_id", [".", "..", "../task", "/task"])
def test_optimizer_rejects_task_path_traversal(tmp_path, task_id):
    with pytest.raises(SystemExit) as error:
        main(["--task-root", str(tmp_path), "--task-id", task_id, "--dry-run", "--overwrite"])
    assert error.value.code == 2
    assert not list(tmp_path.iterdir())


def test_overwrite_rejects_output_escape_and_preserves_inputs(tmp_path):
    from agentmeter.optimization.text import ensure_empty_dir, safe_name

    with pytest.raises(ValueError):
        safe_name("..")
    output_root = tmp_path / "outputs"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    protected = inputs / "trajectory.json"
    protected.write_text('{"prior": true}')
    output_root.mkdir()
    link = output_root / "linked"
    link.symlink_to(inputs, target_is_directory=True)
    for invalid in (output_root, inputs, link):
        with pytest.raises(ValueError):
            ensure_empty_dir(invalid, True, output_root=output_root, protected_paths=[protected])
    assert protected.read_text() == '{"prior": true}'

    nested = output_root / "task" / "combo"
    nested.mkdir(parents=True)
    seed = nested / "seed.md"
    seed.write_text("keep the previous instruction")
    with pytest.raises(ValueError, match="protected input"):
        ensure_empty_dir(nested, True, output_root=output_root, protected_paths=[seed])
    assert seed.read_text() == "keep the previous instruction"


def test_live_optimization_requires_an_explicit_verifier(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        main(["--task-root", str(tmp_path)])
    assert error.value.code == 2
    assert "--eval-command is required for live reruns" in capsys.readouterr().err


def test_candidate_only_optimizer_persists_accepted_rewrite(tmp_path, monkeypatch):
    task = tmp_path / "tasks" / "example"
    task.mkdir(parents=True)
    task.joinpath("instruction.md").write_text(
        "Read input.csv and write result.csv with the required columns.", encoding="utf-8"
    )
    rewritten = (
        "Read `input.csv` and write `result.csv`.\n"
        "Keep the required columns exactly as specified in the original task."
    )

    def optimize_anything(*, seed_candidate, evaluator, objective, max_metric_calls):
        assert max_metric_calls == 2
        assert "semantically equivalent" in objective
        assert evaluator(seed_candidate) == 0.0
        assert evaluator(rewritten) == 1.0
        return {"best_candidate": rewritten}

    monkeypatch.setitem(
        sys.modules, "gepa.optimize_anything", SimpleNamespace(optimize_anything=optimize_anything)
    )
    monkeypatch.setattr(
        "agentmeter.optimization.optimize.detect_gepa",
        lambda: {"installed": True, "version": "test", "module_path": "fixture", "api": {}},
    )
    out = tmp_path / "results"
    main(
        [
            "--task-root",
            str(task.parent),
            "--task-id",
            task.name,
            "--combo",
            "qwen36_codex",
            "--candidate-only",
            "--allow-proxy",
            "--max-metric-calls",
            "2",
            "--out-dir",
            str(out),
        ]
    )
    result_dir = out / task.name / "qwen36_codex"
    result = json.loads((result_dir / "gepa_task_result.json").read_text())
    assert result["accepted_candidate"] is True
    assert result["optimized_passed"] is None
    assert result["real_reruns"] == 0
    assert result["metric_calls"] == 2
    assert (result_dir / "best_rewritten_instruction.md").read_text() == rewritten
