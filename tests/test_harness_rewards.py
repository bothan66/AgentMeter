"""Graded verifier outcomes and unknown charges must survive runner normalization."""

import json
import shlex
import sys
from pathlib import Path

import pytest

from agentmeter.harness import (
    ApiConfig,
    Experiment,
    TaskSpec,
    normalize_api_response,
    reported_reward,
    run_attempt,
)


@pytest.fixture
def run_with_reward(tmp_path, monkeypatch):
    task_dir = tmp_path / "tasks" / "example"
    task_dir.mkdir(parents=True)
    task_dir.joinpath("instruction.md").write_text("Write the result.")

    def run(remote_summary, *, verifier_reward=None, verifier_exit=0):
        payload = {"reward": verifier_reward} if verifier_reward is not None else "done"
        task_dir.joinpath("verify.py").write_text(
            f"print({json.dumps(payload)!r})\nraise SystemExit({verifier_exit})\n"
        )
        task = TaskSpec(
            task_id="example",
            suite="custom",
            relative_task_path="example",
            difficulty="easy",
            domain="test",
            tags=(),
            eval_type="custom",
            eval_command=f"{shlex.quote(sys.executable)} verify.py",
            timeout_sec=10,
        )
        exp = Experiment.from_yaml(Path(__file__).parent / "fixtures" / "smoke.yaml")
        monkeypatch.setattr(
            "agentmeter.harness.run_api",
            lambda *args: {"status": "completed", "summary": remote_summary},
        )
        return run_attempt(
            task,
            task_dir.parent,
            tmp_path / "runs",
            "model",
            "cli",
            1,
            exp,
            {"cli": ApiConfig(url="https://example.invalid")},
        )

    return run


@pytest.mark.parametrize("reward", [0, 0.75, 1])
def test_runner_graded_reward_is_not_collapsed_to_binary_pass(run_with_reward, reward):
    summary = run_with_reward({"passed": True, "reward": reward})
    assert summary["reward"] == reward
    assert summary["passed"] is (reward == 1)
    assert summary["reward_source"] == "runner_verifier_reward"


def test_structured_local_verifier_is_authoritative(run_with_reward):
    summary = run_with_reward({"reward": 1}, verifier_reward=0.4)
    assert summary["reward"] == 0.4
    assert summary["passed"] is False
    assert summary["reward_source"] == "verifier_stdout"


def test_local_verifier_failure_is_not_overridden_by_remote_pass(run_with_reward):
    summary = run_with_reward({"reward": 1}, verifier_exit=1)
    assert summary["reward"] == 0
    assert summary["passed"] is False


def test_binary_verifier_compatibility_does_not_use_api_status_as_reward(run_with_reward):
    summary = run_with_reward({"passed": True}, verifier_exit=1)
    assert summary["reward"] == 0
    assert summary["reward_source"] == "verifier_exit_code"


@pytest.mark.parametrize("cost", [None, 0, 0.05])
def test_harness_cost_preserves_unknown_and_actual_zero(run_with_reward, cost):
    remote = {} if cost is None else {"cost_usd": cost, "total_cost_cny": cost}
    summary = run_with_reward(remote)
    assert summary["cost_usd"] == cost
    assert summary["total_cost_cny"] == cost
    usage = json.loads(Path(summary["run_dir"]).joinpath("usage.json").read_text())
    assert usage["cost_usd"] == cost
    assert usage["total_cost_cny"] == cost


def test_normalization_does_not_invent_a_zero_charge():
    summary = normalize_api_response(
        {"output_text": "done", "usage": {"total_tokens": 20}},
        ApiConfig(url="https://example.invalid", response_format="responses"),
    )["summary"]
    assert summary["cost_usd"] is None
    assert summary["total_cost_cny"] is None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_reward_is_not_silently_treated_as_a_pass(value):
    with pytest.raises(ValueError):
        reported_reward({"reward": value})


def test_nested_verifier_reward_and_explicit_zero():
    assert reported_reward({"verifier_result": {"rewards": {"reward": 0.75}}}) == 0.75
    assert reported_reward({"reward": 0, "rewards": {"reward": 1}}) == 0
    assert reported_reward({"passed": True, "status": "completed"}) is None
