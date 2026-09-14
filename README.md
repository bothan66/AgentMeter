<div align="center">

# AgentMeter

### Matching Matters: A Fair Quality–Efficiency Benchmark for Command-Line Agents

Evaluate the deployable **language model × CLI harness** pair—not the model in isolation.

**Han Chi<sup>1*</sup>, Jiaxin Qi<sup>1*</sup>, Yan Cui<sup>2</sup>, Baisheng Lai<sup>1</sup>, Jianqiang Huang<sup>1,2</sup>**

<sup>1</sup> Computer Network Information Center, Chinese Academy of Sciences  
<sup>2</sup> Hangzhou Institute for Advanced Study, Chinese Academy of Sciences  
<sup>*</sup> Equal contribution

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue)
![Tasks](https://img.shields.io/badge/benchmark-80%20tasks-7c3aed)

[Method](#our-work) · [Results](#main-results) · [Reproduction](#reproduction) · [Artifacts](#released-artifacts)

</div>

## Our work

Command-line agent performance depends on both the language model and the CLI
harness that controls tool invocation, context management, and failure
recovery. Evaluating only the model therefore hides an important deployment
choice. This work makes the **LM–CLI pair** the unit of evaluation.

Our contributions are:

1. **AgentMeter**, a benchmark that evaluates complete LM–CLI configurations
   on quality and execution efficiency under identical tasks and verifiers.
2. **AgentMeter Score (AMS)**, which combines budget-sensitive task quality
   with a penalty for expensive zero-reward executions.
3. **AgentMeter-Opt**, a trajectory-feedback method that identifies
   description-related route friction and generates pair-conditioned,
   task-preserving task descriptions for Self and Cross evaluation.

| Benchmark component | Scale | Purpose |
|:--|--:|:--|
| [Full benchmark](configs/task_lists/full80.txt) | 80 tasks | Deployment-level LM–CLI evaluation |
| [Core subset](configs/task_lists/core30.public.txt) | 30 tasks × 28 pairs | Complete 7-model × 4-CLI comparison |
| AgentMeter-Opt | 16 tasks, 320 main + 64 Generic executions | Original/Self/Cross; Pooled and Adapted-1 are derived controls |

## Main results

These are manuscript results. Exact paper AMS and Core/Full table reproduction
still require the records and settings listed in [reproduction scope](docs/reproduction_status.md).

The central result is simple: **there is no universally best CLI**. The same
model changes substantially across harnesses, and pass rate, cost, and the
AgentMeter Score (AMS) select different winners.

### Core30 highlights

| Objective | Best LM–CLI pair | Result |
|:--|:--|--:|
| Highest AMS ↑ | Qwen3.6-Plus × Kimi CLI | **0.525** |
| Most passes ↑ | GLM-5.1 × Qwen Code | **18/30** |
| Most passes ↑ | Gemini 3.5 Flash × Codex CLI | **18/30** |
| Lowest tokens per pass ↓ | Qwen3.6-Plus × Codex CLI | **0.48M** |
| Lowest USD per pass ↓ | Qwen3.6-Plus × Codex CLI | **$0.074** |

Selected configurations from the complete 28-pair grid:

| Rank | Model | CLI | Pass | Tokens / pass ↓ | USD / pass ↓ | AMS ↑ |
|--:|:--|:--|--:|--:|--:|--:|
| 1 | Qwen3.6-Plus | Kimi | 16/30 | 1.71M | $0.198 | **0.525** |
| 2 | MiniMax-M2.5 | Claude | 13/30 | 1.94M | $0.133 | **0.447** |
| 3 | GPT-5.3-Codex | Qwen | 17/30 | 0.55M | $0.290 | **0.445** |
| 4 | Qwen3.6-Plus | Qwen | 14/30 | 1.89M | $0.204 | **0.440** |
| 5 | GLM-5.1 | Qwen | 18/30 | 1.56M | $0.633 | **0.437** |
| 8 | Qwen3.6-Plus | Codex | 12/30 | **0.48M** | **$0.074** | 0.393 |

Core and Full rankings remain strongly aligned on their shared configurations
(Spearman ρ = **0.835**, Kendall τb = **0.683**).

## AgentMeter-Opt

The main matrix contains 64 Original, 64 Self and 192 Cross executions.
Generic adds 64 public-only control executions. Pooled aggregates source
outcomes, and Adapted-1 samples 10,000 offline source assignments.
See the [paper protocol and release scope](docs/paper_alignment.md).

AgentMeter-Opt diagnoses route friction from an Original trajectory, proposes a
bounded rewrite of `instruction.md`, applies a task-preservation safety gate,
and freezes the selected description before target evaluation. Tests,
environments, verifiers, solutions, and input artifacts are unchanged.

<p align="center">
  <img src="docs/assets/agentmeter_opt_pipeline.png" width="820" alt="AgentMeter-Opt pipeline">
</p>

### Description-condition results

| Target pair | Original AMS | Pooled AMS | Cross-only AMS | Δ Pooled |
|:--|--:|--:|--:|--:|
| Qwen × Kimi | 0.353 | **0.470** | 0.457 | +0.117 |
| Qwen × Codex | 0.250 | **0.457** | 0.411 | +0.207 |
| DeepSeek × Kimi | 0.341 | **0.457** | 0.438 | +0.116 |
| GLM × Qwen | 0.389 | **0.446** | 0.429 | +0.057 |
| **Macro** | **0.333** | **0.458** | **0.434** | **+0.125** |

Cross-transfer effectiveness ranges from **37.5% to 75.0%**, demonstrating
that description transfer is directional rather than universal. The paper's
qualitative examples are available in
[`docs/assets/description_examples.png`](docs/assets/description_examples.png).
This example release contains **16 selected source-conditioned descriptions**
and archived Self/Cross result tables under
[`artifacts/agentmeter_opt_final16/`](artifacts/agentmeter_opt_final16/).

## Reproduction

Start by recomputing the bundled descriptive Self/Cross tables (no API needed):

```bash
python scripts/reproduce_artifact_table.py
```

Archived CSVs retain CNY for provenance; the table command displays **USD**
using the manuscript's frozen rate, **1 CNY = 0.1471 USD**. Cached input is
already included in input tokens. This descriptive command does not compute AMS.

| Self target (16 tasks each) | Original reward | Optimized reward | Original cost (USD) | Optimized cost (USD) |
|:--|--:|--:|--:|--:|
| DeepSeek × Kimi | 0.5521 | 0.7083 | 3.2165 | 1.5588 |
| GLM × Qwen | 0.5208 | 0.6458 | 3.3704 | 2.1855 |
| Qwen × Codex | 0.2761 | 0.6745 | 0.6389 | 0.5704 |
| Qwen × Kimi | 0.4323 | 0.5586 | 0.8206 | 0.6836 |

Source: [archived Self summary](artifacts/agentmeter_opt_final16/results/self_summary.csv).
Reward is the mean verifier reward; cost is the total over all 16 tasks,
including failures. Cross results are printed separately by the same script.

### 1. Install AgentMeter

```bash
git clone https://github.com/bothan66/AgentMeter.git
cd AgentMeter
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[opt]'
```

Install Docker and the pinned Harbor checkout following
[execution dependencies](docs/external_dependencies.md). The released patch
preserves the four locally modified adapters; an arbitrary Harbor installation
is not equivalent. Harbor installs the target CLI inside each task container.
CLIProxyAPI is optional.

### 2. Configure a model–CLI target

```bash
cp .env.example .env
# Export the values below; launchers do not automatically load .env.

export AGENTMETER_HARBOR_BIN=harbor
export AGENTMETER_MODEL=deepseek-v4-pro
export AGENTMETER_AGENT=codex
export OPENAI_API_KEY=your-provider-key
export OPENAI_BASE_URL=https://provider.example/v1
export CODEX_FORCE_API_KEY=1
export CODEX_WIRE_API=responses
export AGENTMETER_AGENT_VERSION=0.153.0
# Optional: use a new directory on your data disk for each invocation.
# export AGENTMETER_JOBS_DIR=/path/to/data/agentmeter/run-001
# export TMPDIR=/path/to/data/tmp
```

Sanitized OpenAI Responses, Chat Completions, Anthropic Messages, and
CLIProxyAPI templates are provided in `configs/` and `integrations/`.

### 3. Reproduce Core30 and Full80

The exact task selections are frozen in:

- [`configs/task_lists/core30.public.txt`](configs/task_lists/core30.public.txt)
- [`configs/task_lists/full80.txt`](configs/task_lists/full80.txt)

Point `AGENTMETER_TASK_ROOT` to an upstream SkillsBench-compatible task checkout
and execute one target pair over either frozen task list:

```bash
export AGENTMETER_TASK_ROOT=/path/to/skillsbench

bash scripts/run_harbor_suite.sh configs/task_lists/core30.public.txt
# or
bash scripts/run_harbor_suite.sh configs/task_lists/full80.txt
```

Repeat for each target configuration to generate new Harbor rewards and usage
records. Compute the manuscript-defined score using
`python scripts/compute_paper_ams.py --runs condition.csv`, with one row per
task: `task_id,stratum,reward,cost_usd`. See [scoring protocol](docs/paper_alignment.md)
for required effort labels, rounded calibration limits, and historical data gaps.

### 4. Run selected AgentMeter-Opt examples

The repository includes 16 task environments and 16 selected optimized
descriptions. Full 64-description replay is not included in this release.
See the [example catalog](artifacts/agentmeter_opt_final16/README.md).
Replay a released example on a target pair with:

```bash
# One released example; omit the task to run this source's released examples.
bash scripts/run_final16_condition.sh \
  qwen36_codex optimized regex-log
```

Here, `qwen36_codex` selects the **description source**; `AGENTMETER_MODEL` and
`AGENTMETER_AGENT` select the **evaluation target**. This supports both Self
and Cross conditions without storing duplicate task copies.

To regenerate a description from an Original trajectory rather than replaying
a released one:

```bash
python agentmeter_opt/optimize_instruction.py \
  --task-id TASK_ID \
  --task-root benchmark_tasks/skillsbench \
  --baseline-result /path/to/original/agent/trajectory.json \
  --combo MODEL__HARNESS \
  --model MODEL \
  --cli HARNESS \
  --adaptation-mode combo_adapted \
  --candidate-only \
  --offline-until-accepted \
  --max-metric-calls 5 \
  --reflection-model openai/REFLECTION_MODEL \
  --out-dir generated_reports/example
```

This command generates a candidate only. Evaluate it with the unchanged task
verifier before reward-first, cost-second selection, then freeze the selected
description before Self or Cross evaluation. Automated preservation gates are
heuristics, not proof of semantic equivalence.

The execution and scoring path is:

```text
task + LM/CLI config → Harbor/Docker → CLI agent → provider API
                    → trajectory + verifier → reward/tokens/cost → AMS
```

## Released artifacts

| Artifact | Location |
|:--|:--|
| Full80 task selection | `configs/task_lists/full80.txt` |
| Core30 task selection | `configs/task_lists/core30.public.txt` |
| Final16 executable tasks | `benchmark_tasks/` |
| 16 selected Original/optimized description pairs | `artifacts/agentmeter_opt_final16/descriptions/` |
| Self and Cross results | `artifacts/agentmeter_opt_final16/results/` |
| AgentMeter-Opt implementation | `agentmeter_opt/` |

Raw trajectories, credentials, private provider endpoints, and duplicated
target-side task copies are intentionally excluded. They are regenerated by
the commands above and written to ignored output directories.

## Citation

```bibtex
@article{chi2026matching,
  title   = {Matching Matters: A Fair Quality--Efficiency Benchmark for Command-Line Agents},
  author  = {Chi, Han and Qi, Jiaxin and Cui, Yan and Lai, Baisheng and Huang, Jianqiang},
  year    = {2026}
}
```

## License

AgentMeter code is released under the [MIT License](LICENSE). The Harbor patch
retains its [Apache-2.0 license](integrations/harbor/LICENSE). Bundled task and
data terms are described in [third-party notices](THIRD_PARTY_NOTICES.md).
