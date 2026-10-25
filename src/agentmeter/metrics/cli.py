#!/usr/bin/env python3
"""Compute the AgentMeter Score (AMS) from a one-condition task CSV."""

import argparse
import csv
import json
from pathlib import Path

from agentmeter.metrics.agentmeter_score import compute_ams
from agentmeter.paths import find_repository


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agentmeter score", description=__doc__)
    parser.add_argument("--runs", required=True, help="CSV: task_id,stratum,reward,cost_usd")
    parser.add_argument(
        "--calibration",
        type=Path,
        help="Frozen AMS calibration JSON; defaults to the research checkout",
    )
    args = parser.parse_args(argv)
    calibration_path = (
        args.calibration or find_repository() / "configs/paper_calibration_full_precision.json"
    )
    with open(args.runs, newline="") as f:
        rows = list(csv.DictReader(f))
    with open(calibration_path) as f:
        calibration = json.load(f)
    print(json.dumps(compute_ams(rows, calibration), indent=2))


if __name__ == "__main__":
    main()
