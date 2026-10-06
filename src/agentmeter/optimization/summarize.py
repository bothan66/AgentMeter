"""Summarize saved AgentMeter optimization results as CSV and Markdown."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

FIELDS = [
    "task_id",
    "baseline_passed",
    "optimized_passed",
    "baseline_tokens",
    "optimized_tokens",
    "token_delta_pct",
    "safety_status",
    "violations",
    "decision",
    "rewritten_instruction_path",
    "diff_path",
    "metric_calls",
    "real_reruns",
    "result_dir",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("gepa_task_result.json")):
        data = read_json(path)
        if not data.get("task_id"):
            continue
        row = {}
        for field in FIELDS:
            value = data.get(field, "")
            if field == "violations" and isinstance(value, list):
                value = ";".join(str(item) for item in value)
            row[field] = value
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# GEPA Full Instruction Optimization Summary",
        "",
        f"- Tasks summarized: {len(rows)}",
        "",
        "| task_id | baseline_passed | optimized_passed | baseline_tokens | optimized_tokens | token_delta_pct | safety_status | decision | metric_calls | real_reruns |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {task_id} | {baseline_passed} | {optimized_passed} | {baseline_tokens} | {optimized_tokens} | {token_delta_pct} | {safety_status} | {decision} | {metric_calls} | {real_reruns} |".format(
                **row
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="agentmeter summarize", description=__doc__)
    parser.add_argument(
        "--out-dir", type=Path, default=Path("generated_reports/agentmeter_opt_min")
    )
    args = parser.parse_args(argv)

    rows = collect_rows(args.out_dir)
    write_csv(args.out_dir / "agentmeter_opt_summary.csv", rows)
    write_md(args.out_dir / "agentmeter_opt_summary.md", rows)
    print(args.out_dir / "agentmeter_opt_summary.csv")
    print(args.out_dir / "agentmeter_opt_summary.md")


if __name__ == "__main__":
    main()
