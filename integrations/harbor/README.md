# Harbor Integration

This folder documents how AgentMeter uses Harbor / SkillsBench task layouts without vendoring the Harbor repository.

Expected real task layout:

```text
tasks/<task-id>/
  instruction.md
  task.toml
  environment/
  tests/
  solution/
```

Generate a manifest from Harbor-style tasks:

```bash
python scripts/build_manifest_from_harbor_tasks.py \
  --task-root "$AGENTMETER_TASK_ROOT" \
  --suite core30 \
  --out configs/manifests/core30.local.csv \
  --eval-command 'harbor run -p {task_dir} -a oracle'
```

For smoke tests that must prove the agent runs inside the copied task directory, use a marker checker instead of oracle:

```text
test -f {task_dir}/.agentmeter_agent_marker.json && test -f {run_dir}/agent_execution_marker.json
```

The harness copies each task into:

```text
runs/<exp>/tasks/<task_id>/<model>__<cli>/attempt_001/task/
```

The real source task directory is not modified.
