# Harbor / SkillsBench Task Layout

The real benchmark tasks in `~/workplace/agent/skillsbench/tasks` use the Harbor / SkillsBench layout.

Typical task directory:

```text
tasks/<task-id>/
  instruction.md
  task.toml
  environment/
    Dockerfile
    ...
  tests/
    test.sh
    test_outputs.py
    ...
  solution/
    solve.sh
    ...
```

Observed examples:

```text
tasks/organize-messy-files/
  instruction.md
  task.toml
  environment/Dockerfile
  tests/test.sh
  tests/test_outputs.py
  solution/solve.sh
```

`task.toml` usually contains:

```toml
version = "1.0"

[metadata]
difficulty = "medium"
category = "file-management"
tags = ["file-management", "pdf"]

[verifier]
timeout_sec = 900.0

[agent]
timeout_sec = 900.0

[environment]
build_timeout_sec = 1200.0
cpus = 4
memory_mb = 4096
storage_mb = 20480
```

## How The Harness Uses This Layout

The harness does not copy the full Harbor project. It treats Harbor as the task format reference:

- `instruction.md` is the task prompt consumed by your backend / CLI adapter.
- `task.toml` provides metadata for manifest generation.
- `environment/` and `tests/` stay inside each task directory.
- `solution/` is not used by normal agent runs.
- `relative_task_path` in the manifest points to `tasks/<task-id>` relative to `--task-root`.

For real benchmark runs, keep tasks outside the harness and pass:

```bash
--task-root /path/to/skillsbench/tasks
```

Manifest row example:

```csv
task_id,suite,relative_task_path,difficulty,domain,tags,eval_type,eval_command,timeout_sec
organize-messy-files,core30,organize-messy-files,medium,file-management,file-management;pdf,harbor,harbor run -p {task_dir} -a oracle,900
```

## Evaluation Commands

There are two common evaluation modes:

1. Local toy tasks:

```text
eval_command = ./checker.sh
```

2. Harbor-style tasks:

```text
eval_command = harbor run -p {task_dir} -a oracle
```

The harness formats these placeholders before running eval:

```text
{task_dir}
{run_dir}
{task_id}
{model}
{cli}
{timeout_sec}
```

If your real backend already runs verification and returns a trusted pass/fail summary, keep a lightweight local checker or use a no-op verification command only for smoke. For final benchmark numbers, prefer the Harbor verifier path.

## Generate A Manifest From Tasks

Use:

```bash
python scripts/build_manifest_from_harbor_tasks.py \
  --task-root tasks \
  --suite core30 \
  --out configs/manifests/core30.local.csv \
  --eval-command 'harbor run -p {task_dir} -a oracle'
```

For Full80:

```bash
python scripts/build_manifest_from_harbor_tasks.py \
  --task-root tasks \
  --suite full80 \
  --out configs/manifests/full80.local.csv \
  --task-list configs/task_lists/full80.txt \
  --eval-command 'harbor run -p {task_dir} -a oracle'
```

The generated `*.local.csv` files should stay local if they reveal private subsets or paths.
