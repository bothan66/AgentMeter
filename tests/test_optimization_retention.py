"""Offline regression tests for the live optimizer's final retention contract."""

import json
import sys
from types import SimpleNamespace

import pytest

from agentmeter.optimization.optimize import main
from agentmeter.optimization.selection import CandidateOutcome, retain_candidate
from agentmeter.optimization.text import diff_summary


def outcome(name, reward, usd=None, cny=None, instruction=None):
    return CandidateOutcome(
        name, instruction or name, reward, None if reward is None else reward >= 1, usd, cny
    )


def test_retention_reward_is_primary_even_when_cost_is_higher_or_unknown():
    original = outcome("original", 0.7, usd=1)
    cheaper = outcome("cheaper", 0.6, usd=0)
    better = outcome("better", 0.8, usd=100)
    best = outcome("best", 0.9)
    assert retain_candidate(original, [cheaper, better, best]).winner == best


@pytest.mark.parametrize(
    ("original", "candidate", "changed"),
    [
        (outcome("original", 1, usd=1), outcome("rewrite", 1, usd=0), True),
        (outcome("original", 1, cny=1), outcome("rewrite", 1, cny=0.5), True),
        (outcome("original", 1, usd=1), outcome("rewrite", 1, cny=0.5), False),
        (outcome("original", 1, usd=1), outcome("rewrite", 1), False),
        (outcome("original", 1), outcome("rewrite", 1, usd=0), False),
        (outcome("original", 1, usd=1), outcome("rewrite", 1, usd=1), False),
        (outcome("original", 1, usd=1), outcome("rewrite", None, usd=0), False),
        (outcome("original", None, usd=1), outcome("rewrite", 1, usd=0), False),
        (outcome("original", 0, usd=1), outcome("rewrite", 0, usd=0), True),
    ],
)
def test_retention_requires_observed_comparable_cost_for_equal_rewards(
    original, candidate, changed
):
    retained = retain_candidate(original, [candidate])
    assert (retained.winner == candidate) is changed


def test_exact_candidate_ties_prefer_smaller_edit_to_original():
    original = outcome("original", 0, usd=1, instruction="Read input.csv.")
    long = outcome("long", 1, usd=2, instruction="Read input.csv carefully before beginning.")
    short = outcome("short", 1, usd=2, instruction="Read input.csv now.")
    assert retain_candidate(original, [long, short]).winner == short
    assert retain_candidate(original, [short, long]).winner == short


def test_mixed_currency_chains_cannot_select_a_regression_against_original():
    original = outcome("original", 1, usd=1, cny=7)
    improved = outcome("improved", 1, usd=0.9, cny=10)
    regressed = outcome("regressed", 1, cny=9)
    assert retain_candidate(original, [improved, regressed]).winner == improved
    assert retain_candidate(original, [regressed, improved]).winner == improved


@pytest.fixture
def optimize_live(tmp_path, monkeypatch):
    """Run the actual coordinator with offline GEPA and agent-service substitutes."""
    task = tmp_path / "tasks" / "example"
    task.mkdir(parents=True)
    original = "Read input.csv and write result.csv."
    task.joinpath("instruction.md").write_text(original)
    baseline_path = tmp_path / "baseline.json"
    runner_config = tmp_path / "runners.yaml"
    runner_config.write_text("api_runners: {}")
    scores = []
    module = "agentmeter.optimization.optimize"
    monkeypatch.setattr(f"{module}.runner_has_route", lambda *args: True)
    monkeypatch.setattr(
        f"{module}.detect_gepa",
        lambda: {"installed": True, "version": "test", "module_path": "fixture", "api": {}},
    )
    monkeypatch.setattr(
        f"{module}.safety_gate_for_mode",
        lambda *args: {"status": "pass", "violations": [], "decision": "accept"},
    )

    def run(baseline, candidates, *, seed=None, cost_file=None):
        baseline_path.write_text(json.dumps(baseline))
        summaries = iter(summary for _, summary in candidates)

        def run_agent_task(**kwargs):
            run_dir = kwargs["run_root"] / "rerun"
            run_dir.mkdir()
            if cost_file is not None:
                run_dir.joinpath("cost.json").write_text(json.dumps(cost_file))
            return {"summary": next(summaries), "run_dir": str(run_dir)}

        def optimize_anything(*, seed_candidate, evaluator, objective, max_metric_calls):
            scores.append(evaluator(original))
            for candidate, _ in candidates:
                scores.append(evaluator(candidate))
            # Deliberately claim the worst text to show final live retention does
            # not blindly accept GEPA's returned proposal or maximum bonus score.
            return {"best_candidate": "unverified output"}

        monkeypatch.setattr(f"{module}.run_agent_task", run_agent_task)
        monkeypatch.setitem(
            sys.modules,
            "gepa.optimize_anything",
            SimpleNamespace(optimize_anything=optimize_anything),
        )
        out = tmp_path / "results"
        args = [
            "--task-root",
            str(task.parent),
            "--task-id",
            task.name,
            "--combo",
            "qwen36_codex",
            "--allow-proxy",
            "--baseline-result",
            str(baseline_path),
            "--runner-config",
            str(runner_config),
            "--eval-command",
            "unused mock verifier",
            "--max-real-reruns",
            str(len(candidates)),
            "--out-dir",
            str(out),
        ]
        if seed is not None:
            seed_path = tmp_path / "seed.md"
            seed_path.write_text(seed)
            args.extend(["--seed-instruction", str(seed_path)])
        main(args)
        result_dir = out / task.name / "qwen36_codex"
        result = json.loads(result_dir.joinpath("gepa_task_result.json").read_text())
        result["retention_details"] = json.loads(result_dir.joinpath("retention.json").read_text())
        text = result_dir.joinpath("best_rewritten_instruction.md").read_text()
        assert task.joinpath("instruction.md").read_text() == original
        assert json.loads(baseline_path.read_text()) == baseline
        return result, text, scores

    return run, original


