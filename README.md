<div align="center">

# AgentMeter

### Matching Matters: A Fair Quality–Efficiency Benchmark for Command-Line Agents

**Benchmark the pair. Understand the trajectory. Improve the description.**

**Han Chi<sup>1*</sup>, Jiaxin Qi<sup>1*</sup>, Yan Cui<sup>2</sup>, Baisheng Lai<sup>1</sup>, Jianqiang Huang<sup>1,2</sup>**

<sup>1</sup> Computer Network Information Center, Chinese Academy of Sciences  
<sup>2</sup> Hangzhou Institute for Advanced Study, Chinese Academy of Sciences  
<sup>*</sup> Equal contribution

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue)
![Tasks](https://img.shields.io/badge/benchmark-80%20tasks-7c3aed)

[Overview](#overview) · [Results](#results) · [Examples](#description-examples) · [Quick Start](#quick-start) · [Citation](#citation)

</div>

## Overview

AgentMeter evaluates **language model × CLI harness configurations** on task
quality and execution efficiency. The same model can behave differently under
different harnesses: tool use, context management, and recovery all matter.

**AgentMeter** provides the benchmark. **AMS** combines quality, cost budgets,
and expensive failures. **AgentMeter-Opt** uses source trajectories to diagnose
description-related friction and construct variants for cross-configuration
evaluation.

<p align="center">
  <img src="docs/assets/agentmeter_opt_pipeline.png" width="100%" alt="AgentMeter-Opt: public task requirements and source trajectories guide candidate construction, screening, and evaluation across configurations.">
  <br>
  <sub>AgentMeter-Opt · Diagnose execution friction, screen descriptions, and evaluate a shared set of variants.</sub>
</p>

| Benchmark | Configuration grid | Description study |
|:--:|:--:|:--:|
| **80 tasks** in Full80 | **7 models × 4 CLIs** on Core30 | **16 tasks × 4 source pairs** |
| [Frozen task selection](configs/task_lists/full80.txt) | [30-task core subset](configs/task_lists/core30.public.txt) | [16 selected rewrite examples](artifacts/agentmeter_opt_final16/README.md) |

The method constructs source-conditioned descriptions while retaining the
task environments and verifiers. See the [example catalog](artifacts/agentmeter_opt_final16/README.md)
for instruction pairs and [technical notes](docs/description_notes.md) for their interpretation.

## Results

**Different objectives select different LM–CLI pairs.** On Core30,
Qwen3.6-Plus × Kimi Code CLI achieves the highest AMS, while
Qwen3.6-Plus × Codex CLI has the lowest tokens and USD per pass.

| Core30 objective | Configuration | Result |
|:--|:--|--:|
| Highest AMS ↑ | Qwen3.6-Plus × Kimi Code CLI | **0.525** |
| Most passes ↑ | GLM-5.1 × Qwen Code / Gemini 3.5 Flash × Codex CLI | **18/30 each** |
| Lowest tokens per pass ↓ | Qwen3.6-Plus × Codex CLI | **0.48M** |
| Lowest USD per pass ↓ | Qwen3.6-Plus × Codex CLI | **$0.074** |

<details>
<summary>View selected Core30 configurations and rank agreement</summary>

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

</details>

**Description choice also changes the comparison.** Source-balanced Pooled
evaluation raises macro AMS from **0.333 to 0.458** in the manuscript;
Cross-only reaches **0.434**.

| Target pair | Original AMS | Pooled AMS | Cross-only AMS | Δ Pooled |
|:--|--:|--:|--:|--:|
| Qwen × Kimi | 0.353 | **0.470** | 0.457 | +0.117 |
| Qwen × Codex | 0.250 | **0.457** | 0.411 | +0.207 |
| DeepSeek × Kimi | 0.341 | **0.457** | 0.438 | +0.116 |
| GLM × Qwen | 0.389 | **0.446** | 0.429 | +0.057 |
| **Macro** | **0.333** | **0.458** | **0.434** | **+0.125** |

<details>
<summary>View archived Self rewards and costs in USD</summary>

| Self target (16 tasks each) | Original reward | Optimized reward | Original cost (USD) | Optimized cost (USD) |
|:--|--:|--:|--:|--:|
| DeepSeek × Kimi | 0.5521 | 0.7083 | 3.2165 | 1.5588 |
| GLM × Qwen | 0.5208 | 0.6458 | 3.3704 | 2.1855 |
| Qwen × Codex | 0.2761 | 0.6745 | 0.6389 | 0.5704 |
| Qwen × Kimi | 0.4323 | 0.5586 | 0.8206 | 0.6836 |

Source: [archived Self summary](artifacts/agentmeter_opt_final16/results/self_summary.csv).
Reward is the mean verifier reward; cost is the total over all 16 tasks,
including failures. Cross results are printed separately by the same script.

Costs use the manuscript's fixed rate, **1 CNY = 0.1471 USD**; original CSVs
retain CNY. Cached input is already included in input tokens.

</details>

<details>
<summary>Evaluation conditions and reproduction boundaries</summary>

The main matrix contains 64 Original, 64 Self and 192 Cross executions.
Generic adds 64 public-only control executions. Pooled aggregates source
outcomes; Adapted-1 samples 10,000 offline source assignments.

The Core30 and AMS tables above report manuscript numbers. The released
descriptive tables can be regenerated from archived CSVs. Exact historical
AMS reconstruction still needs effort assignments, full-precision calibration
and missing run-level records. The repository implements the manuscript
formula with its published rounded calibration.

[Scoring protocol](docs/paper_alignment.md) ·
[Release and verification scope](docs/reproduction_status.md)

</details>

## Description examples

A compact example from **regex-log · Qwen3.6-Plus × Codex CLI**:

| Original excerpt | Rewritten excerpt |
|:--|:--|
| Save your regex in `/app/regex.txt`. | Save your regex in `/app/regex.txt`. The file must contain only the raw regex string, with no extra text, markdown, or explanations. |

The rewrite makes the output-file content explicit, consistent with the
original public Python example that reads and applies the file as a pattern.
This illustrates a textual change; it does not establish a causal cost saving.

[Compare the complete pair](artifacts/agentmeter_opt_final16/descriptions/qwen36_codex/regex-log/)
· [Browse all 16 selected examples](artifacts/agentmeter_opt_final16/README.md)

Examples cover **13 tasks and all four source configurations**. They retain
the wording used in the experiments; the complete 64-description set is not
included in this release.

## Quick start

Requires **Python 3.11+**. Live evaluation additionally needs Docker access,
a provider API key, and network access for task images and CLI dependencies.
Install the [pinned Harbor runtime and patches](docs/external_dependencies.md#harbor)
before running tasks. API calls incur provider charges.

**1. Install the repository**

```bash
git clone https://github.com/bothan66/AgentMeter.git
cd AgentMeter
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[opt]'
```

**2. Inspect the released results**

```bash
python scripts/reproduce_artifact_table.py
```

This command needs no API or Docker and displays archived descriptive results
in USD. For manuscript scoring with your own task-level records:

```bash
python scripts/compute_paper_ams.py --runs condition.csv
```

Required columns: `task_id,stratum,reward,cost_usd`.
[Input conventions and calibration](docs/paper_alignment.md)

**3. Run a released example**

The example below evaluates **regex-log with Qwen3.6-Plus × Codex CLI**, a
source–target pair used in the paper's description study. It compares the
original instruction with the released rewrite from that same pair (Self).

Install Docker and the [pinned, patched Harbor](docs/external_dependencies.md),
then configure the target using the section below.

<details>
<summary>Configure provider credentials and the target model–CLI pair</summary>

```bash
cp .env.example .env
# Export the values below; launchers do not automatically load .env.

export AGENTMETER_HARBOR_BIN=harbor
export AGENTMETER_MODEL='Qwen3.6+'
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
`Qwen3.6+` is the model alias used in the example; replace it with your
provider's identifier for Qwen3.6-Plus. Codex 0.153.0 pins the release runtime;
it does not specify the CLI version of historical paper runs.

</details>

After exporting the configuration, check the endpoint and run both conditions:

```bash
python scripts/probe_responses.py
bash scripts/run_final16_condition.sh qwen36_codex original regex-log
bash scripts/run_final16_condition.sh qwen36_codex optimized regex-log
```

The provider or proxy base URL must also be reachable
from the task container; `127.0.0.1` inside a container refers to that container.

`qwen36_codex` selects the **description source**; `AGENTMETER_MODEL` and
`AGENTMETER_AGENT` select the **evaluation target**. Each invocation creates
a separate default output directory. If setting `AGENTMETER_JOBS_DIR`
explicitly, use a fresh directory per run.

**Outputs:** each run is saved under `jobs/` (or `AGENTMETER_JOBS_DIR`).
Within its task trial directory:

| File | Contents |
|:--|:--|
| `result.json` | Verifier reward, token usage, timing and exception status |
| `agent/trajectory.json` | Structured agent trajectory |
| `agent/codex.txt` | Raw Codex execution log |
| `verifier/test-stdout.txt` | Individual test outcomes |

See the [complete original and rewritten instructions](artifacts/agentmeter_opt_final16/descriptions/qwen36_codex/regex-log/)
and [reproduction guide](docs/reproduction_status.md) for the released artifacts
and runtime details.

<details>
<summary>Run Core30 or Full80</summary>

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

</details>

<details>
<summary>Generate a new trajectory-guided description</summary>

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

</details>

## Repository guide

| Resource | Entry |
|:--|:--|
| Benchmark selections | [Full80](configs/task_lists/full80.txt) · [Core30](configs/task_lists/core30.public.txt) |
| 16 executable task bundles | [benchmark_tasks/](benchmark_tasks/) |
| Selected descriptions and archived results | [artifacts/agentmeter_opt_final16/](artifacts/agentmeter_opt_final16/) |
| Description optimizer | [agentmeter_opt/](agentmeter_opt/) |
| Manuscript scoring | [paper.py](src/agentmeter/metrics/paper.py) · [protocol](docs/paper_alignment.md) |
| Execution dependencies | [Harbor and provider setup](docs/external_dependencies.md) |

Credentials, runtime caches, and raw trajectories are excluded from version
control. Fresh runs write to ignored output directories.

## Citation

<details>
<summary>BibTeX</summary>

```bibtex
@article{chi2026matching,
  title   = {Matching Matters: A Fair Quality--Efficiency Benchmark for Command-Line Agents},
  author  = {Chi, Han and Qi, Jiaxin and Cui, Yan and Lai, Baisheng and Huang, Jianqiang},
  year    = {2026}
}
```

</details>

## License

AgentMeter code: [MIT](LICENSE). Harbor compatibility patch:
[Apache-2.0](integrations/harbor/LICENSE). Benchmark tasks and data retain
their upstream terms; see [third-party notices](THIRD_PARTY_NOTICES.md).
