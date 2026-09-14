#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
run_root="${repo_root}/runs/public_smoke"

python "${repo_root}/scripts/run_benchmark.py" \
  --experiment "${repo_root}/configs/experiments/smoke.example.yaml" \
  --task-root "${repo_root}/examples/toy_tasks" \
  --out "${run_root}" \
  --force
python "${repo_root}/scripts/summarize_runs.py" \
  --runs "${run_root}" --out "${run_root}/summary.csv"
python "${repo_root}/scripts/compute_scores.py" \
  --summary "${run_root}/summary.csv" --out "${run_root}"
python "${repo_root}/scripts/build_reports.py" \
  --runs "${run_root}" --out "${run_root}/report.md"

echo "Public smoke completed: ${run_root}"
