<div align="center">

# AgentMeter

### Matching Matters: A Fair Quality–Efficiency Benchmark for Command-Line Agents

**Evaluate the pair. Account for cost. Compare across descriptions.**

**Han Chi<sup>1*</sup>, Jiaxin Qi<sup>1*</sup>, Yan Cui<sup>2</sup>, Baisheng Lai<sup>1</sup>, Jianqiang Huang<sup>1,2</sup>**

<sup>1</sup> Computer Network Information Center, Chinese Academy of Sciences  
<sup>2</sup> Hangzhou Institute for Advanced Study, Chinese Academy of Sciences  
<sup>*</sup> Equal contribution

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue)
![Benchmark](https://img.shields.io/badge/study-80%20tasks-7c3aed)
![Configurations](https://img.shields.io/badge/Core30-28%20pairs-0f766e)

[Overview](#overview) · [Results](#results) · [Method](#method) · [Reproduce](#quick-start) · [Examples](#description-examples) · [Citation](#citation)

</div>

## Overview

**Which model–harness pair solves tasks well at a reasonable cost—and how much
does that comparison depend on the task description?**

AgentMeter evaluates language models together with their command-line
harnesses. Tool interfaces, context management, and recovery can change the
quality and cost of the same model. A single collected task description can
also favor some configurations over others.

Our study connects three questions:

| Research question | Our approach |
|:--|:--|
| Does the harness change a model's performance? | Compare **7 models × 4 CLIs** on Core30; examine consistency with Full80. |
| How should quality and execution cost be compared? | **AMS** combines graded quality, quality within cost budgets, and expensive zero-reward failures. |
| Does description choice change the comparison? | **AgentMeter-Opt** constructs trajectory-guided rewrites and evaluates targets on a shared, source-balanced description set. |

The benchmark study covers **80 tasks**; the description study covers
**16 tasks × 4 source pairs**. This release includes the frozen task lists,
16 executable task bundles, 16 selected rewrites, and archived Self/Cross
results. [Release contents and reproduction scope](docs/reproduction_status.md)

## Results

**1. The best pair depends on the evaluation objective.**

| Core30 pair | Full passes ↑ | Tokens / pass ↓ | USD / pass ↓ | AMS ↑ |
|:--|--:|--:|--:|--:|
| Qwen3.6-Plus × Kimi Code CLI | 16/30 | 1.71M | $0.198 | **0.525** |
| Qwen3.6-Plus × Codex CLI | 12/30 | **0.48M** | **$0.074** | 0.393 |
| Qwen3.6-Plus × Claude Code | 11/30 | 3.51M | $0.332 | 0.325 |
| GLM-5.1 × Qwen Code | **18/30** | 1.56M | $0.633 | 0.437 |
| Gemini 3.5 Flash × Codex CLI | **18/30** | 3.15M | $2.013 | 0.273 |

With Qwen3.6-Plus fixed, changing the CLI produces a **0.200 AMS gap**.
The highest pass count, lowest cost per pass, and highest AMS select different
pairs. Core30 and Full80 rankings agree strongly on shared configurations
(Spearman **ρ = 0.835**, Kendall **τb = 0.683**).

[All 28 configurations (CSV)](artifacts/core30_paper_results.csv) ·
[Scoring protocol](docs/paper_alignment.md)

Tokens/pass and USD/pass divide total valid-run usage, including failures, by
the number of fully passed tasks. These results are transcribed from the paper.

**2. Description choice affects measured performance.**

| Target pair | Original AMS | Pooled AMS | Cross-only AMS | Δ Pooled |
|:--|--:|--:|--:|--:|
| Qwen3.6-Plus × Kimi | 0.353 | **0.470** | 0.457 | +0.117 |
| Qwen3.6-Plus × Codex | 0.250 | **0.457** | 0.411 | +0.207 |
| DeepSeek-V4-Pro × Kimi | 0.341 | **0.457** | 0.438 | +0.116 |
| GLM-5.1 × Qwen | 0.389 | **0.446** | 0.429 | +0.057 |
| **Macro** | **0.333** | **0.458** | **0.434** | **+0.125** |

Original uses the collected description. Self uses a target's own rewrite;
Cross uses rewrites from other source pairs. Pooled weights all sources
equally, so every target is evaluated against the same description set.
It does not select each target's best source.

The table reports manuscript AMS. Recompute the released reward/cost
statistics with the command below; see the [scoring protocol](docs/paper_alignment.md)
for AMS inputs, calibration and historical result provenance.

## Method

**AMS: quality, budget efficiency, and expensive failures.**

AMS averages equally over fixed observed-effort strata:

$$
\mathrm{AMS}=\frac{1}{3}\sum_{s\in\{\mathrm{Easy,Medium,Hard}\}}
\left[0.6\,\mathrm{TQ}_s+0.4\,\mathrm{AUBQC}_s\right]
\left[1-\mathrm{EFR}_s\right].
$$

TQ is mean graded reward. AUBQC measures reward available within calibrated
cost budgets. EFR measures zero-reward runs exceeding a calibrated cost
threshold. Strata, calibration, and billing rules are shared across pairs.
[Implementation](src/agentmeter/metrics/paper.py) · [Protocol](docs/paper_alignment.md)

**AgentMeter-Opt: trajectory feedback → description construction → shared evaluation.**

<p align="center">
  <img src="docs/assets/agentmeter_opt_pipeline.png" width="960" alt="AgentMeter-Opt constructs candidate descriptions from public requirements and source trajectories, screens and selects them, then evaluates across model–harness pairs.">
</p>

The original instruction and source trajectory guide candidate construction.
Candidates are screened for task preservation, then selected on the source
pair by reward first and cost second. Selected descriptions are frozen before
cross-configuration evaluation. Task environments and verifiers remain fixed.

[Optimizer](agentmeter_opt/) · [Construction and selection details](docs/description_notes.md)

## Quick start

**Requirements:** Python 3.11+ for scoring; Python 3.12–3.13 for Harbor + Opt.
Live runs additionally require Docker access,
a provider API key, and network access for images and dependencies. API calls
incur provider charges.

**1. Install and reproduce the main result tables**

```bash
git clone https://github.com/bothan66/AgentMeter.git
cd AgentMeter
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/reproduce_paper_tables.py
python scripts/reproduce_artifact_table.py
```

The first command recomputes all 28 Core30 rows and Final16
Original/Self/Cross/Pooled AMS from **1,160 archived run records** and frozen
full-precision calibration. The second prints additional reward/cost and
transfer summaries. No API or Docker is needed for this step.
[Scoring data and accounting](artifacts/scoring/README.md)

**2. Run the paper's Qwen3.6-Plus × Codex example**

First install the [pinned Harbor runtime and two patches](docs/external_dependencies.md#harbor).
Then export credentials and run Original and Self on `regex-log`:

```bash
export AGENTMETER_HARBOR_BIN=harbor
export AGENTMETER_MODEL='Qwen3.6+'
export AGENTMETER_AGENT=codex
export AGENTMETER_AGENT_VERSION=0.153.0
export OPENAI_API_KEY=your-provider-key
export OPENAI_BASE_URL=https://provider.example/v1
export CODEX_FORCE_API_KEY=1
export CODEX_WIRE_API=responses

python scripts/probe_responses.py
bash scripts/run_final16_condition.sh qwen36_codex original regex-log
bash scripts/run_final16_condition.sh qwen36_codex optimized regex-log
```

Use your provider's identifier for Qwen3.6-Plus and a Responses endpoint
reachable from the task container. Codex 0.153.0 pins this release's runtime;
historical paper CLI versions are not implied. Provider/proxy configuration
and data-disk storage are covered in [execution setup](docs/external_dependencies.md).

`qwen36_codex` selects the description source; the exported model and
agent select the target. Keeping them matched gives Self. Each invocation
creates a separate directory under `jobs/`.
Omitting task IDs runs the same released source-specific subset in both
conditions, so Original and Self remain paired.

| Trial output | What to inspect |
|:--|:--|
| `result.json` | Reward, input/output/cache tokens, timings and exceptions |
| `agent/trajectory.json` | Structured execution trajectory |
| `agent/codex.txt` | Raw Codex log |
| `verifier/test-stdout.txt` | Individual test outcomes |

**3. Extend the experiment**

| Goal | Instructions |
|:--|:--|
| Run Core30 / Full80 with a complete task checkout | [Benchmark execution](docs/reproduction_status.md#run-core30-or-full80) |
| Construct a rewrite from an Original trajectory | [Trajectory-guided construction](docs/reproduction_status.md#generate-a-new-trajectory-guided-description) |
| Compute AMS from task-level reward and USD cost | [Scoring inputs and calibration](docs/paper_alignment.md) |

## Description examples

**regex-log · Qwen3.6-Plus × Codex CLI**

| Original excerpt | Rewritten excerpt |
|:--|:--|
| Save your regex in `/app/regex.txt`. | Save your regex in `/app/regex.txt`. The file must contain only the raw regex string, with no extra text, markdown, or explanations. |

The rewrite makes the output-file contract explicit, consistent with the
original public Python example that reads the file as a pattern.
This illustrates output-contract clarification. The paired evaluation
records track the resulting reward and execution cost.

| Archived condition | Reward | Cost (USD) | Billable-component tokens |
|:--|--:|--:|--:|
| Original | 1.0 | 0.02238 | 67,380 |
| Self rewrite | 1.0 | 0.01726 | 59,868 |

Historical paired observations, using archived USD costs. See
[all 16 example results](artifacts/agentmeter_opt_final16/README.md#paired-results)
and [the public basis for representative edits](docs/description_notes.md#public-requirements-and-their-adaptations).

[Compare the complete pair](artifacts/agentmeter_opt_final16/descriptions/qwen36_codex/regex-log/) ·
[Browse 16 selected examples](artifacts/agentmeter_opt_final16/README.md)

The examples span 13 tasks and all four source configurations. They are a
selected subset of the 64 descriptions constructed in the study.
Each pair retains the benchmark's Original instruction and the historical
AgentMeter-Opt rewrite, identified by task and source model–harness pair.
The rewrite is our description adaptation, not an upstream benchmark release;
the original task environment and verifier are shared across conditions.
See [example provenance and reuse](artifacts/agentmeter_opt_final16/README.md#provenance-and-reuse)
for attribution and applicable terms.

## Repository guide

| Resource | Location |
|:--|:--|
| Full80 and Core30 selections | [Task lists](configs/task_lists/) |
| 16 executable task bundles | [benchmark_tasks/](benchmark_tasks/) |
| Selected rewrites and Self/Cross results | [Released artifacts](artifacts/agentmeter_opt_final16/) |
| Complete Core30 paper table | [28-pair CSV](artifacts/core30_paper_results.csv) |
| Main-table scoring inputs | [1,160 run records and provenance](artifacts/scoring/) |
| Harbor patches and provider routing | [Execution dependencies](docs/external_dependencies.md) |
| Modified CLIProxyAPI source and route setup | [Proxy integration](integrations/cliproxyapi/) |

Runtime caches, credentials, and new trajectories are excluded from Git.

## Citation

```bibtex
@article{chi2026matching,
  title   = {Matching Matters: A Fair Quality--Efficiency Benchmark for Command-Line Agents},
  author  = {Chi, Han and Qi, Jiaxin and Cui, Yan and Lai, Baisheng and Huang, Jianqiang},
  year    = {2026}
}
```

## License

AgentMeter code: [MIT](LICENSE). Harbor compatibility patches:
[Apache-2.0](integrations/harbor/LICENSE). Benchmark tasks and data retain
their upstream terms; see [third-party notices](THIRD_PARTY_NOTICES.md).
