#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
task_list=${1:?Usage: run_harbor_suite.sh TASK_LIST}
task_root=${AGENTMETER_TASK_ROOT:?Set AGENTMETER_TASK_ROOT to the benchmark task checkout}
harbor_bin=${AGENTMETER_HARBOR_BIN:-harbor}
model=${AGENTMETER_MODEL:?Set AGENTMETER_MODEL}
agent=${AGENTMETER_AGENT:?Set AGENTMETER_AGENT}
run_id=${AGENTMETER_RUN_ID:-$(date -u +%Y%m%dT%H%M%S)_$$}
model_slug=${model//\//_}
jobs_dir=${AGENTMETER_JOBS_DIR:-${repo_root}/jobs/$(basename "${task_list}" .txt)_${model_slug}_${agent}_${run_id}}
agent_args=()
if [[ -n "${AGENTMETER_AGENT_VERSION:-}" ]]; then
  agent_args+=(--ak "version=${AGENTMETER_AGENT_VERSION}")
fi

mkdir -p "${jobs_dir}"
while IFS= read -r task_id; do
  [[ -z "${task_id}" || "${task_id}" == \#* ]] && continue
  mapfile -t matches < <(find "${task_root}" -type f -path "*/${task_id}/instruction.md" -printf '%h\n')
  if ((${#matches[@]} != 1)); then
    echo "Expected exactly one task directory for ${task_id}; found ${#matches[@]}" >&2
    exit 3
  fi
  "${harbor_bin}" run \
    -p "${matches[0]}" \
    -a "${agent}" \
    -m "${model}" \
    "${agent_args[@]}" \
    -e docker -k 1 -n 1 \
    --job-name "agentmeter_${task_id}_${model_slug}_${agent}" \
    --jobs-dir "${jobs_dir}"
done < "${task_list}"
