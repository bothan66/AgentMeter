#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", required=True)
    args = parser.parse_args()

    root = Path(args.runs)
    summaries = list(root.rglob("summary.json"))
    if not summaries:
        raise SystemExit("no summary.json files found")

    seen = {"anthropic": False, "responses": False, "completions": False, "agentmeter": False}
    for summary_path in summaries:
        summary = load_json(summary_path)
        cli = str(summary["cli"])
        usage = load_json(summary_path.parent / "usage.json")
        trajectory = (summary_path.parent / "trajectory.jsonl").read_text(encoding="utf-8")

        if cli == "anthropic_cli_mock":
            seen["anthropic"] = True
            assert usage["cache_creation_tokens"] > 0
            assert usage["cache_hit_tokens"] > 0
            assert '"cache_creation_tokens"' in trajectory
        elif cli == "responses_cli_mock":
            seen["responses"] = True
            assert usage["cache_creation_tokens"] == 0
            assert usage["cache_hit_tokens"] > 0
            assert '"cache_hit_tokens"' in trajectory
        elif cli == "completions_cli_mock":
            seen["completions"] = True
            assert usage["cache_creation_tokens"] == 0
            assert usage["cache_hit_tokens"] > 0
            assert '"cache_hit_tokens"' in trajectory
        elif cli == "agentmeter_cli_mock":
            seen["agentmeter"] = True
            assert usage["cache_hit_tokens"] > 0

    missing = [name for name, ok in seen.items() if not ok]
    if missing:
        raise SystemExit(f"missing smoke formats: {missing}")
    print(f"validated {len(summaries)} summaries across {', '.join(sorted(seen))}")


if __name__ == "__main__":
    main()
