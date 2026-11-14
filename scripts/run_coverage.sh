#!/usr/bin/env bash
# Created at: 2026-11-14 02:51 EST
# Created by: Codex
# Last Modified at: 2026-11-14 02:55 EST
# Last Modified by: Codex
# Measures portable core/application coverage and enforces M3 line and branch thresholds.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
artifact_dir="${project_dir}/.artifacts/coverage"
mkdir -p "${artifact_dir}"
run_dir="$(mktemp -d "${artifact_dir}/run.XXXXXX")"
profile_data="${run_dir}/core.profdata"
report_file="${run_dir}/report.txt"
cd "${project_dir}"
LLVM_PROFILE_FILE="${run_dir}/core-%p.profraw" \
  "${project_dir}/.venv/bin/pio" test -e native_coverage -f native/test_core

xcrun llvm-profdata merge -sparse "${run_dir}"/core-*.profraw \
  -o "${profile_data}"
xcrun llvm-cov report "${project_dir}/.pio/build/native_coverage/program" \
  -instr-profile="${profile_data}" \
  -ignore-filename-regex='(.pio/|test/|src/native/|lib/catamaze_render/)' \
  | tee "${report_file}"

total_line="$(awk '$1 == "TOTAL" {print; exit}' "${report_file}")"
[[ -n "${total_line}" ]]
line_coverage="$(awk '$1 == "TOTAL" {gsub(/%/, "", $10); print $10; exit}' "${report_file}")"
branch_coverage="$(awk '$1 == "TOTAL" {gsub(/%/, "", $13); print $13; exit}' "${report_file}")"
awk -v value="${line_coverage}" 'BEGIN { exit !(value >= 85.0) }'
awk -v value="${branch_coverage}" 'BEGIN { exit !(value >= 75.0) }'
printf 'COVERAGE_OK lines=%s%% branches=%s%%\n' \
  "${line_coverage}" "${branch_coverage}"
