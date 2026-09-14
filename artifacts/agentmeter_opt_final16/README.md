# Selected description clarifications

Four examples per source configuration: 16 evaluated description pairs covering
13 distinct tasks. The collection illustrates different forms of trajectory-guided adaptation. The full 64-description set
is not included. All released instructions retain their historical wording.

| Source | Examples |
|:--|:--|
| qwen36_codex | [citation-check](descriptions/qwen36_codex/citation-check/), [econ-detrending-correlation](descriptions/qwen36_codex/econ-detrending-correlation/), [regex-log](descriptions/qwen36_codex/regex-log/), [sales-pivot-analysis](descriptions/qwen36_codex/sales-pivot-analysis/) |
| qwen36_kimi_cli | [async-task-scheduler](descriptions/qwen36_kimi_cli/async-task-scheduler/), [lru-cache-with-ttl](descriptions/qwen36_kimi_cli/lru-cache-with-ttl/), [markdown-table-generator](descriptions/qwen36_kimi_cli/markdown-table-generator/), [dm-csv-011](descriptions/qwen36_kimi_cli/dm-csv-011/) |
| deepseek_v4_kimi_cli | [virtualhome-agent-planning](descriptions/deepseek_v4_kimi_cli/virtualhome-agent-planning/), [pddl-tpp-planning](descriptions/deepseek_v4_kimi_cli/pddl-tpp-planning/), [markdown-table-generator](descriptions/deepseek_v4_kimi_cli/markdown-table-generator/), [dm-csv-009](descriptions/deepseek_v4_kimi_cli/dm-csv-009/) |
| glm51_qwen_coder | [bash-script-debugger](descriptions/glm51_qwen_coder/bash-script-debugger/), [xlsx-recover-data](descriptions/glm51_qwen_coder/xlsx-recover-data/), [markdown-table-generator](descriptions/glm51_qwen_coder/markdown-table-generator/), [dm-csv-009](descriptions/glm51_qwen_coder/dm-csv-009/) |

## What the examples cover

| Source | Example focus |
|:--|:--|
| Qwen × Codex | Citation normalization, economic input structure, regex output contracts, report organization |
| Qwen × Kimi | Scheduler lifecycle, cache API behavior, report formatting, CSV schemas |
| DeepSeek × Kimi | Planning output syntax, completion criteria, public file references |
| GLM × Qwen | Bug-fix deliverables, spreadsheet value types, report templates |

Each directory contains the Original and evaluated rewritten instruction.
See [description notes](../../docs/description_notes.md) for task-specific
interpretation and the public artifacts referenced by the examples.

## Run an example

From the repository root, after configuring Harbor and provider credentials:

```bash
bash scripts/run_final16_condition.sh qwen36_codex original regex-log
bash scripts/run_final16_condition.sh qwen36_codex optimized regex-log
```

The source argument selects the description; environment variables select
the target model and harness. Use different output directories for Original
and optimized runs if setting `AGENTMETER_JOBS_DIR` explicitly.
Docker and provider access are required.

## Historical results

`results/self_summary.csv` contains full-study Original/Self aggregates.
`results/cross_task_results.csv` contains 192 Cross outcomes, filterable by
task and source; `results/cross_summary.csv` contains pair aggregates.
These are not results on this selected showcase alone. Per-example Self
outcomes cannot be recovered from the aggregate Self CSV.

Run `python scripts/reproduce_artifact_table.py` to summarize those records.
Raw costs are archived CNY; the script displays USD at the paper's frozen
rate of 0.1471 USD/CNY. These are not current prices. The score field has not been
reconciled with manuscript AMS. Full optimized-grid replay requires the
unreleased descriptions.
