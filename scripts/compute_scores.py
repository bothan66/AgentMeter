#!/usr/bin/env python3
"""Summarize development-run diagnostics. For manuscript AMS use compute_paper_ams.py."""
from __future__ import annotations

import argparse
from pathlib import Path

from harness_lib import read_csv, summarize_scores, write_csv, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = read_csv(args.summary)
    scores = summarize_scores(rows)
    write_csv(out / "scores.csv", scores)
    write_json(out / "score_report.json", {"rows": len(rows), "groups": len(scores), "scores_csv": str(out / "scores.csv")})
    print(f"wrote {out / 'scores.csv'} and {out / 'score_report.json'}")


if __name__ == "__main__":
    main()
