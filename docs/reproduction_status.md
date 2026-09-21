# Reproduction guide

| Workflow | Entry point | Inputs |
|:--|:--|:--|
| Inspect archived results | `scripts/reproduce_artifact_table.py` | Included Self/Cross CSVs |
| Score task-level results | `scripts/compute_paper_ams.py` | One-condition CSV with task ID, effort stratum, reward and USD cost |
| Replay an example | `scripts/run_final16_condition.sh` | Selected source, target configuration and provider credentials |
| Run Core30 / Full80 | `scripts/run_harbor_suite.sh` | Frozen task list and matching task checkout |
| Generate a rewrite | `agentmeter_opt/optimize_instruction.py` | Original task, source trajectory and reflection API |

The release includes 16 executable task bundles and 16 selected rewritten
descriptions. Each source configuration contributes four examples.
Full-study Self aggregates and 192 Cross records are also included.

## Scoring and accounting

Public tables display USD using the paper's fixed conversion,
1 CNY = 0.1471 USD. Raw CSV fields retain CNY. Use the manuscript scorer in
`metrics/paper.py` for AMS; the historical `AgentMeterScore` CSV field and
legacy diagnostic functions are not the final manuscript metric.

The included calibration file records published rounded values. Historical
table reconstruction additionally requires original effort labels,
full-precision calibration and run-level records. See
[scoring and condition definitions](paper_alignment.md).

## Runtime setup

Follow [execution dependencies](external_dependencies.md) to install the
pinned Harbor version and both patches. Export the provider API key and base
URL before running. Keep task outputs and temporary files on a disk with
adequate space; Docker layer storage is configured separately.

The real API self-check passed with GLM-5.3-Flash through CLIProxyAPI on
2026-09-14: HTTP 200, completed response with output text, 17 input and 85
output tokens. Run `python scripts/probe_responses.py` with provider variables
exported to check your own endpoint.

The `markdown-table-generator` Original smoke run also completed on
2026-09-14 with GLM-5.3-Flash × Codex 0.153.0 through CLIProxyAPI.
Harbor recorded no runtime exception and saved the trajectory, usage and
verifier output. Total elapsed time was approximately 10 minutes 36 seconds,
including about 4 minutes 10 seconds for CLI setup and 3 minutes 44 seconds
for verification (mostly dependency downloads). Usage was 77,952 input tokens
(including 1,024 cached) and 4,953 output tokens.

The verifier passed 10/11 checks and assigned reward 0: its summary test
expects `6,219,500`, whereas the generated report and agent's CSV-sum check
give `6,419,800`. The bundled verifier remains unchanged. This run validates
execution and result recording; it is not an additional paper result.

`provider-auth.patch` configures the credential environment variable and
preserves full custom-provider model IDs. The validated GLM route uses
CLIProxyAPI for Responses-to-upstream conversion; the direct upstream route
rejected the tested Responses inputs.

The bundled `lru-cache-with-ttl` reference solution previously reached the
verifier with 14/15 tests passing; `test_evict_all_expired_picks_oldest` failed.
Use the original task unchanged when comparing historical results.

## Run Core30 or Full80

The exact task selections are frozen in:

- [`configs/task_lists/core30.public.txt`](../configs/task_lists/core30.public.txt)
- [`configs/task_lists/full80.txt`](../configs/task_lists/full80.txt)

Point `AGENTMETER_TASK_ROOT` to an upstream SkillsBench-compatible task checkout
and execute one target pair over either frozen task list:

```bash
export AGENTMETER_TASK_ROOT=/path/to/skillsbench

bash scripts/run_harbor_suite.sh configs/task_lists/core30.public.txt
# or
bash scripts/run_harbor_suite.sh configs/task_lists/full80.txt
```

Repeat for each target configuration to generate new Harbor rewards and usage
records. Compute the manuscript-defined score using
`python scripts/compute_paper_ams.py --runs condition.csv`, with one row per
task: `task_id,stratum,reward,cost_usd`. See [scoring protocol](paper_alignment.md)
for required effort labels, rounded calibration limits, and historical data gaps.

## Generate a new trajectory-guided description

To regenerate a description from an Original trajectory rather than replaying
a released one:

```bash
python -m pip install -e '.[opt]'
python agentmeter_opt/optimize_instruction.py \
  --task-id regex-log \
  --task-root benchmark_tasks/terminal_bench \
  --baseline-result /path/to/original/agent/trajectory.json \
  --combo qwen36_codex \
  --model 'Qwen3.6+' \
  --cli codex \
  --adaptation-mode combo_adapted \
  --candidate-only \
  --offline-until-accepted \
  --max-metric-calls 5 \
  --reflection-model openai/qwen3.7-max \
  --out-dir generated_reports/example
```

The paper uses Qwen3.7-Max for construction. Set the reflection model's
provider credentials and use its corresponding model identifier; the
construction provider may differ from the evaluation provider. Replace
`--baseline-result` with the saved Original trajectory from the preceding
run. Run these commands from the repository root.

This command generates a candidate only. Evaluate it with the unchanged task
verifier before reward-first, cost-second selection, then freeze the selected
description before Self or Cross evaluation. Review the automatic gate's
decisions against the original requirements when selecting candidates.

## Validation

```bash
python -m pip install -e '.[dev]'
pytest -q
python scripts/public_release_check.py
```

Local tests cover metric behavior, task/description consistency and launcher
output handling. Mock pipeline checks exercise report generation.
Candidate generation and task evaluation are separate steps: evaluate a
candidate with the original verifier before source-side selection and freezing.
[Description notes](description_notes.md) document example-specific interpretation.
