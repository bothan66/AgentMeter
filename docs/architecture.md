# Architecture

AgentMeter does not vendor SkillsBench, Harbor, or CLIProxyAPI.

## SkillsBench and Harbor

SkillsBench owns task definitions: `instruction.md`, `task.toml`, Docker
environment, skills, tests, verifier, solution, and public input data. Harbor
owns task execution. AgentMeter receives only task paths and run artifacts.

The adapters in `integrations/skillsbench` discover valid task layouts and
build manifests. The adapters in `integrations/harbor` launch or describe
Harbor evaluations without importing Harbor internals.

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
Only a sanitized config template and operational notes are included here; the
upstream proxy remains an external component with its own license.
