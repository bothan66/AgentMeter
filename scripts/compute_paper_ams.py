#!/usr/bin/env python3
"""Score a one-condition task CSV using the manuscript AMS definition."""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from agentmeter.metrics.paper import paper_ams


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', required=True, help='CSV: task_id,stratum,reward,cost_usd')
    parser.add_argument('--calibration', default=str(ROOT / 'configs/paper_calibration.json'))
    args = parser.parse_args()
    with open(args.runs, newline='') as f:
        rows = list(csv.DictReader(f))
    with open(args.calibration) as f:
        calibration = json.load(f)
    print(json.dumps(paper_ams(rows, calibration), indent=2))


if __name__ == '__main__':
    main()
