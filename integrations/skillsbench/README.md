# SkillsBench Task Layout

This integration contains the minimal code AgentMeter needs to recognize and run SkillsBench/Harbor-style tasks.

The release bundles 16 tasks under `benchmark_tasks/`. For a larger task
selection, point the suite launcher to a complete external checkout:

```bash
export AGENTMETER_TASK_ROOT=/path/to/skillsbench/tasks
```

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
