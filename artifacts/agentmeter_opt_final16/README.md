# Four tasks, four description sources

The release contains four complete task groups: each includes the Original
and all four historical source rewrites, with every paired outcome.
The examples span CSV rankings, bibliography checking, Markdown reporting
and spreadsheet recovery. Publication is task-level, not a selection of
individual variants by reward or cost. All evaluated wording is retained.

## Task coverage

| Task | Core requirement | Source coverage |
|:--|:--|:--|
| `dm-csv-009` | Three top-10 author rankings, following public guidance and the CSV template | 4/4 |
| `citation-check` | Identify fake citations and return cleaned, alphabetically sorted titles in JSON | 4/4 |
| `markdown-table-generator` | Report the sales total, all sorted rows and the top region/product | 4/4 |
| `xlsx-recover-data` | Replace missing workbook values using cross-sheet relationships | 4/4 |

These 16 variants are an illustrative subset of the 64-description study.
The full archived result grid, not this subset, supplies the paper tables.

## Paired results

Each link opens the Original and evaluated rewrite. Self uses the same
model–harness pair as the description source. Costs use the archived USD
records, the same inputs as the main-table AMS calculation.

| Task / source pair | Reward: Original → Self | USD: Original → Self | Cost change |
|:--|--:|--:|--:|
| [citation-check / deepseek_v4_kimi_cli](descriptions/deepseek_v4_kimi_cli/citation-check/) | 1.000 → 1.000 | 0.78372 → 0.17290 | -77.9% |
| [citation-check / glm51_qwen_coder](descriptions/glm51_qwen_coder/citation-check/) | 1.000 → 1.000 | 0.24062 → 0.16641 | -30.8% |
| [citation-check / qwen36_codex](descriptions/qwen36_codex/citation-check/) | 0.000 → 1.000 | 0.11176 → 0.04519 | -59.6% |
| [citation-check / qwen36_kimi_cli](descriptions/qwen36_kimi_cli/citation-check/) | 1.000 → 1.000 | 0.03529 → 0.01476 | -58.2% |
| [dm-csv-009 / deepseek_v4_kimi_cli](descriptions/deepseek_v4_kimi_cli/dm-csv-009/) | 0.333 → 0.333 | 0.04906 → 0.04318 | -12.0% |
| [dm-csv-009 / glm51_qwen_coder](descriptions/glm51_qwen_coder/dm-csv-009/) | 0.333 → 0.333 | 0.05093 → 0.03515 | -31.0% |
| [dm-csv-009 / qwen36_codex](descriptions/qwen36_codex/dm-csv-009/) | 0.000 → 0.333 | 0.00540 → 0.01142 | +111.4% |
| [dm-csv-009 / qwen36_kimi_cli](descriptions/qwen36_kimi_cli/dm-csv-009/) | 0.333 → 0.333 | 0.03301 → 0.01409 | -57.3% |
| [markdown-table-generator / deepseek_v4_kimi_cli](descriptions/deepseek_v4_kimi_cli/markdown-table-generator/) | 0.000 → 0.000 | 0.08426 → 0.04775 | -43.3% |
| [markdown-table-generator / glm51_qwen_coder](descriptions/glm51_qwen_coder/markdown-table-generator/) | 0.000 → 0.000 | 0.03931 → 0.02605 | -33.7% |
| [markdown-table-generator / qwen36_codex](descriptions/qwen36_codex/markdown-table-generator/) | 0.000 → 0.000 | 0.01016 → 0.00999 | -1.7% |
| [markdown-table-generator / qwen36_kimi_cli](descriptions/qwen36_kimi_cli/markdown-table-generator/) | 0.000 → 0.000 | 0.01254 → 0.00958 | -23.6% |
| [xlsx-recover-data / deepseek_v4_kimi_cli](descriptions/deepseek_v4_kimi_cli/xlsx-recover-data/) | 0.000 → 0.000 | 0.19523 → 0.08904 | -54.4% |
| [xlsx-recover-data / glm51_qwen_coder](descriptions/glm51_qwen_coder/xlsx-recover-data/) | 0.000 → 0.000 | 0.22398 → 0.19111 | -14.7% |
| [xlsx-recover-data / qwen36_codex](descriptions/qwen36_codex/xlsx-recover-data/) | 0.000 → 0.000 | 0.07929 → 0.03817 | -51.9% |
| [xlsx-recover-data / qwen36_kimi_cli](descriptions/qwen36_kimi_cli/xlsx-recover-data/) | 0.000 → 0.000 | 0.07284 → 0.05296 | -27.3% |

