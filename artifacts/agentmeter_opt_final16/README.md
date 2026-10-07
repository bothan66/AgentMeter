# One task, four description sources

The release presents `dm-csv-009` as a complete task group: the Original
and all four historical source rewrites, with every paired outcome.
The task's public guidance and CSV template provide inspectable grounding
for each version. Publication is task-level, not a selection of individual
variants by reward or cost. The full study contains 64 descriptions; its
aggregate results remain separate from this illustrative group.

## Paired results

Each link opens the Original and evaluated rewrite. Self uses the same
model–harness pair as the description source. Costs use the archived USD
records, the same inputs as the main-table AMS calculation.

| Task / source pair | Reward: Original → Self | USD: Original → Self | Cost change |
|:--|--:|--:|--:|
| [dm-csv-009 / deepseek_v4_kimi_cli](descriptions/deepseek_v4_kimi_cli/dm-csv-009/) | 0.333 → 0.333 | 0.04906 → 0.04318 | -12.0% |
| [dm-csv-009 / glm51_qwen_coder](descriptions/glm51_qwen_coder/dm-csv-009/) | 0.333 → 0.333 | 0.05093 → 0.03515 | -31.0% |
| [dm-csv-009 / qwen36_codex](descriptions/qwen36_codex/dm-csv-009/) | 0.000 → 0.333 | 0.00540 → 0.01142 | +111.4% |
| [dm-csv-009 / qwen36_kimi_cli](descriptions/qwen36_kimi_cli/dm-csv-009/) | 0.333 → 0.333 | 0.03301 → 0.01409 | -57.3% |

Recompute this table with `agentmeter tables --examples`.
All four outcomes are included, including the cost increase. These are
historical observations, not repeated-run estimates. A reward of 0.333 is
partial completion, not a full pass. Interpret reward and cost together.

## Public requirements and adaptations

The Original requests top-10 author rankings using
[`guidance.txt`](../../benchmark_tasks/da_code/dm-csv-009/environment/guidance.txt)
and the
[`sample_result.csv`](../../benchmark_tasks/da_code/dm-csv-009/environment/sample_result.csv)
format. The bundled environment includes those files and the book data.

| Source | Adaptation grounded in the public task |
|:--|:--|
| DeepSeek × Kimi | Expands the guidance, template and output references to their full paths. |
| GLM × Qwen | Makes the guidance criteria explicit and spells out the template's columns and row IDs. |
| Qwen × Codex | Makes the guidance criteria, metrics and thresholds explicit; spells out the template's columns and rank IDs. |
| Qwen × Kimi | Separates reading the ranking guidance and following the CSV template into explicit instructions. |

See [description notes](../../docs/description_notes.md) for interpretation.
The evaluated text is retained unchanged; task data, environments and
verifiers are not rewritten.

## Provenance and reuse

- `baseline_instruction.md` is byte-identical to the bundled task's
  `instruction.md`; it is not AgentMeter-authored.
- `optimized_instruction.md` is the historical AgentMeter-Opt modification.
  Its parent directories identify the source model–harness pair and task ID.
  The source pair need not be the evaluation target.
- The task belongs to the local [DA-Code](https://github.com/yiyihum/da-code)-compatible
  collection. Compatibility is not a claim of an exact upstream snapshot.

Original content and retained material in rewrites remain subject to their
applicable upstream terms, not automatically the repository's MIT license.
See [third-party notices](../../THIRD_PARTY_NOTICES.md) for attribution and
task-specific terms.

## Run an example

From the repository root, after configuring Harbor and provider credentials:

```bash
agentmeter compare qwen36_codex original dm-csv-009
agentmeter compare qwen36_codex optimized dm-csv-009
```

Replace `qwen36_codex` with any of the four source IDs in the table to
select another rewrite. Environment variables select the target model and
harness; matching the source configuration gives Self. Docker and provider
access are required. Use different output directories for the two conditions
if setting `AGENTMETER_JOBS_DIR` explicitly.

## Historical results

`results/self_summary.csv` contains full-study Original/Self aggregates.
`results/cross_task_results.csv` contains 192 Cross outcomes, filterable by
task and source; `results/cross_summary.csv` contains pair aggregates.
These are not results on this example group alone. Per-example Self outcomes
are available in the [run-level scoring records](../scoring/README.md).

Run `agentmeter tables --descriptive` for descriptive summaries
and `agentmeter tables` for AMS. Both read the same run-level USD inputs,
without changing historical accounting. The CNY files in `results/` remain
unchanged as legacy source tables; their `AgentMeterScore` field is not
manuscript AMS. Full optimized-grid replay requires the remaining descriptions.
