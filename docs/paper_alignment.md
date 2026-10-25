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
agentmeter score --runs condition.csv
```

Supply task_id,stratum,reward,cost_usd for one configuration/condition, with
one row per task. Use the frozen observed-effort assignment from the study,
not task.toml difficulty or labels inferred from a new run. Missing strata
and duplicate task IDs are rejected. The CLI does not define a repeated-run
aggregation policy or compute Pooled automatically.

The default `configs/paper_calibration_full_precision.json` preserves the
archived USD budgets and thresholds at full precision.
`artifacts/scoring/run_metrics.csv` includes the frozen effort strata and
run-level inputs for 840 Core30 and 320 Final16 observations.

```bash
agentmeter tables
```

This command reproduces all 28 Core30 table rows and the four targets'
Original/Pooled/Cross AMS at manuscript display precision. For Cross/Pooled,
each task-source is an observation in a complete balanced grid; apply budget
and failure thresholds before aggregation, not to averaged costs. Pooled
is not the mean of separately computed source AMS values, because EFR
multiplies the quality term. See [data provenance](../artifacts/scoring/README.md).
The implementation is [`agentmeter.metrics.agentmeter_score`](../src/agentmeter/metrics/agentmeter_score.py).

## Currency and archived scores

Both table views use archived `cost_usd` without repricing. The
historical conversion is 1 / 6.7972 USD/CNY, approximately 0.1471.
This is historical accounting, not current pricing.
The original model-rate snapshot is included unchanged in
[`paper_model_pricing.json`](../configs/paper_model_pricing.json); table
reproduction still reads recorded per-run costs rather than repricing tokens.

For example, GLM Original totals USD 3.37084 in the archived run-level
records, rounding to the paper's 3.371. Using recorded USD costs avoids a
second conversion at a rounded exchange rate.

## Conditions and counts

Self is a source-side diagnostic of description adaptation. Following the
paper's retention rule, a candidate must improve source reward or preserve it
at lower cost; otherwise the Original description is retained. Candidates are
ordered by reward, then billable cost, with smaller task-preserving edits as a
tie-breaker. Self therefore reflects source-outcome selection, not independent
evidence of transfer. Descriptions are frozen before evaluating other targets;
Cross-only and the shared, equal-weight Pooled set test beyond source matching.

- Original: 16 tasks × 4 targets = 64 executions.
- Self: 16 × 4 = 64 source-matched outcomes.
- Cross: 16 × 4 sources × 3 other targets = 192 executions.
- Main matrix: 320 executions. Pooled equally weights the four source
  outcomes; Cross-only equally weights the three other-source outcomes.
- Generic: 16 public-only descriptions × 4 targets = 64 additional executions.
- Adapted-1: 10,000 offline assignments, selecting one source description per
  task and sharing it across targets; not 10,000 new API experiments.

Generic records/descriptions and an executable Adapted-1 reconstruction are
not included in this compact release. The description showcase contains all
four source variants for each of four tasks (16 variants), a task-complete
subset of the 64 constructed variants, not the full 16-task × 4-source grid.

The construction model is Qwen3.7-Max. Evaluation harness names are Claude
Code, Codex CLI, Kimi Code CLI, and Qwen Code. A GLM-5.3-Flash smoke run is a
compatibility check, not a replacement for the paper's GLM-5.1 results.
