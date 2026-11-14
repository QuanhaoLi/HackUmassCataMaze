#!/usr/bin/env bash
# Created at: 2026-11-14 02:26 EST
# Created by: Codex
# Last Modified at: 2026-11-14 02:32 EST
# Last Modified by: Codex
# Builds and executes a bounded headless Native gameplay acceptance check.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
mode="${2:-${1:-headless}}"

if [[ "${1:-}" == "--mode" ]]; then
  mode="${2:-}"
fi
if [[ "${mode}" != "headless" ]]; then
  echo "native_smoke.sh currently supports only --mode headless" >&2
  exit 2
fi

cd "${project_dir}"
"${project_dir}/.venv/bin/pio" run -e native >/dev/null
output="$("${project_dir}/.pio/build/native/program" --seed 0x134fd5a --auto 32)"
printf '%s\n' "${output}"
grep -q '^CATAMAZE_HEADLESS_OK tick=' <<<"${output}"
