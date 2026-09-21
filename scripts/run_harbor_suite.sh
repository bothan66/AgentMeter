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

[[ -f "${task_list}" && -d "${task_root}" ]] || { echo "Task list or task root not found" >&2; exit 3; }
declare -A seen_tasks=()
task_ids=()
task_paths=()
while IFS= read -r task_id || [[ -n "${task_id}" ]]; do
  task_id=${task_id%$'\r'}
  [[ -z "${task_id}" || "${task_id}" == \#* ]] && continue
  [[ "${task_id}" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] || { echo "Invalid task ID: ${task_id}" >&2; exit 3; }
  [[ -z "${seen_tasks[$task_id]:-}" ]] || { echo "Duplicate task: ${task_id}" >&2; exit 3; }
  seen_tasks[$task_id]=1
  mapfile -t matches < <(find "${task_root}" -type f -path "*/${task_id}/instruction.md" -printf '%h\n')
  if ((${#matches[@]} != 1)); then
    echo "Expected exactly one task directory for ${task_id}; found ${#matches[@]}" >&2
    exit 3
  fi
  [[ -f "${matches[0]}/task.toml" && -f "${matches[0]}/tests/test.sh" ]] || { echo "Incomplete task: ${task_id}" >&2; exit 3; }
  task_ids+=("${task_id}")
  task_paths+=("${matches[0]}")
done < "${task_list}"
((${#task_ids[@]})) || { echo "Task list is empty" >&2; exit 3; }

# Validate the full selection before starting any paid execution.
mkdir -p "${jobs_dir}"
for index in "${!task_ids[@]}"; do
  task_id=${task_ids[$index]}
  "${harbor_bin}" run \
    -p "${task_paths[$index]}" \
    -a "${agent}" \
    -m "${model}" \
    "${agent_args[@]}" \
    -e docker -k 1 -n 1 \
    --job-name "agentmeter_${task_id}_${model_slug}_${agent}" \
    --jobs-dir "${jobs_dir}"
done