Recompute this table with `agentmeter tables --examples`.
All four outcomes per task are included, including cost increases and
unchanged zero rewards. These are historical observations, not repeated-run
estimates. A lower cost at zero reward is not successful completion; 0.333
is partial reward, not a full pass. Interpret reward and cost together.

## Reading the adaptations

The four groups preserve the stated task targets while illustrating
different description interventions:

- Author ranking: explicit public file paths, guidance and template fields.
- Citation checking: organized input/output requirements and title normalization.
- Markdown reporting: explicit section layout and source-specific numeric presentation.
- Spreadsheet recovery: numeric replacement, cross-sheet relationships and preservation of existing workbook content.

Some variants also introduce post-output completion directives. Those are
execution guidance, not requirements already present in every Original.
The examples are therefore not uniformly paraphrase-only edits.
[Description notes](../../docs/description_notes.md) distinguish these
directives from shared task requirements and document each source variant.
Task data, environments and verifiers are unchanged.

## Provenance and reuse

- `baseline_instruction.md` is byte-identical to the bundled task's
  `instruction.md`; it is not AgentMeter-authored.
- `optimized_instruction.md` is the historical AgentMeter-Opt modification.
  Its parent directories identify the source model–harness pair and task ID.
  The source pair need not be the evaluation target.

| Local collection | Tasks in this catalog | Attribution |
|:--|:--|:--|
| `da_code` | dm-csv-009 | Local [DA-Code](https://github.com/yiyihum/da-code)-compatible collection |
| `terminal_bench` | markdown-table-generator | Local Terminal-Bench-compatible collection |
| `skillsbench` | citation-check, xlsx-recover-data | [SkillsBench](https://github.com/benchflow-ai/skillsbench) |

Collection names are not claims of exact upstream snapshots. Original
content and retained material in rewrites remain subject to their applicable
upstream terms, not automatically the repository's MIT license.
See [third-party notices](../../THIRD_PARTY_NOTICES.md) for attribution and
task-specific terms, including the separately licensed bundled XLSX skill.

## Run an example

From the repository root, after configuring Harbor and provider credentials:

```bash
agentmeter compare qwen36_codex original dm-csv-009
agentmeter compare qwen36_codex optimized dm-csv-009
```

Replace the task ID with any of the four catalog tasks and the source ID
with any of the four source configurations. Omitting task IDs selects all
four released tasks for either condition. Environment variables select the
target model and harness; matching the source gives Self.
Docker and provider access are required. Use different output directories
for the two conditions if setting `AGENTMETER_JOBS_DIR` explicitly.

## Historical results

`results/self_summary.csv` contains full-study Original/Self aggregates.
`results/cross_task_results.csv` contains 192 Cross outcomes, filterable by
task and source; `results/cross_summary.csv` contains pair aggregates.
These are not results on this showcase alone. Per-example Self outcomes
are available in the [run-level scoring records](../scoring/README.md).

Run `agentmeter tables --descriptive` for descriptive summaries
and `agentmeter tables` for AMS. Both read the same run-level USD inputs,
without changing historical accounting. The CNY files in `results/` remain
unchanged as legacy source tables; their `AgentMeterScore` field is not
manuscript AMS. Full optimized-grid replay requires the remaining descriptions.
