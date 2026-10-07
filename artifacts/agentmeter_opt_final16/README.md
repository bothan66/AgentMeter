# Description adaptations and paired results

Twelve evaluated description pairs cover 9 distinct tasks and all four source
configurations. Selected for traceable links to public requirements and input
artifacts, they illustrate trajectory-guided clarification of paths, schemas,
deliverables, and interface behavior. Selection is not based on the size or
direction of cost changes. All released instructions retain their historical wording; the full
64-description set is not included.

## Paired results

Each link opens the Original and evaluated rewrite. Self uses the same
model–harness pair as the description source. Costs use the archived USD
records, the same inputs as the main-table AMS calculation.

| Source pair / task | Reward: Original → Self | USD: Original → Self | Cost change |
|:--|--:|--:|--:|
| [deepseek_v4_kimi_cli / dm-csv-009](descriptions/deepseek_v4_kimi_cli/dm-csv-009/) | 0.333 → 0.333 | 0.04906 → 0.04318 | -12.0% |
| [deepseek_v4_kimi_cli / lru-cache-with-ttl](descriptions/deepseek_v4_kimi_cli/lru-cache-with-ttl/) | 0.000 → 1.000 | 0.06181 → 0.09909 | +60.3% |
| [deepseek_v4_kimi_cli / pddl-tpp-planning](descriptions/deepseek_v4_kimi_cli/pddl-tpp-planning/) | 0.000 → 0.000 | 0.10940 → 0.09830 | -10.2% |
| [deepseek_v4_kimi_cli / virtualhome-agent-planning](descriptions/deepseek_v4_kimi_cli/virtualhome-agent-planning/) | 0.000 → 0.000 | 0.18972 → 0.16127 | -15.0% |
| [glm51_qwen_coder / bash-script-debugger](descriptions/glm51_qwen_coder/bash-script-debugger/) | 1.000 → 1.000 | 0.07054 → 0.05525 | -21.7% |
| [glm51_qwen_coder / dm-csv-009](descriptions/glm51_qwen_coder/dm-csv-009/) | 0.333 → 0.333 | 0.05093 → 0.03515 | -31.0% |
| [glm51_qwen_coder / sales-pivot-analysis](descriptions/glm51_qwen_coder/sales-pivot-analysis/) | 0.000 → 1.000 | 0.13910 → 0.13539 | -2.7% |
| [qwen36_codex / citation-check](descriptions/qwen36_codex/citation-check/) | 0.000 → 1.000 | 0.11176 → 0.04519 | -59.6% |
| [qwen36_codex / regex-log](descriptions/qwen36_codex/regex-log/) | 1.000 → 1.000 | 0.02238 → 0.01726 | -22.9% |
| [qwen36_codex / sales-pivot-analysis](descriptions/qwen36_codex/sales-pivot-analysis/) | 0.000 → 1.000 | 0.04163 → 0.05957 | +43.1% |
| [qwen36_kimi_cli / bash-script-debugger](descriptions/qwen36_kimi_cli/bash-script-debugger/) | 1.000 → 1.000 | 0.01225 → 0.00863 | -29.6% |
| [qwen36_kimi_cli / dm-csv-011](descriptions/qwen36_kimi_cli/dm-csv-011/) | 0.000 → 0.000 | 0.07135 → 0.06537 | -8.4% |

Recompute this table with `agentmeter tables --examples`.
These are selected historical observations, not repeated-run estimates.
Cost reductions at zero reward are not successful task completion; interpret
reward and cost together. Complete-study comparisons use the full result grid.

## What the examples cover

| Source | Example focus |
|:--|:--|
| Qwen × Codex | Citation normalization, regex output contracts, demographic report organization |
| Qwen × Kimi | CSV template schema and completion after the public Bash test |
| DeepSeek × Kimi | Planning output syntax, public file references, and cache update behavior |
| GLM × Qwen | Bug-fix deliverables, author-table schema, and demographic input structure |

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
| `skillsbench` | citation-check, sales-pivot-analysis, virtualhome-agent-planning, pddl-tpp-planning | [SkillsBench](https://github.com/benchflow-ai/skillsbench) |
| `terminal_bench` | regex-log, bash-script-debugger, lru-cache-with-ttl | Local Terminal-Bench-compatible collection; compatibility is not a claim of an official upstream snapshot |
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
agentmeter compare qwen36_codex original regex-log
agentmeter compare qwen36_codex optimized regex-log
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

Run `agentmeter tables --descriptive` for descriptive summaries
and `agentmeter tables` for AMS. Both read the
same run-level USD inputs, without changing historical accounting.
The CNY files in `results/` remain unchanged as legacy source tables; their
`AgentMeterScore` field is not manuscript AMS. Full optimized-grid replay
requires the unreleased descriptions.
