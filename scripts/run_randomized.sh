#!/usr/bin/env bash
# Created at: 2026-11-14 02:51 EST
# Created by: Codex
# Last Modified at: 2026-11-14 02:51 EST
# Last Modified by: Codex
# Builds, runs, and repeats the deterministic randomized invariant executable.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
ticks="100000"
seed="0x5eed1234cafebabe"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ticks) ticks="$2"; shift 2 ;;
    --seed) seed="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

cd "${project_dir}"
"${project_dir}/.venv/bin/pio" run -e native_randomized >/dev/null
first="$("${project_dir}/.pio/build/native_randomized/program" --ticks "${ticks}" --seed "${seed}")"
second="$("${project_dir}/.pio/build/native_randomized/program" --ticks "${ticks}" --seed "${seed}")"
printf '%s\n' "${first}"
[[ "${first}" == "${second}" ]]
grep -q "^RANDOMIZED_OK ticks=${ticks} " <<<"${first}"
