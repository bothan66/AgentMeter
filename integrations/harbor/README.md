# Harbor Integration

This folder preserves AgentMeter's Harbor compatibility patches. Prepare the
pinned runtime from the repository root with:

```bash
agentmeter setup
```

The Python runtime clones Harbor into the ignored `vendor/` directory, checks out the
locked revision, applies both patches exactly once, and installs it into the
active Python environment. It never reads provider credentials. The upstream
source is fetched rather than duplicated in this repository; pins are recorded
in `integrations/agentmeter_runtime.lock.json`.

Use `--prepare-only` to inspect the pinned source and applied patches before
installation, or `--vendor-dir /path/to/dependencies` to choose the checkout
location. Task discovery and launch logic live in
[`agentmeter.runtime`](../../src/agentmeter/runtime/).

Expected task layout:

```text
tasks/<task-id>/
  instruction.md
  task.toml
  environment/
  tests/
  solution/
```

Run a released instruction pair:

```bash
agentmeter compare qwen36_codex original regex-log --dry-run
agentmeter compare qwen36_codex original regex-log
agentmeter compare qwen36_codex optimized regex-log
```

Run a frozen list with `agentmeter suite configs/task_lists/core30.public.txt`
after configuring an external task checkout. The comparison command retains evaluated
instructions under `jobs/<run>/task_snapshots/` and saves Harbor results and
trajectories beside them. `agentmeter_cli_adapters.patch` implements the four
CLI execution adapters; `agentmeter_provider_routing.patch` carries custom
endpoint authentication and model-ID handling. See
[execution setup](../../docs/external_dependencies.md) for the pinned base.
