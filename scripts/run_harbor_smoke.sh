#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
task_root=${AGENTMETER_TASK_ROOT:?Set AGENTMETER_TASK_ROOT to a SkillsBench task directory}
harbor_bin=${AGENTMETER_HARBOR_BIN:-harbor}
model=${AGENTMETER_MODEL:-deepseek-v4-pro}
codex_version=${AGENTMETER_CODEX_VERSION:-0.153.0}
jobs_dir=${AGENTMETER_JOBS_DIR:-${repo_root}/jobs/api_smoke}

if (($# == 0)); then
  set -- organize-messy-files court-form-filling
fi

mkdir -p "${jobs_dir}"
for task_id in "$@"; do
  task_path="${task_root}/${task_id}"
  test -f "${task_path}/instruction.md"
  job_name="agentmeter_api_smoke_${task_id}_${model//\//_}_codex"
  "${harbor_bin}" run \
    -p "${task_path}" \
    -a codex \
    -m "${model}" \
    --ak "version=${codex_version}" \
    -e docker -k 1 -n 1 \
    --timeout-multiplier 2.0 \
    --job-name "${job_name}" \
    --jobs-dir "${jobs_dir}"
done
