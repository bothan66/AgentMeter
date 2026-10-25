# Four tasks, four description sources

Each task includes its Original instruction, all four historical source
rewrites, and every paired outcome. The selection illustrates public artifact
interpretation, output contracts and completion guidance across four domains.
It is made at the task level, not by choosing individual variants with
favorable reward or cost.

## Task coverage

| Task | Core requirement | Source coverage |
|:--|:--|:--|
| `dm-csv-009` | Three top-10 author rankings using public guidance and the CSV template | 4/4 |
| `citation-check` | Identify fake citations and return cleaned, sorted titles in JSON | 4/4 |
| `csv-data-validator` | Apply five validation rules and generate a JSON error report | 4/4 |
| `econ-detrending-correlation` | Apply the specified annual-series analysis and report one correlation | 4/4 |

These 16 variants are an illustrative subset of the 64-description study.
The complete archived result grid supplies the paper tables; changing the
showcase does not change that grid or its scores.

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
| [csv-data-validator / deepseek_v4_kimi_cli](descriptions/deepseek_v4_kimi_cli/csv-data-validator/) | 1.000 → 1.000 | 0.04947 → 0.04392 | -11.2% |
| [csv-data-validator / glm51_qwen_coder](descriptions/glm51_qwen_coder/csv-data-validator/) | 1.000 → 1.000 | 0.04915 → 0.03992 | -18.8% |
| [csv-data-validator / qwen36_codex](descriptions/qwen36_codex/csv-data-validator/) | 1.000 → 1.000 | 0.02024 → 0.01666 | -17.7% |
| [csv-data-validator / qwen36_kimi_cli](descriptions/qwen36_kimi_cli/csv-data-validator/) | 1.000 → 1.000 | 0.01212 → 0.01025 | -15.5% |
| [dm-csv-009 / deepseek_v4_kimi_cli](descriptions/deepseek_v4_kimi_cli/dm-csv-009/) | 0.333 → 0.333 | 0.04906 → 0.04318 | -12.0% |
| [dm-csv-009 / glm51_qwen_coder](descriptions/glm51_qwen_coder/dm-csv-009/) | 0.333 → 0.333 | 0.05093 → 0.03515 | -31.0% |
| [dm-csv-009 / qwen36_codex](descriptions/qwen36_codex/dm-csv-009/) | 0.000 → 0.333 | 0.00540 → 0.01142 | +111.4% |
| [dm-csv-009 / qwen36_kimi_cli](descriptions/qwen36_kimi_cli/dm-csv-009/) | 0.333 → 0.333 | 0.03301 → 0.01409 | -57.3% |
| [econ-detrending-correlation / deepseek_v4_kimi_cli](descriptions/deepseek_v4_kimi_cli/econ-detrending-correlation/) | 1.000 → 1.000 | 0.07794 → 0.06483 | -16.8% |
| [econ-detrending-correlation / glm51_qwen_coder](descriptions/glm51_qwen_coder/econ-detrending-correlation/) | 1.000 → 1.000 | 0.20054 → 0.14199 | -29.2% |
| [econ-detrending-correlation / qwen36_codex](descriptions/qwen36_codex/econ-detrending-correlation/) | 0.000 → 0.000 | 0.05035 → 0.04249 | -15.6% |
| [econ-detrending-correlation / qwen36_kimi_cli](descriptions/qwen36_kimi_cli/econ-detrending-correlation/) | 1.000 → 1.000 | 0.03469 → 0.03190 | -8.0% |

Recompute this table with `agentmeter tables --examples`.
All four outcomes per task are included, including the cost increase and
unchanged zero reward. These are historical observations, not repeated-run
estimates. A lower cost at zero reward is not successful completion; 0.333
is partial reward, not a full pass. Interpret reward and cost together.

## Reading the adaptations

- Author ranking: public file paths, ranking guidance and template fields.
- Citation checking: input/output organization and title normalization.
- CSV validation: existing rules, report fields and completion guidance.
- Economic analysis: annual/quarterly input parsing and an already specified
  deflation, filtering and correlation procedure.

Some variants also add post-output stopping directives or restrict inspection.
These are execution guidance, not requirements already present in every
Original. [Description notes](../../docs/description_notes.md) explain each
source variant and the selection criteria. The results measure the complete
rewrite, rather than attributing savings to an individual directive.
Task environments and verifiers remain unchanged.

## Provenance and reuse

- `baseline_instruction.md` is byte-identical to the bundled task's
  `instruction.md`; it is not AgentMeter-authored.
- `optimized_instruction.md` retains the historical AgentMeter-Opt wording.
  Its parent directories identify the source pair and task. New text copies
  use a final newline; their content is not edited for presentation.
- Instructions are drawn from the frozen
  `final16_experiment_bundle_20260712_v1/self_optimization/instruction_bundle`
  archive. All four sources are retained for each selected task.
- The source pair need not be the evaluation target.

| Local collection | Tasks in this catalog | Attribution |
|:--|:--|:--|
| `da_code` | dm-csv-009 | Local [DA-Code](https://github.com/yiyihum/da-code)-compatible collection |
| `terminal_bench` | csv-data-validator | Local Terminal-Bench-compatible collection |
| `skillsbench` | citation-check, econ-detrending-correlation | [SkillsBench](https://github.com/benchflow-ai/skillsbench) |

Original content and retained material in rewrites keep their applicable
upstream terms. [Benchmark sources and adaptations](../../benchmark_tasks/SOURCES.md)
record the available source revisions and distinguish local compatible
snapshots from upstream originals. License copies are included by task family;
see [third-party notices](../../THIRD_PARTY_NOTICES.md).

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

The [run-level scoring records](../scoring/README.md) contain all 64 Original,
64 Self and 192 Cross observations, filterable by task, source and target.
These cover the complete Final16 grid, not just this showcase.

Run `agentmeter tables --descriptive` for descriptive summaries
and `agentmeter tables` for AMS. Both read the same run-level USD inputs,
without changing historical accounting. Full optimized-grid replay requires
the remaining descriptions.
