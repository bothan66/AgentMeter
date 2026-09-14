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
exported to check your own endpoint. The Harbor task rerun is being verified;
API connectivity and full task verification are separate checks.

`provider-auth.patch` configures the credential environment variable and
preserves full custom-provider model IDs. The validated GLM route uses
CLIProxyAPI for Responses-to-upstream conversion; the direct upstream route
rejected the tested Responses inputs.

The bundled `lru-cache-with-ttl` reference solution previously reached the
verifier with 14/15 tests passing; `test_evict_all_expired_picks_oldest` failed.
Use the original task unchanged when comparing historical results.

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
