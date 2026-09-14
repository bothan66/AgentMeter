# Manuscript scoring and experiment protocol

## AMS

For each observed-effort stratum s, compute:

```text
TQ_s = mean(reward)
AUBQC_s = mean over cost budgets b of mean(reward * [cost_usd <= b])
EFR_s = mean([reward == 0 and cost_usd > zero_reward_threshold_s])
S_s = (0.6 * TQ_s + 0.4 * AUBQC_s) * (1 - EFR_s)
AMS = (S_Easy + S_Medium + S_Hard) / 3
```

All runs contribute to each denominator, including failures. Partial rewards
contribute to TQ and AUBQC and are not expensive zero-reward failures.
Budget inclusion uses <=; expensive failures use >. Strata receive equal
weight, irrespective of their task counts.

```bash
python scripts/compute_paper_ams.py --runs condition.csv
```

Supply task_id,stratum,reward,cost_usd for one configuration/condition, with
one row per task. Use the frozen observed-effort assignment from the study,
not task.toml difficulty or labels inferred from a new run. Missing strata
and duplicate task IDs are rejected. The CLI does not define a repeated-run
aggregation policy or compute Pooled automatically.

configs/paper_calibration.json transcribes the rounded budget/threshold
values in the supplementary table. It implements the manuscript formula,
but threshold-adjacent runs can differ from original full-precision scoring.
Exact historical table reconstruction still requires task effort assignments,
full-precision calibration and missing run-level records. The legacy metrics
in metrics/agentmeter.py and metrics/cost.py are not final-paper AMS.

## Currency and archived scores

Public descriptive tables use USD at the paper's frozen conversion:
1 CNY = 0.1471 USD. Raw CSVs retain original CNY fields. This is a historical
accounting convention, not a current price recommendation.

self_summary.csv's AgentMeterScore is an archived legacy field, not the
manuscript score; it must not be relabeled as AMS. The public table script
omits it. GLM Original cost converts to approximately USD 3.370 from the
released aggregate, while the paper table lists 3.371. This small discrepancy
remains unresolved and is not silently adjusted to match the paper.

## Conditions and counts

- Original: 16 tasks × 4 targets = 64 executions.
- Self: 16 × 4 = 64 source-matched outcomes.
- Cross: 16 × 4 sources × 3 other targets = 192 executions.
- Main matrix: 320 executions. Pooled equally weights the four source
  outcomes; Cross-only equally weights the three other-source outcomes.
- Generic: 16 public-only descriptions × 4 targets = 64 additional executions.
- Adapted-1: 10,000 offline assignments, selecting one source description per
  task and sharing it across targets; not 10,000 new API experiments.

Generic records/descriptions and an executable Adapted-1 reconstruction are
not included in this compact release. The selected 16 description examples
are a subset of the 64 constructed variants, not the full 16-task × 4-source
grid. Do not confuse this showcase with the complete study.

The construction model is Qwen3.7-Max. Evaluation harness names are Claude
Code, Codex CLI, Kimi Code CLI, and Qwen Code. A GLM-5.3-Flash smoke run is a
compatibility check, not a replacement for the paper's GLM-5.1 results.
