#!/usr/bin/env python3
"""Recompute descriptive results from the released CSVs (no API required)."""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CNY_TO_USD = 0.1471  # Manuscript frozen rate, not a live exchange rate.


def main():
    result_dir = ROOT / 'artifacts/agentmeter_opt_final16/results'
    with (result_dir / 'self_summary.csv').open(newline='') as f:
        rows = list(csv.DictReader(f))
    print('| Target | Condition | N | Mean reward | Full passes | Total cost (USD) | Input tokens | Cached input | Output tokens |')
    print('|:--|:--|--:|--:|--:|--:|--:|--:|--:|')
    for r in rows:
        print(f"| {r['combo']} | {r['variant']} | {r['n_tasks']} | {float(r['mean_reward']):.4f} | {r['full_pass_count']} | {float(r['total_cost_cny']) * CNY_TO_USD:.4f} | {r['total_input_tokens']} | {r['total_cached_tokens']} | {r['total_output_tokens']} |")
    groups = defaultdict(list)
    with (result_dir / 'cross_task_results.csv').open(newline='') as f:
        for r in csv.DictReader(f):
            groups[(r['source_combo'], r['target_combo'])].append(r)
    print('\n| Source → Target | N | Original reward | Cross reward | Cost change |')
    print('|:--|--:|--:|--:|--:|')
    for (source, target), items in sorted(groups.items()):
        before = sum(float(r['baseline_cost_cny_model_specific']) for r in items)
        after = sum(float(r['optimized_cost_cny_model_specific']) for r in items)
        br = sum(float(r['baseline_reward']) for r in items) / len(items)
        ar = sum(float(r['optimized_reward']) for r in items) / len(items)
        delta = f'{100 * (after / before - 1):+.2f}%' if before else 'N/A'
        print(f'| {source} → {target} | {len(items)} | {br:.4f} | {ar:.4f} | {delta} |')
    print('\nCosts convert archived CNY at the manuscript frozen rate 1 CNY = 0.1471 USD, not current prices. Cached input is a subset of input; do not add it again. Cross baselines repeat across sources. This table does not recompute paper AMS.')


if __name__ == '__main__':
    main()
