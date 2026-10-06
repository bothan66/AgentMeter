"""Register execution commands with the public AgentMeter CLI."""

from __future__ import annotations

import argparse
import os
import shlex
from pathlib import Path

from agentmeter.paths import find_repository

from .experiments import SOURCE_PAIRS, RunOptions, plan_comparison, plan_suite, run_plan
from .setup import setup_runtime


def _setup(args: argparse.Namespace) -> int:
    checkout = setup_runtime(
        find_repository(args.repo_root), vendor_dir=args.vendor_dir, install=not args.prepare_only
    )
    print(f"Pinned Harbor prepared at: {checkout}")
    return 0


def _execute(args: argparse.Namespace) -> int:
    repo = find_repository(args.repo_root)
    options = RunOptions.from_environment(
        model=args.model,
        agent=args.agent,
        harbor=args.harbor,
        agent_version=args.agent_version,
        setup_timeout_multiplier=args.setup_timeout_multiplier,
    )
    if args.command == "compare":
        plan = plan_comparison(
            repo, args.source_pair, args.variant, args.tasks, options, jobs_dir=args.jobs_dir
        )
    else:
        task_root = args.task_root or os.environ.get("AGENTMETER_TASK_ROOT")
        if not task_root:
            raise ValueError(
                "Set --task-root or AGENTMETER_TASK_ROOT to the external benchmark checkout"
            )
        plan = plan_suite(repo, args.task_list, Path(task_root), options, jobs_dir=args.jobs_dir)
    print(f"Jobs directory: {plan.jobs_dir}")
    for task in plan.tasks:
        if task.instruction is not None:
            print(
                f"Snapshot: {task.source} -> {task.execution_path}; instruction: {task.instruction}"
            )
        print(shlex.join(plan.command(task)))
    if not args.dry_run:
        run_plan(plan)
    return 0


def register_subcommands(subparsers: argparse._SubParsersAction) -> None:
    setup = subparsers.add_parser("setup", help="Install pinned Harbor and AgentMeter adapters")
    setup.add_argument(
        "--repo-root", type=Path, help="AgentMeter repository (auto-detected by default)"
    )
    setup.add_argument("--vendor-dir", type=Path, help="Dependency checkout directory")
    setup.add_argument(
        "--prepare-only", action="store_true", help="Clone and patch without pip install"
    )
    setup.set_defaults(handler=_setup)

    comparison = subparsers.add_parser(
        "compare", help="Run original or optimized released task descriptions"
    )
    comparison.add_argument(
        "source_pair", choices=SOURCE_PAIRS, help="Source model-harness pair of the rewrite"
    )
    comparison.add_argument("variant", choices=("original", "optimized"))
    comparison.add_argument(
        "tasks", nargs="*", help="Task IDs; default: released examples for this source pair"
    )
    suite = subparsers.add_parser(
        "suite", help="Run a task list from an external benchmark checkout"
    )
    suite.add_argument("task_list", type=Path)
    suite.add_argument(
        "--task-root", type=Path, help="External task directory (or AGENTMETER_TASK_ROOT)"
    )
    for parser in (comparison, suite):
        parser.add_argument(
            "--repo-root", type=Path, help="AgentMeter repository (auto-detected by default)"
        )
        parser.add_argument("--model", help="Target model (or AGENTMETER_MODEL)")
        parser.add_argument("--agent", help="Target Harbor agent (or AGENTMETER_AGENT)")
        parser.add_argument(
            "--agent-version", help="Agent CLI version (or AGENTMETER_AGENT_VERSION)"
        )
        parser.add_argument("--harbor", help="Harbor executable (or AGENTMETER_HARBOR_BIN)")
        parser.add_argument(
            "--setup-timeout-multiplier",
            type=float,
            help="Scale CLI installation time only; leaves agent and verifier budgets unchanged",
        )
        parser.add_argument(
            "--jobs-dir", type=Path, help="Output directory (or AGENTMETER_JOBS_DIR)"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Print the validated run plan without execution"
        )
        parser.set_defaults(handler=_execute)
