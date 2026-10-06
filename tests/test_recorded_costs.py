"""Recorded execution charges must not be replaced by token-price estimates."""

import hashlib
import json
from pathlib import Path

import pytest

from agentmeter.optimization.costs import (
    comparable_costs,
    cost_summary_from_mapping,
    load_cost_summary,
)
from agentmeter.optimization.feedback import build_round_feedback, load_baseline_result


def test_cost_json_is_authoritative_and_preserves_explicit_zero(tmp_path):
    (tmp_path / "cost.json").write_text(
        json.dumps({"cost_cny": {"total": 0}, "tokens": {"cache_hit": 0, "cache_hit_observed": 10}})
    )
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"agent_result": {"cost_usd": 5}}))
    summary = load_cost_summary(result)
    assert summary["available"] is True
    assert summary["billable_cost_cny"] == 0
    assert summary["billable_cost_usd"] is None
    assert summary["cost_currency"] == "CNY"
    assert summary["cost_path"] == str(tmp_path / "cost.json")
    assert summary["cache_hit_tokens"] == 0


def test_harbor_recorded_usd_is_read_without_token_estimation(tmp_path):
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps({"agent_result": {"cost_usd": 0.123, "n_input_tokens": 1_000_000}})
    )
    summary = load_cost_summary(result)
    assert summary["billable_cost_usd"] == 0.123
    assert summary["billable_cost_cny"] is None
    assert summary["cost_source"] == "result.json.agent_result.cost_usd"


def test_token_only_result_keeps_cost_missing(tmp_path):
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps({"agent_result": {"n_input_tokens": 1_000_000, "n_cache_tokens": 20}})
    )
    summary = load_cost_summary(result)
    assert summary["available"] is False
    assert summary["billable_cost_usd"] is None
    assert summary["billable_cost_cny"] is None
    assert summary["reason"] == "no_recorded_cost"


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, "invalid"])
def test_invalid_recorded_cost_does_not_fall_back_to_token_prices(tmp_path, value):
    (tmp_path / "cost.json").write_text(json.dumps({"cost_cny": {"total": value}}))
    (tmp_path / "result.json").write_text(json.dumps({"agent_result": {"cost_usd": 1}}))
    summary = load_cost_summary(tmp_path)
    assert summary["available"] is False
    assert summary["reason"] == "invalid_recorded_cost"


def test_runner_costs_keep_currencies_and_missing_values_separate():
    costs = cost_summary_from_mapping({"cost_usd": 0.2, "total_cost_cny": 1.3})
    assert costs["billable_cost_usd"] == 0.2
    assert costs["billable_cost_cny"] == 1.3
    unknown = cost_summary_from_mapping({"cost_usd": None, "total_cost_cny": None})
    assert unknown["available"] is False
    cny = cost_summary_from_mapping({"total_cost_cny": 1.3})
    usd = cost_summary_from_mapping({"cost_usd": 0.2})
    assert comparable_costs(cny, usd) == (None, None, None)
    assert comparable_costs(costs, cny) == (1.3, 1.3, "CNY")


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ({}, None),
        ({"passed": False}, 0.0),
        ({"passed": True}, 1.0),
        ({"reward": 0, "passed": True}, 0.0),
        ({"rewards": {"reward": 0.75}, "passed": True}, 0.75),
        ({"verifier_result": {"rewards": {"reward": 0}}, "passed": True}, 0.0),
        ({"reward": 0, "rewards": {"reward": 1}}, 0.0),
        ({"passed": "false"}, None),
        ({"passed": "true"}, None),
        ({"passed": 1}, None),
    ],
)
def test_baseline_missing_and_zero_reward_are_distinct(tmp_path, record, expected):
    path = tmp_path / "result.json"
    path.write_text(json.dumps(record))
    baseline = load_baseline_result(path, "example", "pair")
    assert baseline["baseline_reward"] == expected
    assert baseline["baseline_passed"] is (expected == 1.0)


@pytest.mark.parametrize("reward", [-1, 1.1, float("nan"), float("inf")])
def test_baseline_rejects_invalid_reward_consistently_with_live_runner(tmp_path, reward):
    path = tmp_path / "result.json"
    path.write_text(json.dumps({"reward": reward}))
    with pytest.raises(ValueError):
        load_baseline_result(path, "example", "pair")


def test_invalid_reward_file_does_not_override_valid_recorded_reward(tmp_path):
    (tmp_path / "result.json").write_text(json.dumps({"reward": 0.75}))
    (tmp_path / "verifier").mkdir()
    (tmp_path / "verifier" / "reward.txt").write_text("nan")
    baseline = load_baseline_result(tmp_path, "example", "pair")
    assert baseline["baseline_reward"] == 0.75


def test_feedback_does_not_compare_different_currencies(tmp_path):
    baseline_dir = tmp_path / "baseline"
    previous_dir = tmp_path / "previous"
    baseline_dir.mkdir()
    previous_dir.mkdir()
    baseline_path = baseline_dir / "result.json"
    previous_path = previous_dir / "result.json"
    baseline_path.write_text(json.dumps({"reward": 1, "cost_usd": 1}))
    previous_path.write_text(json.dumps({"reward": 1, "total_cost_cny": 0.5}))
    feedback = build_round_feedback(
        adaptation_mode="combo_adapted",
        round_index=2,
        original_instruction="Write result.csv.",
        seed_instruction="Write result.csv.",
        baseline=load_baseline_result(baseline_path, "example", "pair"),
        baseline_result=baseline_path,
        previous_result=previous_path,
        public_instruction="Write result.csv.",
        max_events=3,
    )
    assert feedback["baseline_billable_cost_usd"] == 1
    assert feedback["previous_billable_cost_cny"] == 0.5
    assert feedback["cost_delta_pct_vs_baseline"] is None
    assert feedback["failure_type"] == "missing_comparable_cost"


def test_published_prices_match_the_frozen_source_checksum():
    root = Path(__file__).resolve().parents[1]
    provenance = json.loads((root / "artifacts/scoring/provenance.json").read_text())
    prices = root / provenance["published_pricing_file"]
    expected = provenance["source_sha256"]["paper_recompute_20260713_price_config.json"]
    assert hashlib.sha256(prices.read_bytes()).hexdigest() == expected
