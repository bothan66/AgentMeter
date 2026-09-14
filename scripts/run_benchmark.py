#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from harness_lib import Experiment, run_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--task-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--runner-config")
    parser.add_argument("--task-id", action="append", dest="task_ids")
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--cli", action="append", dest="clis")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    exp = Experiment.from_yaml(args.experiment)
    if args.models:
        exp = replace(exp, models=tuple(args.models))
    if args.clis:
        exp = replace(exp, clis=tuple(args.clis))
    summaries = run_experiment(
        exp,
        task_root=Path(args.task_root),
        out=Path(args.out),
        runner_config=args.runner_config,
        resume=args.resume or exp.resume,
        force=args.force,
        task_ids=set(args.task_ids) if args.task_ids else None,
    )
    print(f"completed {len(summaries)} attempts")


if __name__ == "__main__":
    main()
