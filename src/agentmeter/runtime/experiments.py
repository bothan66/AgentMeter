"""Plan complete experiment batches before launching any paid execution.

Planning is side-effect free. Comparison runs retain the exact evaluated task
and instruction in a snapshot; Harbor receives credentials through the inherited
environment, never through generated files or command-line arguments.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

SOURCE_PAIRS = (
    "qwen36_kimi_cli",
    "qwen36_codex",
    "deepseek_v4_kimi_cli",
    "glm51_qwen_coder",
)
TASK_FAMILIES = ("skillsbench", "terminal_bench", "da_code")
TASK_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*\Z")


@dataclass(frozen=True)
class RunOptions:
    """Execution settings shared by the comparison and benchmark runners."""

    model: str
    agent: str
    harbor: str = "harbor"
    agent_version: str | None = None

    @classmethod
    def from_environment(
        cls,
        *,
        model: str | None = None,
        agent: str | None = None,
        harbor: str | None = None,
        agent_version: str | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> RunOptions:
        env = os.environ if environment is None else environment
        model = model or env.get("AGENTMETER_MODEL")
        agent = agent or env.get("AGENTMETER_AGENT")
        if not model or not agent:
            raise ValueError("Set --model and --agent (or AGENTMETER_MODEL and AGENTMETER_AGENT)")
        return cls(
            model,
            agent,
            harbor or env.get("AGENTMETER_HARBOR_BIN", "harbor"),
            agent_version or env.get("AGENTMETER_AGENT_VERSION"),
        )


@dataclass(frozen=True)
class TaskRun:
    task_id: str
    source: Path
    execution_path: Path
    job_name: str
    instruction: Path | None = None


@dataclass(frozen=True)
class RunPlan:
    """An immutable, validated batch. Construct via a plan_* function."""

    jobs_dir: Path
    options: RunOptions
    tasks: tuple[TaskRun, ...]

    def command(self, task: TaskRun) -> list[str]:
        args = [
            self.options.harbor,
            "run",
            "-p",
            str(task.execution_path),
            "-a",
            self.options.agent,
            "-m",
            self.options.model,
        ]
        if self.options.agent_version:
            args.extend(["--ak", f"version={self.options.agent_version}"])
        return args + [
            "-e",
            "docker",
            "-k",
            "1",
            "-n",
            "1",
            "--job-name",
            task.job_name,
            "--jobs-dir",
            str(self.jobs_dir),
        ]


def _validated_ids(task_ids: Sequence[str]) -> tuple[str, ...]:
    if not task_ids:
        raise ValueError("Task list is empty")
    seen = set()
    for task_id in task_ids:
        if not TASK_ID.fullmatch(task_id):
            raise ValueError(f"Invalid task ID: {task_id}")
        if task_id in seen:
            raise ValueError(f"Duplicate task: {task_id}")
        seen.add(task_id)
    return tuple(task_ids)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]", "_", value)


def _jobs_path(repo: Path, prefix: str, options: RunOptions, jobs_dir: Path | None) -> Path:
    if jobs_dir is not None:
        return Path(jobs_dir).expanduser().resolve()
    if os.environ.get("AGENTMETER_JOBS_DIR"):
        return Path(os.environ["AGENTMETER_JOBS_DIR"]).expanduser().resolve()
    run_id = os.environ.get("AGENTMETER_RUN_ID") or (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f") + f"_{os.getpid()}"
    )
    return repo / "jobs" / f"{prefix}_{_slug(options.model)}_{_slug(options.agent)}_{_slug(run_id)}"


def _check_destinations(jobs_dir: Path, tasks: Sequence[TaskRun]) -> None:
    for task in tasks:
        if task.instruction is not None and os.path.lexists(task.execution_path):
            raise ValueError(
                f"Task snapshot already exists: {task.task_id}; select a new jobs directory"
            )
        if os.path.lexists(jobs_dir / task.job_name):
            raise ValueError(
                f"Harbor job already exists: {task.job_name}; select a new jobs directory"
            )


def plan_comparison(
    repo: Path,
    source_pair: str,
    variant: str,
    task_ids: Sequence[str],
    options: RunOptions,
    *,
    jobs_dir: Path | None = None,
) -> RunPlan:
    """Select the same released subset for both description conditions."""
    repo = Path(repo).resolve()
    if source_pair not in SOURCE_PAIRS:
        raise ValueError(f"Unknown source pair: {source_pair}")
    if variant not in ("original", "optimized"):
        raise ValueError("Variant must be original or optimized")
    descriptions = repo / "artifacts/agentmeter_opt_final16/descriptions" / source_pair
    selected = tuple(task_ids) or tuple(
        sorted(p.name for p in descriptions.iterdir() if p.is_dir())
    )
    selected = _validated_ids(selected)
    jobs = _jobs_path(repo, f"final16_{source_pair}_{variant}", options, jobs_dir)
    tasks = []
    for task_id in selected:
        sources = [repo / "benchmark_tasks" / family / task_id for family in TASK_FAMILIES]
        source = next(
            (
                p
                for p in sources
                if (p / "instruction.md").is_file() and (p / "task.toml").is_file()
            ),
            None,
        )
        if source is None:
            raise ValueError(f"Missing task: {task_id}")
        if any(
            not (source / name).is_file() for name in ("tests/test.sh", "environment/Dockerfile")
        ):
            raise ValueError(f"Incomplete task: {task_id}")
        instruction = (
            descriptions / task_id / "optimized_instruction.md"
            if variant == "optimized"
            else source / "instruction.md"
        )
        if not instruction.is_file():
            raise ValueError(
                f"Optimized description not included in this example release: {source_pair}/{task_id}"
            )
        tasks.append(
            TaskRun(
                task_id,
                source,
                jobs / "task_snapshots" / task_id,
                f"final16_{task_id}_{source_pair}_{variant}",
                instruction,
            )
        )
    _check_destinations(jobs, tasks)
    return RunPlan(jobs, options, tuple(tasks))


def plan_suite(
    repo: Path,
    task_list: Path,
    task_root: Path,
    options: RunOptions,
    *,
    jobs_dir: Path | None = None,
) -> RunPlan:
    """Resolve an external task list, rejecting missing or ambiguous tasks."""
    task_list, task_root = Path(task_list), Path(task_root).expanduser().resolve()
    if not task_list.is_file() or not task_root.is_dir():
        raise ValueError("Task list or task root not found")
    selected = _validated_ids(
        [
            line.strip()
            for line in task_list.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    )
    index: dict[str, list[Path]] = {task_id: [] for task_id in selected}
    for instruction in task_root.rglob("instruction.md"):
        if instruction.parent.name in index and instruction.is_file():
            index[instruction.parent.name].append(instruction.parent)
    jobs = _jobs_path(Path(repo).resolve(), task_list.stem, options, jobs_dir)
    tasks = []
    for task_id in selected:
        matches = index[task_id]
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one task directory for {task_id}; found {len(matches)}"
            )
        source = matches[0]
        if not (source / "task.toml").is_file() or not (source / "tests/test.sh").is_file():
            raise ValueError(f"Incomplete task: {task_id}")
        tasks.append(
            TaskRun(
                task_id,
                source,
                source,
                f"agentmeter_{task_id}_{_slug(options.model)}_{_slug(options.agent)}",
            )
        )
    _check_destinations(jobs, tasks)
    return RunPlan(jobs, options, tuple(tasks))


def run_plan(plan: RunPlan) -> None:
    """Materialize comparison snapshots and execute Harbor sequentially.

    Snapshot checks happen again immediately before writing, so a previously
    planned run cannot overwrite results produced in the meantime.
    """
    _check_destinations(plan.jobs_dir, plan.tasks)
    if shutil.which(plan.options.harbor) is None:
        raise ValueError(
            f"Harbor executable not found: {plan.options.harbor}; run agentmeter setup first"
        )
    plan.jobs_dir.mkdir(parents=True, exist_ok=True)
    for task in plan.tasks:
        if task.instruction is not None:
            # copytree refuses existing destinations, including concurrent runs.
            shutil.copytree(task.source, task.execution_path, symlinks=True)
            instruction = task.execution_path / "instruction.md"
            if instruction.is_symlink():
                instruction.unlink()
            shutil.copyfile(task.instruction, instruction)
    for task in plan.tasks:
        subprocess.run(plan.command(task), check=True)
