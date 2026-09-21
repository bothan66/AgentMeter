#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_pair=${1:?Usage: run_agentmeter_comparison.sh SOURCE_PAIR original|optimized [TASK ...]}
variant=${2:?Usage: run_agentmeter_comparison.sh SOURCE_PAIR original|optimized [TASK ...]}
shift 2

case "${source_pair}" in
  qwen36_kimi_cli|qwen36_codex|deepseek_v4_kimi_cli|glm51_qwen_coder) ;;
  *) echo "Unknown source pair: ${source_pair}" >&2; exit 2 ;;
esac
case "${variant}" in original|optimized) ;; *) echo "Variant must be original or optimized" >&2; exit 2 ;; esac

if (($# == 0)); then
  # Both conditions use the same released task subset for paired comparisons.
  mapfile -t tasks < <(find "${repo_root}/artifacts/agentmeter_opt_final16/descriptions/${source_pair}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort)
  ((${#tasks[@]})) || { echo "No released examples for source: ${source_pair}" >&2; exit 3; }
else
  tasks=("$@")
fi

harbor_bin=${AGENTMETER_HARBOR_BIN:-harbor}
# Check the entire selection before starting any paid execution.
if [[ "${variant}" == optimized ]]; then
  for task_id in "${tasks[@]}"; do
    [[ -f "${repo_root}/artifacts/agentmeter_opt_final16/descriptions/${source_pair}/${task_id}/optimized_instruction.md" ]] || { echo "Optimized description not included in this example release: ${source_pair}/${task_id}" >&2; exit 3; }
  done
fi
model=${AGENTMETER_MODEL:?Set AGENTMETER_MODEL for the target pair}
agent=${AGENTMETER_AGENT:?Set AGENTMETER_AGENT for the target CLI}
run_id=${AGENTMETER_RUN_ID:-$(date -u +%Y%m%dT%H%M%S)_$$}
target_slug=${model//\//_}_${agent}
jobs_dir=${AGENTMETER_JOBS_DIR:-${repo_root}/jobs/final16_${source_pair}_${variant}_${target_slug}_${run_id}}
find_task() {
  local task_id=$1 candidate
  for family in skillsbench terminal_bench da_code; do
    candidate="${repo_root}/benchmark_tasks/${family}/${task_id}"
    if [[ -f "${candidate}/instruction.md" && -f "${candidate}/task.toml" ]]; then printf '%s\n' "${candidate}"; return 0; fi
  done
  return 1
}

# Validate the full batch before creating snapshots or invoking Harbor.
declare -A seen_tasks=()
for task_id in "${tasks[@]}"; do
  [[ "${task_id}" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] || { echo "Invalid task ID: ${task_id}" >&2; exit 3; }
  [[ -z "${seen_tasks[$task_id]:-}" ]] || { echo "Duplicate task: ${task_id}" >&2; exit 3; }
  seen_tasks[$task_id]=1
  find_task "${task_id}" >/dev/null || { echo "Missing task: ${task_id}" >&2; exit 3; }
  [[ ! -e "${jobs_dir}/task_snapshots/${task_id}" ]] || { echo "Task snapshot already exists: ${task_id}; select a new jobs directory" >&2; exit 3; }
done
# Retain exact evaluated instructions and task paths for auditing/resume.
mkdir -p "${jobs_dir}/task_snapshots"
jobs_dir=$(cd "${jobs_dir}" && pwd)
tmp_root=${jobs_dir}/task_snapshots
agent_args=()
if [[ -n "${AGENTMETER_AGENT_VERSION:-}" ]]; then
  agent_args+=(--ak "version=${AGENTMETER_AGENT_VERSION}")
fi

mkdir -p "${jobs_dir}"
for task_id in "${tasks[@]}"; do
  task_source=$(find_task "${task_id}") || { echo "Missing task: ${task_id}" >&2; exit 3; }
  task_copy="${tmp_root}/${task_id}"
  [[ ! -e "${task_copy}" ]] || { echo "Task snapshot already exists: ${task_copy}; select a new jobs directory" >&2; exit 3; }
  cp -a "${task_source}" "${task_copy}"

  description_dir="${repo_root}/artifacts/agentmeter_opt_final16/descriptions/${source_pair}/${task_id}"
  if [[ "${variant}" == optimized ]]; then
    cp "${description_dir}/optimized_instruction.md" "${task_copy}/instruction.md"
  else
    cp "${task_source}/instruction.md" "${task_copy}/instruction.md"
  fi

  "${harbor_bin}" run \
    -p "${task_copy}" \
    -a "${agent}" \
    -m "${model}" \
    "${agent_args[@]}" \
    -e docker -k 1 -n 1 \
    --job-name "final16_${task_id}_${source_pair}_${variant}" \
    --jobs-dir "${jobs_dir}"
done
