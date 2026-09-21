# SkillsBench Task Layout

This integration contains the minimal code AgentMeter needs to recognize and run SkillsBench/Harbor-style tasks.

The release bundles 16 tasks under `benchmark_tasks/`. For a larger task
selection, keep a compatible task checkout outside AgentMeter and point the
suite launcher to it:

```bash
export AGENTMETER_TASK_ROOT=/path/to/external/skillsbench/tasks
```

The upstream URL and paper-time commit are recorded in
`integrations/execution-lock.json`; AgentMeter does not download that task tree.
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
