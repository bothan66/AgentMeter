# Main-table reproduction data

Run from the repository root:

```bash
agentmeter tables
```

This recomputes the 28-row Core30 results and the Final16 description-condition
AMS table. Regression tests compare every Core30 pass count, tokens/pass,
USD/pass and AMS to the released paper table, and Original/Pooled/Cross AMS
for all four Final16 targets to manuscript display precision.

## Contents

| Material | Scope |
|:--|:--|
| `run_metrics.csv` | 840 Core30 rows + 64 Final16 Original + 64 Self + 192 Cross = 1,160 observations |
| `diagnostics.csv` | Same 1,160 run keys; archived steps, tool calls and alternate cache-read counter |
| `provenance.json` | Original archive filenames and SHA256 checksums, plus extraction policy |
| [`paper_calibration_full_precision.json`](../../configs/paper_calibration_full_precision.json) | Frozen USD budget grids and expensive-failure thresholds |
| [`paper_model_pricing.json`](../../configs/paper_model_pricing.json) | Unchanged model-rate snapshot from the study archive; not a current price list |

Numeric strings are retained from the frozen archive. Private machine paths,
exception text, credentials, trajectories, and task documents are not included
in this data table. No new model executions were performed to create it.

## Accounting and aggregation

- `stratum` is the historical observed-effort assignment, not task metadata
  difficulty. Core30 has a balanced 10/10/10 assignment; Final16 uses its
  tasks' Full80 assignments. The same task may therefore have different
  strata across these two experiments.
- `cost_usd` is the archived per-run USD cost. Both table views use it
  unchanged, without reconversion or repricing. Historical accounting uses
  `1 / 6.7972` USD/CNY where currency conversion applies.
- `input_tokens` retains the archive's raw prompt counter. Some Claude
  bridges report fresh input separately from cache reads/writes; others
  include cache tokens in prompt input. `billable_component_tokens` retains
  the archived accounting total used for tokens/pass. `cached_input_tokens`
  retains the primary archived cache-hit counter. The alternate
  `cache_read_input_tokens` is in `diagnostics.csv`; the two are not additive
  and were extracted through different fields. Neither is silently rewritten.
- `cache_creation_input_tokens` displays the archived counter for Claude
  Code targets only (210 rows). It is blank for other harnesses by display
  convention, not a claim of zero cache creation or absence of upstream
  measurements. Archived zero values are retained, including zeros produced
  by the historical extractor's missing-field default. This display selection
  does not change `cost_usd` or `billable_component_tokens`, and must not be
  used to infer a new billing formula. The table reproduces scoring from
  recorded costs, not a fresh provider invoice calculation.
- `diagnostics.csv` preserves `steps` and `tool_calls` unchanged. Harnesses
  can record different granularities and missing counters can appear as zero;
  these fields are not used in the main result tables or AMS.
- All archived valid-run rows are retained, including zero rewards and
  exceptions. `has_exception` records presence, not a new validity filter.
  Core30 contains 66 such exception-marked observations.
- Cross baseline copies are omitted: the 64 Original observations are
  counted once. Self/Cross identify the rewrite source and evaluation target.
- Pooled uses all four sources per task; Cross-only uses the three other
  sources. These are balanced observation mixtures, not additional runs and
  not averages of source-level AMS. Threshold each observation before
  aggregating TQ, AUBQC and EFR within the frozen strata.

The released 12 description examples remain a showcase subset. Scoring the
complete archived grid does not require releasing all descriptions or traces;
regenerating every execution does. This package does not reconstruct Generic,
Adapted-1, or the complete Full80 experiment table.
