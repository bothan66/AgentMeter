# Reproduction guide

Install from the cloned repository with `python -m pip install -e .`.
The `agentmeter` command and `python -m agentmeter` expose the same interface.

| Workflow | Command | Inputs |
|:--|:--|:--|
| Recompute manuscript tables | `agentmeter tables` | Included 1,160 records and full-precision calibration |
| Inspect reward/cost summaries | `agentmeter tables --descriptive` | The same archived observations |
| Inspect four complete four-source examples | `agentmeter tables --examples` | 16 released pairs and their archived results |
| Score one condition | `agentmeter score --runs condition.csv` | Task ID, frozen stratum, reward and USD cost |
| Prepare pinned Harbor | `agentmeter setup` | Git, Python 3.12–3.13 and network access |
| Replay a paired example | `agentmeter compare SOURCE CONDITION TASK` | Harbor, Docker and provider credentials |
| Run a frozen task list | `agentmeter suite TASK_LIST` | Matching task checkout and target configuration |
| Construct a description | `agentmeter optimize --help` | Source task, trajectory and reflection API |

The release contains 16 executable tasks and all four source rewrites of
four tasks: `dm-csv-009`, `citation-check`, `csv-data-validator` and
`econ-detrending-correlation`. Archived scoring covers all 840 Core30 and 320 Final16
observations, including the 192 Cross outcomes.

## Recompute archived results

```bash
agentmeter tables
agentmeter tables --descriptive
agentmeter tables --examples
```

These commands use archived `cost_usd` and full-precision calibration without
repricing. The main table reproduces all 28 Core30 rows and the four targets'
Original/Pooled/Cross AMS at manuscript precision. The historical
`AgentMeterScore` field in legacy CSVs is distinct from manuscript AMS.
See [scoring inputs](../artifacts/scoring/README.md) and
[condition definitions](paper_alignment.md).

## Replay Original and optimized instructions

Follow [execution setup](external_dependencies.md) to prepare Harbor and
configure the target model and harness. Preview selection and launch:

```bash
agentmeter compare qwen36_codex original dm-csv-009 --dry-run
agentmeter compare qwen36_codex original dm-csv-009
agentmeter compare qwen36_codex optimized dm-csv-009
```

The source pair selects the released instruction; `AGENTMETER_MODEL` and
`AGENTMETER_AGENT` select the evaluation target. Omitting task IDs runs the
same released source-specific subset for Original and optimized conditions.
Each invocation creates a separate run directory. If setting
`AGENTMETER_JOBS_DIR` explicitly, give each condition a new directory.
Instruction snapshots, Harbor results, trajectories and verifier outputs
remain together under that run directory.

## Run Core30 or Full80

The frozen selections are
[`core30.public.txt`](../configs/task_lists/core30.public.txt) and
[`full80.txt`](../configs/task_lists/full80.txt). Supply a separate compatible
task checkout containing every selected ID:

```bash
export AGENTMETER_TASK_ROOT=/path/to/skillsbench/tasks
agentmeter suite configs/task_lists/core30.public.txt --dry-run
agentmeter suite configs/task_lists/core30.public.txt
# Or select the full benchmark:
agentmeter suite configs/task_lists/full80.txt
```

Repeat with each target configuration. Record task-level reward and billable
USD cost, then run `agentmeter score --runs condition.csv` using the frozen
strata from the study. The [scoring protocol](paper_alignment.md) defines the
required fields and aggregation rules.

## Generate a new trajectory-guided description

Install `python -m pip install -e '.[opt]'`, then follow
[AgentMeter-Opt](optimization.md). Construction consumes the Original task
and its saved source trajectory. Evaluate proposed instructions with the
unchanged task verifier before reward-first, cost-second selection and
Self/Cross evaluation.

## Reproduce from an installed wheel

The installed package includes the CLI and optimization modules. Data-driven
commands also need the research checkout; when running elsewhere, set:

```bash
export AGENTMETER_REPO_ROOT=/path/to/AgentMeter
python -m agentmeter tables
```

Use a repository commit ID when recording a reproduction, along with the
provider model ID, CLI version, task snapshot, generation settings, timeouts,
pricing and cache-accounting rules. Provider revisions and sampling can
change new executions even when the archived result tables reproduce exactly.

## Validation

```bash
python -m pip install -e '.[dev]'
ruff check src/agentmeter tests
ruff format --check src/agentmeter tests
pytest -q
python tests/check_public_release.py
```

CI checks package installation outside the source directory, table
reproduction, task/description consistency, execution preflight, preservation
checks and provider usage normalization. Proxy protocol tests use a local
fixture upstream. A live API probe (`agentmeter probe`) and Harbor task run
exercise provider connectivity and container execution separately.
