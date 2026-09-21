# Reading the description adaptations

Technical notes for the selected historical instruction pairs. See the
[example catalog](../artifacts/agentmeter_opt_final16/README.md) for files and replay commands.

## Public requirements and their adaptations

The following links connect representative edits to the instruction or input
artifact available to the agent. They explain the textual change, not the
unreleased source trajectory's exact reasoning.

| Example | Public basis | Adaptation |
|:--|:--|:--|
| [regex-log · Qwen × Codex](../artifacts/agentmeter_opt_final16/descriptions/qwen36_codex/regex-log/) | The Original reads `/app/regex.txt` directly into Python `re.findall`. | Makes the raw-pattern output contract explicit. |
| [dm-csv-011 · Qwen × Kimi](../artifacts/agentmeter_opt_final16/descriptions/qwen36_kimi_cli/dm-csv-011/) | The Original requires the supplied [CSV template](../benchmark_tasks/da_code/dm-csv-011/environment/sample_result.csv) and names the input/output directories. | Places the template's three column names and complete output path directly in the instruction. |
| [pddl-tpp-planning · DeepSeek × Kimi](../artifacts/agentmeter_opt_final16/descriptions/deepseek_v4_kimi_cli/pddl-tpp-planning/) | The Original gives action-per-line examples and the `plan_output` destination. | Separates input, output and completion requirements; additionally excludes output metadata and makes case matching explicit. |
| [bash-script-debugger · GLM × Qwen](../artifacts/agentmeter_opt_final16/descriptions/glm51_qwen_coder/bash-script-debugger/) | The Original lists five bug categories, the executable output path, and a public test command. | Reorganizes these requirements and adds an explicit completion sentence; retains the test command. |

For every released pair, [paired reward and cost](../artifacts/agentmeter_opt_final16/README.md#paired-results)
are joined by task ID and source configuration, without changing the evaluated text.

## Other changes in the collection

| Source | Main changes | Interpretation boundaries |
|:--|:--|:--|
| Qwen × Codex | Citation cleaning, economic input layout, raw-regex output, and report sheet structure | Regex uses the original public read/apply example, without lookaround recipes. Economic file-layout claims require checking the workbooks. The report clarifies merging and unique-region counts. |
| Qwen × Kimi | Scheduler lifecycle, cache expiry semantics, report formatting, and CSV schema | Scheduler/cache variants strengthen underspecified API behavior. Markdown adds stricter currency formatting for table cells; distinguish this from pure reorganization. |
| DeepSeek × Kimi | Planning output syntax, report completion, and ranking-file paths | Planning variants tighten formatting. The Markdown completion sentence can affect stopping behavior, but does not prohibit testing. |
| GLM × Qwen | Bug-fix submission, numeric spreadsheet output, Markdown template, and author template fields | Bash retains the original public test command. XLSX adds preservation constraints. Markdown specifies exactly three sections. |

The collection includes both requirement reorganization and additional
constraints; it is not uniformly a paraphrase-only intervention. No selected
variant explicitly prohibits testing or verification. The paired results
measure each full rewrite, not the causal effect of an individual sentence.

Each directory includes the original and evaluated rewritten instruction.
For the remaining CSV examples, public evidence includes:
[author schema](../benchmark_tasks/da_code/dm-csv-009/environment/sample_result.csv),
[ranking guidance](../benchmark_tasks/da_code/dm-csv-009/environment/guidance.txt),
and [bike schema](../benchmark_tasks/da_code/dm-csv-011/environment/sample_result.csv).

These task IDs contain historical names: for example, sales-pivot-analysis
actually asks for a demographic workbook. Examples follow the task content,
not an inferred interpretation of the ID.
