# Harbor Integration

This folder preserves AgentMeter's Harbor adapters and patches. Prepare the
pinned runtime from the repository root with:

```bash
bash scripts/bootstrap_execution.sh
```

The script clones Harbor into the ignored `vendor/` directory, checks out the
locked revision, applies both patches exactly once, and installs it into the
active Python environment. It never reads provider credentials. The upstream
source is fetched rather than duplicated in this repository; pins are recorded
in `integrations/execution-lock.json`.

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

Run a released task with `scripts/run_final16_condition.sh`, or a task list
with `scripts/run_harbor_suite.sh`. The Final16 launcher retains evaluated
instructions under `jobs/<run>/task_snapshots/` and saves Harbor results and
trajectories beside them. See [execution setup](../../docs/external_dependencies.md)
for the pinned Harbor revision and compatibility patches.
