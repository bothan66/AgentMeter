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

## Provenance and reuse

These pairs document AgentMeter-Opt's changes to benchmark task descriptions:

- `baseline_instruction.md` is the collected Original, byte-identical to the
  corresponding bundled task's `instruction.md`; it is not AgentMeter-authored.
- `optimized_instruction.md` is the historical AgentMeter-Opt modification of
  that description. Its parent directories identify the source model–harness
  pair and task ID. The source pair is not necessarily the evaluation target.
- Environments, input artifacts, and verifiers are not rewritten by this
  description intervention. The released historical text is not edited for
  presentation; interpretation notes are kept separately.

| Local task collection | Examples in this catalog | Source attribution |
|:--|:--|:--|
| `skillsbench` | citation-check, econ-detrending-correlation, sales-pivot-analysis, virtualhome-agent-planning, pddl-tpp-planning, xlsx-recover-data | [SkillsBench](https://github.com/benchflow-ai/skillsbench) |
| `terminal_bench` | regex-log, async-task-scheduler, lru-cache-with-ttl, markdown-table-generator, bash-script-debugger | Local Terminal-Bench-compatible collection; compatibility is not a claim of an official upstream snapshot |
| `da_code` | dm-csv-009, dm-csv-011 | Local [DA-Code](https://github.com/yiyihum/da-code)-compatible collection |

Original content and retained material in rewrites remain subject to their
applicable upstream terms, not automatically the repository's MIT license.
Source attribution does not replace license compliance. Exact historical
upstream revisions and any task-specific exceptions still need confirmation
before public redistribution of the affected files.

A separately licensed skill bundled inside a task environment is distinct
from that task's instruction pair: its restrictions are not evidence that
every rewritten description is restricted. See the
[third-party notices](../../THIRD_PARTY_NOTICES.md) for the known XLSX skill
exception. The catalog preserves the description examples independently of
that environment-file review.

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
outcomes cannot be recovered from the aggregate Self CSV, but are available
in the newly released [run-level scoring records](../scoring/README.md).

Run `python scripts/reproduce_artifact_table.py` to summarize those records.
Raw costs are archived CNY; the script displays USD at the paper's frozen
rate of 0.1471 USD/CNY. These are not current prices. The score field has not been
reconciled with manuscript AMS; use `scripts/reproduce_paper_tables.py` for
the manuscript metric from run-level USD inputs. Full optimized-grid replay requires the
unreleased descriptions.
