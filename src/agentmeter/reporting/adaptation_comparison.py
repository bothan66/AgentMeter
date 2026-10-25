#!/usr/bin/env python3
"""Compare Original, Self, and Cross adaptation outcomes from archived records."""

from .benchmark_tables import summarize_run_outcomes


def build_adaptation_comparisons(rows, calibration):
    """Return Original/Self summaries and paired cross-source transfer outcomes."""
    rows = [r for r in rows if r["dataset"] == "final16"]
    targets = sorted({r["target"] for r in rows})
    summary = []
    transfers = []
    for target in targets:
        for condition in ["Original", "Self"]:
            selected = [r for r in rows if r["target"] == target and r["condition"] == condition]
            summary.append(
                dict(
                    target=target,
                    condition=condition,
                    **summarize_run_outcomes(selected, calibration),
                )
            )
        baseline = [r for r in rows if r["target"] == target and r["condition"] == "Original"]
        before = summarize_run_outcomes(baseline, calibration)
        for source in targets:
            if source == target:
                continue
            selected = [
                r
                for r in rows
                if r["target"] == target and r["source"] == source and r["condition"] == "Cross"
            ]
            after = summarize_run_outcomes(selected, calibration)
            transfers.append(dict(source=source, target=target, before=before, after=after))
    return summary, transfers


def print_adaptation_comparisons(rows, calibration):
    """Print the descriptive comparisons using the same archived billing data."""
    summary, transfers = build_adaptation_comparisons(rows, calibration)
    print(
        "| Target | Condition | N | Mean reward | Full passes | Total cost (USD) | Archived accounting tokens |"
    )
    print("|:--|:--|--:|--:|--:|--:|--:|")
    for r in summary:
        print(
            f"| {r['target']} | {r['condition']} | {r['n']} | {r['reward']:.4f} | {r['passes']} | {r['cost']:.5f} | {r['tokens']} |"
        )
    print(
        "\n| Source → Target | N | Original reward | Cross reward | Original USD | Cross USD | Cost change |"
    )
    print("|:--|--:|--:|--:|--:|--:|--:|")
    for r in transfers:
        b, a = r["before"], r["after"]
        change = f"{100 * (a['cost'] / b['cost'] - 1):+.2f}%" if b["cost"] else "N/A"
        print(
            f"| {r['source']} → {r['target']} | {a['n']} | {b['reward']:.4f} | {a['reward']:.4f} | {b['cost']:.5f} | {a['cost']:.5f} | {change} |"
        )
    print(
        "\nUses archived cost_usd without reconversion or repricing. "
        "Original baselines repeat for comparison, not as additional executions."
    )
