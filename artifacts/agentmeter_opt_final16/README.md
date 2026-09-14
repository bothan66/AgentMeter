# Selected description clarifications

Four examples per source configuration: 16 evaluated description pairs covering
13 distinct tasks. Selection prioritizes varied task types and public
requirements over repeated CSV cases. These are illustrative, not randomly
sampled or chosen to establish aggregate gains. The full 64-description set
is not included. All released instructions retain their historical wording.

| Source | Examples |
|:--|:--|
| qwen36_codex | [citation-check](descriptions/qwen36_codex/citation-check/), [econ-detrending-correlation](descriptions/qwen36_codex/econ-detrending-correlation/), [regex-log](descriptions/qwen36_codex/regex-log/), [sales-pivot-analysis](descriptions/qwen36_codex/sales-pivot-analysis/) |
| qwen36_kimi_cli | [async-task-scheduler](descriptions/qwen36_kimi_cli/async-task-scheduler/), [lru-cache-with-ttl](descriptions/qwen36_kimi_cli/lru-cache-with-ttl/), [markdown-table-generator](descriptions/qwen36_kimi_cli/markdown-table-generator/), [dm-csv-011](descriptions/qwen36_kimi_cli/dm-csv-011/) |
| deepseek_v4_kimi_cli | [virtualhome-agent-planning](descriptions/deepseek_v4_kimi_cli/virtualhome-agent-planning/), [pddl-tpp-planning](descriptions/deepseek_v4_kimi_cli/pddl-tpp-planning/), [markdown-table-generator](descriptions/deepseek_v4_kimi_cli/markdown-table-generator/), [dm-csv-009](descriptions/deepseek_v4_kimi_cli/dm-csv-009/) |
| glm51_qwen_coder | [bash-script-debugger](descriptions/glm51_qwen_coder/bash-script-debugger/), [xlsx-recover-data](descriptions/glm51_qwen_coder/xlsx-recover-data/), [markdown-table-generator](descriptions/glm51_qwen_coder/markdown-table-generator/), [dm-csv-009](descriptions/glm51_qwen_coder/dm-csv-009/) |

## How to read these examples

| Source | Main changes | Interpretation boundaries |
|:--|:--|:--|
| Qwen × Codex | Citation cleaning, economic input layout, raw-regex output, and report sheet structure | Regex uses the original public read/apply example, without lookaround recipes. Economic file-layout claims require checking the workbooks. The report clarifies merging and unique-region counts. |
| Qwen × Kimi | Scheduler lifecycle, cache expiry semantics, report formatting, and CSV schema | Scheduler/cache variants strengthen underspecified API behavior. Markdown adds stricter currency formatting for table cells; distinguish this from pure reorganization. |
| DeepSeek × Kimi | Planning output syntax, report completion, and ranking-file paths | Planning variants tighten formatting. The Markdown completion sentence can affect stopping behavior, but does not prohibit testing. |
| GLM × Qwen | Bug-fix submission, numeric spreadsheet output, Markdown template, and author template fields | Bash retains the original public test command. XLSX adds preservation constraints. Markdown specifies exactly three sections. |

No selected variant explicitly prohibits testing or verification. This is not
a formal task-equivalence certification. More varied examples do not establish
that every rewrite in the full study is valid, or that all observed savings
come from clarification alone.

Each directory includes the original and evaluated rewritten instruction.
For the remaining CSV examples, public evidence includes:
[author schema](../../benchmark_tasks/da_code/dm-csv-009/environment/sample_result.csv),
[ranking guidance](../../benchmark_tasks/da_code/dm-csv-009/environment/guidance.txt),
and [bike schema](../../benchmark_tasks/da_code/dm-csv-011/environment/sample_result.csv).

These task IDs contain historical names: for example, sales-pivot-analysis
actually asks for a demographic workbook. Examples follow the task content,
not an inferred interpretation of the ID.

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
Costs are archived CNY, not current prices. The score field has not been
reconciled with manuscript AMS. Full optimized-grid replay requires the
unreleased descriptions.
