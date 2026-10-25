#!/usr/bin/env python3
"""Build Core30 and Final16 benchmark tables from archived run records."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from agentmeter.metrics.agentmeter_score import compute_ams
from agentmeter.paths import find_repository


def load_scoring_data(repository=None):
    """Load archived run records and calibration, validating the full experiment grid."""
    root = find_repository(repository)
    with (root / "artifacts/scoring/run_metrics.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    calibration = json.loads((root / "configs/paper_calibration_full_precision.json").read_text())
    validate_experiment_grid(rows, root)
    return rows, calibration


def validate_experiment_grid(rows, repository=None):
    """Reject missing, duplicated, or mispaired observations before scoring."""
    keys = [(r["dataset"], r["target"], r["source"], r["condition"], r["task_id"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate run key")
    root = find_repository(repository)
    core_tasks = set((root / "configs/task_lists/core30.public.txt").read_text().splitlines())
    opt_tasks = set(
        (root / "configs/task_lists/agentmeter_opt_final16.txt").read_text().splitlines()
    )
    core_targets = {r["target"] for r in rows if r["dataset"] == "core30"}
    targets = {"deepseek_v4_kimi_cli", "glm51_qwen_coder", "qwen36_codex", "qwen36_kimi_cli"}
    if len(core_targets) != 28:
        raise ValueError("Expected 28 Core30 targets")
    expected = {("core30", t, "", "Original", task) for t in core_targets for task in core_tasks}
    expected |= {("final16", t, "", "Original", task) for t in targets for task in opt_tasks}
    expected |= {
        ("final16", t, s, "Self" if s == t else "Cross", task)
        for t in targets
        for s in targets
        for task in opt_tasks
    }
    if set(keys) != expected:
        raise ValueError("Incomplete or unexpected experiment grid")
    strata = {}
    for r in rows:
        key = (r["dataset"], r["task_id"])
        if key in strata and strata[key] != r["stratum"]:
            raise ValueError("Inconsistent task stratum across configurations")
        strata[key] = r["stratum"]
    if Counter(s for (d, _), s in strata.items() if d == "core30") != {
        "Easy": 10,
        "Medium": 10,
        "Hard": 10,
    }:
        raise ValueError("Core30 must have 10 tasks in each stratum")


def summarize_run_outcomes(rows, calibration):
    """Aggregate AMS, rewards, passes, recorded costs, and accounting tokens."""
    # In balanced Cross/Pooled grids, each task-source is one observation.
    # Never average costs/rewards before thresholding, or average source AMS:
    # EFR multiplies quality, so those would implement different estimands.
    observations = [dict(r, task_id=r["source"] + "/" + r["task_id"]) for r in rows]
    score = compute_ams(observations, calibration)["AMS"]
    passes = sum(float(r["reward"]) == 1 for r in rows)
    return dict(
        AMS=score,
        n=len(rows),
        passes=passes,
        reward=sum(float(r["reward"]) for r in rows) / len(rows),
        cost=sum(float(r["cost_usd"]) for r in rows),
        tokens=sum(int(r["billable_component_tokens"]) for r in rows),
    )


def build_benchmark_tables(rows, calibration):
    """Group Core30 by target and Final16 by target and adaptation condition."""
    core = {}
    final = {}
    for target in sorted({r["target"] for r in rows if r["dataset"] == "core30"}):
        core[target] = summarize_run_outcomes(
            [r for r in rows if r["dataset"] == "core30" and r["target"] == target], calibration
        )
    for target in sorted({r["target"] for r in rows if r["dataset"] == "final16"}):
        final[target] = {}
        for condition in ["Original", "Self", "Cross", "Pooled"]:
            sub = [
                r
                for r in rows
                if r["dataset"] == "final16"
                and r["target"] == target
                and (
                    r["condition"] == condition
                    or condition == "Pooled"
                    and r["condition"] in {"Self", "Cross"}
                )
            ]
            final[target][condition] = summarize_run_outcomes(sub, calibration)
    return core, final


def render_example_comparison(rows, repository=None):
    """Pair every released example with its archived Original and Self result."""
    index = {
        (r["target"], r["task_id"], r["condition"]): r
        for r in rows
        if r["dataset"] == "final16" and r["condition"] in {"Original", "Self"}
    }
    lines = [
        "| Task / source pair | Reward: Original → Self | USD: Original → Self | Cost change |",
        "|:--|--:|--:|--:|",
    ]
    root = find_repository(repository)
    for path in sorted(
        (root / "artifacts/agentmeter_opt_final16/descriptions").glob(
            "*/*/optimized_instruction.md"
        ),
        key=lambda path: (path.parent.name, path.parent.parent.name),
    ):
        source, task = path.parent.parent.name, path.parent.name
        before, after = (index[(source, task, c)] for c in ["Original", "Self"])
        b, a = float(before["cost_usd"]), float(after["cost_usd"])
        change = f"{100 * (a / b - 1):+.1f}%" if b else "N/A"
        link = f"descriptions/{source}/{task}/"
        lines.append(
            f"| [{task} / {source}]({link}) | {float(before['reward']):.3f} → {float(after['reward']):.3f} | {b:.5f} → {a:.5f} | {change} |"
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agentmeter tables", description=__doc__)
    parser.add_argument(
        "--examples", action="store_true", help="Print the released Original/Self example pairs"
    )
    parser.add_argument("--repository", type=Path, help="AgentMeter research checkout")
    parser.add_argument(
        "--descriptive",
        action="store_true",
        help="Print reward, USD cost and source-transfer summaries",
    )
    args = parser.parse_args(argv)
    rows, calibration = load_scoring_data(args.repository)
    if args.descriptive:
        from .adaptation_comparison import print_adaptation_comparisons

        print_adaptation_comparisons(rows, calibration)
        return 0
    if args.examples:
        print(render_example_comparison(rows, args.repository))
        return 0
    core, final = build_benchmark_tables(rows, calibration)
    print("| Core30 target | Passes | Tokens/pass (M) | USD/pass | AMS |")
    print("|:--|--:|--:|--:|--:|")
    for target, r in sorted(core.items(), key=lambda item: -item[1]["AMS"]):
        tp = f"{r['tokens'] / r['passes'] / 1e6:.2f}" if r["passes"] else "N/A"
        cp = f"{r['cost'] / r['passes']:.3f}" if r["passes"] else "N/A"
        print(f"| {target} | {r['passes']}/{r['n']} | {tp} | {cp} | {r['AMS']:.3f} |")
    conditions = ["Original", "Self", "Cross", "Pooled"]
    print("\n| Final16 target | Original AMS | Self AMS | Cross-only AMS | Pooled AMS |")
    print("|:--|--:|--:|--:|--:|")
    for target, result in final.items():
        print(
            "| " + target + " | " + " | ".join(f"{result[c]['AMS']:.3f}" for c in conditions) + " |"
        )
    print(
        "| Macro | "
        + " | ".join(
            f"{sum(r[c]['AMS'] for r in final.values()) / len(final):.3f}" for c in conditions
        )
        + " |"
    )
    print(
        "\n840 Core30 + 320 Final16 observations. Pooled reuses Self/Cross, not new runs. "
        "Uses archived USD and full-precision calibration; no API calls. "
        "This recomputes results, not agent trajectories or description generation."
    )


if __name__ == "__main__":
    main()
