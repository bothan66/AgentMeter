# Architecture

The release bundles selected benchmark tasks and a modified CLIProxyAPI source
snapshot. Harbor is installed from its pinned upstream revision plus patches.

## SkillsBench and Harbor

SkillsBench owns task definitions: `instruction.md`, `task.toml`, Docker
environment, skills, tests, verifier, solution, and public input data. Harbor
owns task execution. AgentMeter receives only task paths and run artifacts.

The adapters in `integrations/skillsbench` discover valid task layouts and
build manifests. The launchers in `scripts/` execute paired examples or
frozen task lists through Harbor. `integrations/harbor` contains compatibility
patches and task/evaluation helpers.

## AgentMeter and AgentMeter-Opt

AgentMeter normalizes trajectories from different harnesses into common route
features: turns, token usage, tool calls, repeated reads, repair loops, output
events, and reward. AgentMeter-Opt uses those observations as feedback for a language
model that proposes a revised public task description.

The safety gate rejects checker leakage, hidden-test references, solver hints,
new implementation constraints, changed file contracts, and unsupported task
semantics. Validation copies the task and replaces only `instruction.md`.

## Model and harness routing

The experiment matrix treats model and harness as separate variables. Runner
configuration maps a `(model, harness)` pair to one of three wire formats:
OpenAI Responses, OpenAI Chat Completions, or Anthropic Messages.

For production, CLIProxyAPI can expose these formats at a single local address.
The modified proxy source, configuration renderer and build instructions are
included in `integrations/cliproxyapi/`, under its upstream MIT license.

## Code and tests

`src/agentmeter/metrics/paper.py` implements manuscript AMS.
`agentmeter_opt/` implements trajectory-guided candidate construction and
preservation checks; its shared execution helpers live in
`scripts/harness_lib.py`. Archived results and task descriptions live in
`artifacts/`. Simulation data is isolated in `tests/fixtures/`; production
runner discovery reads local configuration files only.
