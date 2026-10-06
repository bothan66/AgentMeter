# SkillsBench Task Layout

AgentMeter recognizes SkillsBench/Harbor task layouts through
[`agentmeter.tasks`](../../src/agentmeter/tasks.py); its Python runtime sends
selected task paths to Harbor for execution.

The release bundles 16 tasks under `benchmark_tasks/`. For a larger task
selection, keep a compatible task checkout outside AgentMeter and point the
suite launcher to it:

```bash
export AGENTMETER_TASK_ROOT=/path/to/external/skillsbench/tasks
agentmeter suite configs/task_lists/core30.public.txt --dry-run
```

The upstream URL and paper-time commit are recorded in
`integrations/agentmeter_runtime.lock.json`; AgentMeter does not download that task tree.
All released Final16 examples use the bundled task directories.

Expected task layout:

```text
tasks/<task-id>/
  instruction.md
  task.toml
  environment/
  tests/
  solution/
```

The `task.toml` metadata is used for manifest generation:

- `metadata.difficulty`
- `metadata.category`
- `metadata.tags`
- `verifier.timeout_sec`

For a custom remote-runner integration, `agentmeter manifest --help` describes
manifest generation. Supply `--eval-command` explicitly with a checker that
evaluates the completed agent artifacts. Normal `agentmeter compare` and
`agentmeter suite` workflows use Harbor's verifier and need no custom manifest.
