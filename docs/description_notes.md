# Description interpretation notes

Technical notes for the selected historical instruction pairs. See the
[example catalog](../artifacts/agentmeter_opt_final16/README.md) for files and replay commands.

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
[author schema](../benchmark_tasks/da_code/dm-csv-009/environment/sample_result.csv),
[ranking guidance](../benchmark_tasks/da_code/dm-csv-009/environment/guidance.txt),
and [bike schema](../benchmark_tasks/da_code/dm-csv-011/environment/sample_result.csv).

These task IDs contain historical names: for example, sales-pivot-analysis
actually asks for a demographic workbook. Examples follow the task content,
not an inferred interpretation of the ID.
