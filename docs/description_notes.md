# Reading the description adaptations

Technical notes for the 9 selected historical instruction pairs. See the
[example catalog](../artifacts/agentmeter_opt_final16/README.md) for files and replay commands.

## Public requirements and their adaptations

The following links connect representative edits to the instruction or input
artifact available to the agent. They explain the textual change, not the
unreleased source trajectory's exact reasoning.

| Example | Public basis | Adaptation |
|:--|:--|:--|
| [regex-log · Qwen × Codex](../artifacts/agentmeter_opt_final16/descriptions/qwen36_codex/regex-log/) | The Original reads `/app/regex.txt` directly into Python `re.findall`. | Makes the raw-pattern output contract explicit. |
| [citation-check · Qwen × Codex](../artifacts/agentmeter_opt_final16/descriptions/qwen36_codex/citation-check/) | The Original requires sorted titles of fake citations, cleaned of BibTeX formatting. | Groups the output requirements and gives examples of removing markup. |
| [sales-pivot-analysis · Qwen × Codex](../artifacts/agentmeter_opt_final16/descriptions/qwen36_codex/sales-pivot-analysis/) | The Original specifies five sheets, SA2-region counts, income quartiles and a Total formula; public `income.xlsx` has unique SA2 identifiers. | Organizes the two-source merge and report schema, including unique-region counts and a completion condition. |
| [dm-csv-011 · Qwen × Kimi](../artifacts/agentmeter_opt_final16/descriptions/qwen36_kimi_cli/dm-csv-011/) | The Original requires the supplied [CSV template](../benchmark_tasks/da_code/dm-csv-011/environment/sample_result.csv) and names the input/output directories. | Places the template's three column names and complete output path directly in the instruction. |
| [dm-csv-009 · DeepSeek × Kimi](../artifacts/agentmeter_opt_final16/descriptions/deepseek_v4_kimi_cli/dm-csv-009/) / [GLM × Qwen](../artifacts/agentmeter_opt_final16/descriptions/glm51_qwen_coder/dm-csv-009/) | The Original names the guidance and [author template](../benchmark_tasks/da_code/dm-csv-009/environment/sample_result.csv); the template provides the columns and IDs. | Makes public file references explicit; the GLM-source variant also spells out the template fields. |
| [pddl-tpp-planning · DeepSeek × Kimi](../artifacts/agentmeter_opt_final16/descriptions/deepseek_v4_kimi_cli/pddl-tpp-planning/) | The Original gives action-per-line examples and the `plan_output` destination. | Separates input, output and completion requirements; additionally excludes output metadata and makes case matching explicit. |
| [virtualhome-agent-planning · DeepSeek × Kimi](../artifacts/agentmeter_opt_final16/descriptions/deepseek_v4_kimi_cli/virtualhome-agent-planning/) | The Original specifies PDDL inputs, action-per-line examples and an output path for each entry. | Concentrates plan formatting, name matching and all-entry completion requirements. |
| [bash-script-debugger · GLM × Qwen](../artifacts/agentmeter_opt_final16/descriptions/glm51_qwen_coder/bash-script-debugger/) | The Original lists five bug categories, the executable output path, and a public test command. | Reorganizes these requirements and adds an explicit completion sentence; retains the test command. |

For every released pair, [paired reward and cost](../artifacts/agentmeter_opt_final16/README.md#paired-results)
are joined by task ID and source configuration, without changing the evaluated text.

## Interpreting the examples

The showcase is selected for inspectable public grounding, not measured reward
or cost gains. It includes unchanged zero rewards, partial rewards and full
passes; the sales-report rewrite improves reward while increasing cost. The
complete archived grid, rather than this illustrative subset, supplies the
paper's aggregate results.

These are historical description adaptations, not uniformly paraphrase-only
edits: explicit formatting and completion language can change execution
behavior. No selected variant prohibits testing or verification. Paired
results measure each full rewrite, not the causal effect of one sentence.
Public grounding supports inspection of the edits; it does not by itself
prove semantic equivalence. Each directory retains the evaluated text
unchanged, separately from these interpretation notes.

These task IDs contain historical names: for example, sales-pivot-analysis
actually asks for a demographic workbook. Examples follow the task content,
not an inferred interpretation of the ID.
