"""Run a rewritten task through a configured agent service and verifier."""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path
from typing import Any

from agentmeter.harness import Experiment, TaskSpec, api_lookup, load_api_configs, run_attempt

from .text import write_text


def load_task_spec(
    task_root: Path, task_id: str, eval_command: str, default_timeout_sec: int
) -> TaskSpec:
    task_dir = task_root / task_id
    if not (task_dir / "instruction.md").exists():
        raise SystemExit(f"task instruction not found: {task_dir / 'instruction.md'}")
    toml_path = task_dir / "task.toml"
    data = tomllib.loads(toml_path.read_text(encoding="utf-8")) if toml_path.exists() else {}
    metadata = data.get("metadata") or {}
    verifier = data.get("verifier") or {}
    tags = metadata.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    timeout_sec = int(verifier.get("timeout_sec") or default_timeout_sec)
    return TaskSpec(
        task_id=task_id,
        suite="custom",
        relative_task_path=task_id,
        difficulty=str(metadata.get("difficulty") or "unknown"),
        domain=str(metadata.get("category") or "unknown"),
        tags=tuple(str(tag) for tag in tags),
        eval_type="harbor",
        eval_command=eval_command,
        timeout_sec=timeout_sec,
    )


def run_agent_task(
    *,
    original_task_root: Path,
    task_id: str,
    rewritten_instruction: str,
    runner_config: Path,
    model: str,
    cli: str,
    eval_command: str,
    default_timeout_sec: int,
    attempt: int,
    run_root: Path,
) -> dict[str, Any]:
    variant_task_root = run_root / "variant_task_root"
    variant_task_dir = variant_task_root / task_id
    source_task_dir = original_task_root / task_id
    shutil.copytree(source_task_dir, variant_task_dir, dirs_exist_ok=True)
    write_text(variant_task_dir / "instruction.md", rewritten_instruction)

    task = load_task_spec(variant_task_root, task_id, eval_command, default_timeout_sec)
    exp = Experiment(
        name="agentmeter_opt_one_task",
        manifest="",
        models=(model,),
        clis=(cli,),
        runner="api",
        attempts=1,
        timeout_sec=task.timeout_sec or default_timeout_sec,
        record_trajectory=True,
        save_stdout=True,
        save_stderr=True,
        save_patch=True,
        resume=False,
    )
    api_configs = load_api_configs(runner_config)
    api_lookup(api_configs, model, cli)
    rerun_root = run_root / "rerun"
    summary = run_attempt(
        task, variant_task_root, rerun_root, model, cli, attempt, exp, api_configs
    )
    return {
        "summary": summary,
        "run_dir": summary.get("run_dir"),
        "variant_task_dir": str(variant_task_dir),
    }
