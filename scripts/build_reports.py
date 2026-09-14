#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    runs = Path(args.runs)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    summary = runs / "summary.csv"
    scores = runs / "scores.csv"
    out.write_text(
        "# AgentMeter Run Report\n\n"
        f"- Runs: `{runs}`\n"
        f"- Summary CSV: `{summary}` ({'present' if summary.exists() else 'missing'})\n"
        f"- Scores CSV: `{scores}` ({'present' if scores.exists() else 'missing'})\n",
        encoding="utf-8",
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
