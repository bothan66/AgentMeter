# Architecture

AgentMeter is an installable Python package with one entry point:
`agentmeter` (or `python -m agentmeter`). Research artifacts and execution
dependencies remain explicit inputs to that package.

| Package | Responsibility |
|:--|:--|
| `agentmeter.metrics` | Manuscript AMS from task reward, archived cost and shared calibration |
| `agentmeter.reporting` | Validate the released observation grid and reproduce paper tables |
| `agentmeter.optimization` | Extract trajectory evidence, construct descriptions, check preservation and summarize candidates |
| `agentmeter.runtime` | Prepare pinned Harbor and run matched instruction conditions or task lists |
| `agentmeter.providers` | Probe Responses endpoints and render private CLIProxyAPI routes |
| `agentmeter.tasks` | Discover task directories and build manifests for explicit custom verifiers |
| `agentmeter.harness` | Optional remote-runner transport, usage normalization and artifact recording |

## Description construction

The optimizer separates evidence extraction, feedback, optimization policy,
provider setup, execution and preservation checks into individual modules.
The public task instruction and source trajectory are inputs to candidate
construction. The original environment and verifier remain fixed. Candidate
selection uses source-pair reward first and cost second; the selected text
is then frozen for Self/Cross evaluation.

The released instruction pairs and result records are in `artifacts/`.
[`docs/optimization.md`](optimization.md) gives the generation command and
describes candidate outputs.

## Task execution

SkillsBench-style tasks contain `instruction.md`, `task.toml`, an environment
and a verifier. The 16 released task bundles are in `benchmark_tasks/`;
larger task checkouts are supplied through `AGENTMETER_TASK_ROOT`.

Harbor owns container execution and records verifier reward and trajectories.
AgentMeter's runtime prepares the pinned Harbor revision and compatibility
patches, checks task selection, preserves instruction snapshots and launches
the chosen model–harness pair. The patches and lock file live in
`integrations/harbor/` and `integrations/agentmeter_runtime.lock.json`.

## Provider routing

Model and harness are separate experiment variables. A harness can connect
directly to a compatible provider or use the bundled modified CLIProxyAPI
snapshot for Responses, Chat Completions and Messages conversion. Its Go
source, license and checksum manifest are kept under `integrations/cliproxyapi/`.
Python runtime setup and scoring do not require building this optional proxy.

## Installed code and research artifacts

The wheel includes the Python implementation. Commands that consume task
bundles, result tables or Harbor patches locate the research checkout from
the current directory or `AGENTMETER_REPO_ROOT`. Credentials come from the
environment; generated jobs, private configurations and caches stay outside
the tracked source. Tests cover both the package and the released artifacts.
