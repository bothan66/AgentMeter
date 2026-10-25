"""Benchmark table reproduction, adaptation comparisons, and experiment-grid validation."""

import csv
from copy import deepcopy

import pytest

from agentmeter.paths import find_repository
from agentmeter.reporting.adaptation_comparison import build_adaptation_comparisons
from agentmeter.reporting.benchmark_tables import (
    build_benchmark_tables,
    load_scoring_data,
    render_example_comparison,
    validate_experiment_grid,
)

ROOT = find_repository()


def short_pair(target):
    model, cli = target.split("__")
    model = {
        "Qwen3.6+": "Qwen",
        "MiniMax-M2.5": "MM",
        "GLM-5.1": "GLM",
        "DeepSeek-v4-pro": "DS",
        "gpt-5.3-codex": "GPT",
        "claude-sonnet-4-6": "Claude",
        "gemini-3.5-flash": "Gem.",
    }[model]
    cli = {
        "kimi-cli": "kimi",
        "qwen-coder": "qwen",
        "Codex": "Codex",
        "codex": "Codex",
        "Claude_Code": "Claude",
        "claude-code": "Claude",
    }[cli]
    return f"{model}/{cli}"


def test_recompute_all_core30_paper_rows():
    core, _ = build_benchmark_tables(*load_scoring_data())
    with (ROOT / "artifacts/core30_paper_results.csv").open() as f:
        reference = {r["pair"]: r for r in csv.DictReader(f)}
    assert len(core) == len(reference) == 28
    for target, r in core.items():
        ref = reference[short_pair(target)]
        assert r["passes"] == int(ref["full_pass_tasks"])
        assert round(r["AMS"], 3) == float(ref["ams"])
        assert round(r["tokens"] / r["passes"] / 1e6, 2) == float(ref["tokens_per_pass_million"])
        assert round(r["cost"] / r["passes"], 3) == float(ref["usd_per_pass"])


def test_final16_matches_manuscript():
    _, final = build_benchmark_tables(*load_scoring_data())
    expected = {
        "qwen36_kimi_cli": (0.353, 0.470, 0.457),
        "qwen36_codex": (0.250, 0.457, 0.411),
        "deepseek_v4_kimi_cli": (0.341, 0.457, 0.438),
        "glm51_qwen_coder": (0.389, 0.446, 0.429),
    }
    for target, values in expected.items():
        assert (
            tuple(round(final[target][c]["AMS"], 3) for c in ["Original", "Pooled", "Cross"])
            == values
        )
        assert [final[target][c]["n"] for c in ["Original", "Self", "Cross", "Pooled"]] == [
            16,
            16,
            48,
            64,
        ]


def test_all_example_results_match_catalog():
    rows, _ = load_scoring_data()
    table = render_example_comparison(rows)
    assert len(table.splitlines()) == 18  # header + separator + four tasks × four sources
    assert table in (ROOT / "artifacts/agentmeter_opt_final16/README.md").read_text()


def test_cache_creation_display_scope():
    rows, _ = load_scoring_data()
    cc_rows = 0
    for row in rows:
        value = row["cache_creation_input_tokens"]
        if row["target"].endswith(("__Claude_Code", "__claude-code")):
            cc_rows += 1
            assert value != "" and int(value) >= 0
        else:
            assert value == ""  # Not displayed, not measured zero.
    assert cc_rows == 210


def test_scoring_records_exclude_auxiliary_counters():
    rows, _ = load_scoring_data()
    assert not {"steps", "tool_calls", "cache_read_input_tokens", "has_exception"} & rows[0].keys()


def test_descriptive_tables_use_same_costs_as_main_tables():
    inputs = load_scoring_data()
    _, final = build_benchmark_tables(*inputs)
    summary, transfers = build_adaptation_comparisons(*inputs)
    assert len(summary) == 8 and len(transfers) == 12
    for r in summary:
        ref = final[r["target"]][r["condition"]]
        assert r["cost"] == ref["cost"] and r["tokens"] == ref["tokens"]
    for target in final:
        selected = [r for r in transfers if r["target"] == target]
        assert sum(r["after"]["cost"] for r in selected) == pytest.approx(
            final[target]["Cross"]["cost"]
        )
        assert all(r["before"]["cost"] == final[target]["Original"]["cost"] for r in selected)


def test_reject_incomplete_duplicate_or_inconsistent_grid():
    rows, _ = load_scoring_data()
    for invalid in [rows[:-1], rows + [rows[0]]]:
        with pytest.raises(ValueError):
            validate_experiment_grid(invalid)
    altered = deepcopy(rows)
    altered[0]["stratum"] = "Hard" if altered[0]["stratum"] != "Hard" else "Easy"
    with pytest.raises(ValueError):
        validate_experiment_grid(altered)
