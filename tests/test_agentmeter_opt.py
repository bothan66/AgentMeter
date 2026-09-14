from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentmeter_opt.optimize_instruction import (
    adaptation_policy_for_baseline,
    baseline_efficiency_friction,
    load_baseline_result,
    objective_for_mode,
)
from agentmeter_opt.safety_gate import combo_adapted_instruction_safety_gate, instruction_safety_gate


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
    rewritten = (
        "Count how many fighters remain undefeated in each weight class and write the result to undefeated.csv."
    )
    result = combo_adapted_instruction_safety_gate(original, rewritten)
    assert result["status"] == "fail"
    assert "changed_core_task_objective" in result["violations"]


def test_safety_gate_reviews_unsupported_sorting_or_rounding_preferences():
    original = (
        "Calculate totals by category and write result.csv following sample_result.csv."
    )
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
        "trajectory_evidence": {"route_profile": {"repeated_reads": [], "repeated_commands": [], "high_token_events": []}},
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
        "trajectory_evidence": {"route_profile": {"repeated_reads": [], "repeated_commands": [], "high_token_events": []}},
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
