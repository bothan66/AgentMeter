#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from harness_lib import read_json, write_csv


FIELDS = [
    "task_id",
    "suite",
    "difficulty",
    "domain",
    "tags",
    "model",
    "cli",
    "attempt",
    "passed",
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "cache_hit_tokens",
    "total_cost_cny",
    "turns",
    "tool_calls",
    "duration_sec",
    "exit_code",
    "error",
    "run_dir",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    rows = [read_json(path) for path in sorted(Path(args.runs).rglob("summary.json"))]
    write_csv(args.out, rows, fieldnames=FIELDS)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
