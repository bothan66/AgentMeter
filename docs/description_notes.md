# Reading the four-source task groups

The showcase contains four tasks, each with all four historical source
rewrites and paired outcomes. They illustrate public artifact interpretation,
output contracts and completion guidance across ranking, bibliography,
validation and time-series analysis.
See the [example catalog](../artifacts/agentmeter_opt_final16/README.md)
for every version, result and replay command.

Tasks are selected by inspecting all four rewrites against the public
instruction and supplied artifacts, rather than by the size of a reward or
cost improvement. The selection favors inspectable file/schema clarifications
and existing task procedures over new solver choices or conflicting output
conventions. It is an illustrative subset, not a new evaluation set.
Historical rewrite wording is preserved; newly included text files receive
a final newline. No evaluated instruction is rewritten for presentation.

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

## csv-data-validator

The [Original](../benchmark_tasks/terminal_bench/csv-data-validator/instruction.md)
specifies five validation rules: integer/unique employee IDs, an email pattern,
exclusive salary bounds, the date format/cutoff and valid manager references.
It requires writing and running `/app/validate.py`, then producing a JSON
report with one entry per error and 1-based data-row indices. The public
[environment generator](../benchmark_tasks/terminal_bench/csv-data-validator/environment/generate_data.py)
creates the input CSV.

| Source | Adaptation | Execution guidance |
|:--|:--|:--|
| DeepSeek × Kimi | Separates validation rules, script requirements and report schema. | Stop after execution/report generation; do not read back or manually verify the report. |
| GLM × Qwen | Retains the rules and requires programmatic CSV processing. | Do not inspect the CSV directly or print/summarize input/output contents. |
| Qwen × Codex | Organizes write/run steps and explains error-object fields. | Stop after successful execution and report creation without reading/printing the report. |
| Qwen × Kimi | Organizes the same rules and specifies original invalid values as strings. | Stop after report creation without reading or verifying the output. |

All four retain the five validation rules and require executing the script.
The numeric JSON examples originate in Original; they are not newly supplied
answers. Direct-inspection/readback restrictions are added workflow constraints,
not requirements already present in Original. The paired outcomes therefore
measure schema clarification and execution policy together.

## econ-detrending-correlation

The [Original](../benchmark_tasks/skillsbench/econ-detrending-correlation/instruction.md)
already specifies the full calculation: use 1973–2024, average the available
2024 quarters, deflate nominal PCE/PFI by CPI, take natural logarithms, apply
the HP filter with lambda 100, and correlate the cyclical components.
The deliverable is one number, rounded to five decimal places, in
`/root/answer.txt`. The
[input spreadsheets](../benchmark_tasks/skillsbench/econ-detrending-correlation/environment/)
are included.

| Source | Adaptation | Completion guidance |
|:--|:--|:--|
| DeepSeek × Kimi | Repeats the existing year range next to the annual-data extraction requirement. | Stop after writing the answer; no further verification or file reads. |
| GLM × Qwen | Separates extraction, deflation, filtering, correlation and the single-number output into sections. | No further verification, testing or command loops after writing. |
| Qwen × Codex | Adds descriptions of spreadsheet headers and year/quarter indexing; foregrounds the existing 2024 averaging rule. | Deliver the specified single-number output. |
| Qwen × Kimi | Separates annual 1973–2023 rows from the available 2024 quarters and restates the existing calculation order. | Stop after writing; do not read the result back. |

The analysis procedure, parameter and precision are already in Original;
these are not new algorithm choices. The Codex variant's file-structure
descriptions are source-specific parsing guidance, while the other variants
also illustrate completion guidance. The numerical output example comes
from Original and is not a newly supplied answer. Historical formatting,
including the Kimi variant's trailing backtick, is retained.

## Interpreting the results

Every selected task includes all four source-matched outcomes, with no source
omitted for its reward or cost. The showcase includes full passes, partial
rewards, an unchanged zero reward and a cost increase. Lower cost at zero
reward does not establish successful completion.

Completion directives are part of the intervention: these variants are not
all pure paraphrases. Public grounding supports inspection but does not
prove semantic equivalence, and a gate pass is not a substitute for review.
The reported outcomes measure each complete historical rewrite, not the
causal effect of an individual sentence. The full archived study, not this
showcase selection, supplies the paper's aggregate results.