def test_live_retention_does_not_trade_reward_for_token_bonus(optimize_live):
    run, original = optimize_live
    result, text, scores = run(
        {"reward": 1, "passed": True, "total_tokens": 1000, "cost_usd": 1},
        [
            (
                original + " Carefully.",
                {"reward": 0.9, "passed": True, "total_tokens": 1, "cost_usd": 0.01},
            )
        ],
        seed=original + " Previous rewrite.",
    )
    assert scores[1] > scores[0]
    assert text == original
    assert result["retained_candidate_id"] == "original"
    assert result["optimized_reward"] == 1
    assert result["optimized_cost_usd"] == 1
    assert result["optimized_tokens"] == 1000
    assert result["exploration_score_used_for_retention"] is False


def test_live_partial_reward_is_not_a_pass_when_bonus_exceeds_one(optimize_live):
    run, original = optimize_live
    rewritten = original + " Clarified."
    result, text, scores = run(
        {"reward": 0.7, "total_tokens": 1000, "cost_usd": 1},
        [(rewritten, {"reward": 0.9, "passed": True, "total_tokens": 1, "cost_usd": 2})],
    )
    assert scores[-1] > 1
    assert text == rewritten
    assert result["optimized_reward"] == 0.9
    assert result["optimized_passed"] is False
    assert result["retention_reason"] == "higher_reward"


def test_live_equal_reward_uses_money_not_total_tokens(optimize_live):
    run, original = optimize_live
    cheaper = original + " Clarified."
    result, text, scores = run(
        {"reward": 1, "total_tokens": 1000, "cost_usd": 1},
        [
            (original + " Shorter.", {"reward": 1, "total_tokens": 1, "cost_usd": 1.5}),
            (cheaper, {"reward": 1, "total_tokens": 2000, "cost_usd": 0.5}),
        ],
    )
    assert scores[1] > scores[2]
    assert text == cheaper
    assert result["optimized_cost_usd"] == 0.5
    assert result["optimized_tokens"] == 2000


def test_live_candidate_cost_file_takes_precedence(optimize_live):
    run, original = optimize_live
    result, text, _ = run(
        {"reward": 1, "cost_usd": 1},
        [(original + " Clarified.", {"reward": 1, "cost_usd": 0})],
        cost_file={"cost_usd": {"total": 2}},
    )
    assert text == original
    assert result["retention_reason"] == "no_measured_improvement"


@pytest.mark.parametrize("reward", [None, 0])
def test_live_missing_or_zero_reward_is_not_promoted(optimize_live, reward):
    run, original = optimize_live
    summary = {"total_tokens": 1, "cost_usd": 0}
    if reward is not None:
        summary.update(reward=reward, passed=True)
    result, text, _ = run(
        {"reward": 0.5, "total_tokens": 1000, "cost_usd": 1},
        [(original + " Clarified.", summary)],
    )
    assert text == original
    assert result["optimized_reward"] == 0.5
    assert result["optimized_passed"] is False


def test_live_unknown_cost_does_not_count_as_zero(optimize_live):
    run, original = optimize_live
    result, text, _ = run(
        {"reward": 1, "total_tokens": 1000, "cost_usd": 1},
        [(original + " Clarified.", {"reward": 1, "total_tokens": 1})],
    )
    assert text == original
    assert result["unresolved_cost_ties"] == ["metric_call_002"]


def test_identical_candidate_cache_does_not_count_as_independent_evidence(optimize_live):
    run, original = optimize_live
    rewritten = original + " Clarified."
    summary = {"reward": 1, "total_tokens": 10, "cost_usd": 0.5}
    result, text, _ = run(
        {"reward": 1, "total_tokens": 1000, "cost_usd": 1},
        [(rewritten, summary), (rewritten, summary)],
    )
    assert text == rewritten
    assert result["metric_calls"] == 3
    assert result["real_reruns"] == 1
    assert result["retention_details"]["evaluated_candidates"] == 1
    assert result["retained_candidate_id"] == "metric_call_002"


def test_code_indentation_changes_are_not_noops():
    original = "```python\nif ready:\n    write_result()\n```"
    changed = "```python\nif ready:\nwrite_result()\n```"
    assert " ".join(original.split()) == " ".join(changed.split())
    assert diff_summary(original, changed)["changed"] is True
    assert diff_summary(original, original)["changed"] is False


def test_whitespace_changes_require_their_own_rerun(optimize_live):
    run, original = optimize_live
    first = original.replace(" ", "  ")
    second = original.replace(" ", "\n")
    result, text, _ = run(
        {"reward": 1, "cost_usd": 1},
        [
            (first, {"reward": 1, "cost_usd": 0.5}),
            (second, {"reward": 1, "cost_usd": 0.25}),
        ],
    )
    assert text == second
    assert result["real_reruns"] == 2
    assert result["retention_details"]["evaluated_candidates"] == 2
    assert result["retained_candidate_id"] == "metric_call_003"
