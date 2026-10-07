# Reading the four-source task groups

The release includes four tasks, each with all four historical rewrites and
paired outcomes. See the
[example catalog](../artifacts/agentmeter_opt_final16/README.md) for the exact
instructions, archived reward/cost records and replay commands.
Task requirements and execution directives are distinguished below.
The evaluated files are preserved byte-for-byte, not edited for presentation.

## dm-csv-009

The Original requests three top-10 author rankings. Public
[guidance](../benchmark_tasks/da_code/dm-csv-009/environment/guidance.txt)
defines aggregation, ranking metrics and a ratings threshold; the
[CSV template](../benchmark_tasks/da_code/dm-csv-009/environment/sample_result.csv)
defines the column names and row IDs 0–9.

| Source | Adaptation |
|:--|:--|
| DeepSeek × Kimi | Uses complete guidance, template and output paths. |
| GLM × Qwen | Names the guidance criteria, bundled book file and template columns/IDs. |
| Qwen × Codex | Emphasizes guidance metrics/thresholds and lists template columns and rank IDs. |
| Qwen × Kimi | Explicitly requests reading the guidance and following the template. |

All four retain the rankings and the requested `author.csv` deliverable.

## citation-check

The [Original](../benchmark_tasks/skillsbench/citation-check/instruction.md)
requires checking `test.bib`, identifying fake citations, cleaning their
titles and writing an alphabetically sorted `fake_citations` array to
`/root/answer.json`. The
[input bibliography](../benchmark_tasks/skillsbench/citation-check/environment/test.bib)
is included; the rewrites do not supply labels identifying the fake entries.

| Source | Adaptation | Completion guidance |
|:--|:--|:--|
| DeepSeek × Kimi | Separates input, task and JSON requirements. | Stop after writing the required output, without further verification or tool calls. |
| GLM × Qwen | Organizes schema, cleaned titles and alphabetical ordering. | Stop after writing the required payload, without further searches or processing. |
| Qwen × Codex | Gives generic examples of removing braces and resolving LaTeX escapes. | Completion requires valid JSON containing all fake citations' cleaned, sorted titles. |
| Qwen × Kimi | Organizes input, output and title requirements. | Terminate after saving, without further summaries or conversational text. |

The fake-citation identification target and output content remain the same.
The post-write directives are added execution guidance, not statements copied
from the Original; their effect is part of the full rewrite intervention.

## markdown-table-generator

The [Original](../benchmark_tasks/terminal_bench/markdown-table-generator/instruction.md)
requires a grand sales total, every CSV row sorted by total descending, and
the top region/product by aggregate sales. It supplies three section headings,
seven table columns and currency examples for the summary/top performers.
The public environment
[generates the sales CSV](../benchmark_tasks/terminal_bench/markdown-table-generator/environment/generate_data.py).

| Source | Adaptation |
|:--|:--|
| DeepSeek × Kimi | Moves directory creation next to the output path and adds a completion sentence. |
| GLM × Qwen | Presents a three-section layout, currency formatting for summary/top performers, and no text outside the sections. |
| Qwen × Codex | Makes section formats explicit and asks for table numbers in their original CSV representation. |
| Qwen × Kimi | Uses the three-section layout and formats all table numbers as currency. |

The aggregate calculations, rows, sorting and winners are retained.
Original does not prescribe the numeric display format of table cells.
The Codex and Kimi versions choose different presentations, and some versions
restrict extra sections; these are explicit format refinements, not identical
wording or identical output-format constraints. The illustrative total and
top-performer examples are carried over from Original, not newly supplied
task answers.

## xlsx-recover-data

The [Original](../benchmark_tasks/skillsbench/xlsx-recover-data/instruction.md)
asks to replace each `???` in
[`nasa_budget_incomplete.xlsx`](../benchmark_tasks/skillsbench/xlsx-recover-data/environment/nasa_budget_incomplete.xlsx)
with a computed numeric value using relationships between sheets, then save
`nasa_budget_recovered.xlsx`. The input workbook contains Budget by
Directorate, YoY Changes, Directorate Shares and Growth Analysis sheets.

| Source | Adaptation | Completion guidance |
|:--|:--|:--|
| DeepSeek × Kimi | Explains same-year directorate totals and year-over-year percentage changes; asks to preserve existing content and formatting. | Save the recovered workbook. |
| GLM × Qwen | Emphasizes numeric cell types and preserving other cells, sheets and structure. | Save the named output. |
| Qwen × Codex | Groups requirements, numeric replacements and workbook preservation; specifies the current working directory. | Finish after saving a valid workbook with no placeholders; no additional verification is required. |
| Qwen × Kimi | Names cross-sheet relationship types and asks to match surrounding numeric types/percentage scales. | Verify that no placeholders remain. |

The relationship types are inspectable in the input workbook; the rewrites
do not list recovered cell answers. All four retain numeric recovery and the
output filename. Their guidance differs on post-save verification, which
is an execution-policy difference rather than a different missing-value
recovery target.

## Interpreting the results

Every task includes all four source-matched outcomes, with no source omitted
for its reward or cost. The showcase contains full passes, partial rewards
and unchanged zero rewards, as well as a cost increase. Savings at zero
reward should not be interpreted as successful optimization.

Public grounding supports inspection of task preservation but is not by
itself a proof of semantic equivalence. These examples retain the task targets;
some add formatting or execution constraints. Paired outcomes measure each
full historical rewrite, not the causal effect of an individual sentence.
The full archived study supplies the paper's aggregate results.
