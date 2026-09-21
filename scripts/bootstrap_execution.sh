#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
vendor_dir=${AGENTMETER_VENDOR_DIR:-${repo_root}/vendor}
install=1
harbor_already_patched=0

usage() {
  cat <<'EOF'
Usage: bash scripts/bootstrap_execution.sh [OPTIONS]

Prepare AgentMeter's pinned execution dependencies.

Options:
  --prepare-only      Clone and patch without installing Harbor into Python.
  --vendor-dir PATH   Store dependency checkouts under PATH (default: vendor/).
  -h, --help          Show this help.

This script prepares Harbor only. The 16 released tasks are already bundled;
larger task checkouts remain external. Credentials are not read or written.
EOF
}

while (($#)); do
  case "$1" in
    --prepare-only) install=0; shift ;;
    --vendor-dir)
      (($# >= 2)) || { echo "--vendor-dir requires a path" >&2; exit 2; }
      vendor_dir=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

command -v git >/dev/null || { echo "git is required" >&2; exit 3; }
command -v python >/dev/null || { echo "python is required" >&2; exit 3; }
command -v sha256sum >/dev/null || { echo "sha256sum is required" >&2; exit 3; }

mapfile -t lock_values < <(python - "${repo_root}/integrations/execution-lock.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
for section, key in (("harbor", "repository"), ("harbor", "commit")):
    print(data[section][key])
PY
)
harbor_repository=${lock_values[0]}
harbor_commit=${lock_values[1]}

python - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit("Harbor requires Python 3.12 or newer")
PY

mkdir -p "${vendor_dir}"

checkout_pinned() {
  local repository=$1 commit=$2 destination=$3
  local created=0
  if [[ -e "${destination}" && ! -d "${destination}/.git" ]]; then
    echo "Refusing to replace non-Git path: ${destination}" >&2
    return 3
  fi
  if [[ ! -d "${destination}/.git" ]]; then
    mkdir -p "${destination}"
    git -C "${destination}" init --quiet
    git -C "${destination}" remote add origin "${repository}"
    git -C "${destination}" fetch --depth 1 --filter=blob:none origin "${commit}"
    created=1
  fi
  git -C "${destination}" cat-file -e "${commit}^{commit}" 2>/dev/null || \
    git -C "${destination}" fetch --depth 1 origin "${commit}"
  local current
  current=$(git -C "${destination}" rev-parse HEAD 2>/dev/null || true)
  if ((created)); then
    git -C "${destination}" checkout --detach "${commit}"
    return
  fi
  if [[ -n "$(git -C "${destination}" status --porcelain 2>/dev/null)" ]]; then
    local marker=${destination}/.git/agentmeter-patched-commit
    local diff_hash marker_commit marker_hash
    diff_hash=$(git -C "${destination}" diff --binary HEAD | sha256sum | awk '{print $1}')
    marker_commit=$(sed -n '1p' "${marker}" 2>/dev/null || true)
    marker_hash=$(sed -n '2p' "${marker}" 2>/dev/null || true)
    if [[ "${marker_commit}" != "${commit}" || "${marker_hash}" != "${diff_hash}" ]]; then
      echo "Refusing to alter a dirty Harbor checkout: ${destination}" >&2
      return 3
    fi
    harbor_already_patched=1
  fi
  if [[ "${current}" != "${commit}" ]]; then
    git -C "${destination}" checkout --detach "${commit}"
  fi
}

apply_patch_once() {
  local checkout=$1 patch=$2
  if git -C "${checkout}" apply --check "${patch}" 2>/dev/null; then
    git -C "${checkout}" apply "${patch}"
  elif git -C "${checkout}" apply --reverse --check "${patch}" 2>/dev/null; then
    echo "Already applied: $(basename "${patch}")"
  else
    echo "Patch does not apply cleanly: ${patch}" >&2
    return 4
  fi
}

harbor_dir=${vendor_dir}/harbor
checkout_pinned "${harbor_repository}" "${harbor_commit}" "${harbor_dir}"
if ((harbor_already_patched)); then
  echo "AgentMeter Harbor patches already applied"
else
  apply_patch_once "${harbor_dir}" "${repo_root}/integrations/harbor/compatibility.patch"
  apply_patch_once "${harbor_dir}" "${repo_root}/integrations/harbor/provider-auth.patch"
  harbor_diff_hash=$(git -C "${harbor_dir}" diff --binary HEAD | sha256sum | awk '{print $1}')
  printf '%s\n%s\n' "${harbor_commit}" "${harbor_diff_hash}" > "${harbor_dir}/.git/agentmeter-patched-commit"
fi

if ((install)); then
  python -m pip install -e "${harbor_dir}"
  command -v harbor >/dev/null || { echo "Harbor installation did not provide the harbor command" >&2; exit 5; }
  harbor --help >/dev/null
fi

printf 'Bundled AgentMeter task root: %s\n' "${repo_root}/benchmark_tasks"
printf 'Pinned Harbor prepared at: %s\n' "${harbor_dir}"
if ((install)); then printf 'Harbor command: %s\n' "$(command -v harbor)"; fi
