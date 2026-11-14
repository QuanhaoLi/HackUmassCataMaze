#!/usr/bin/env bash
# Created at: 2026-11-14 04:44 EST
# Created by: Codex
# Last Modified at: 2026-11-14 05:02 EST
# Last Modified by: Codex
# Preflights, uploads only diagnostic firmware, captures Serial, and asserts physical evidence.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
artifact_dir="${project_dir}/.artifacts/esp32"
mkdir -p "${artifact_dir}"

"${script_dir}/esp32_preflight.sh"
port="$("${script_dir}/esp32_detect_port.sh")"
cd "${project_dir}"
"${project_dir}/.venv/bin/pio" run -e esp32s3_diagnostic
"${project_dir}/.venv/bin/pio" run -e esp32s3_diagnostic -t upload \
  --upload-port "${port}"

for _ in {1..100}; do
  if next_port="$("${script_dir}/esp32_detect_port.sh" 2>/dev/null)"; then
    port="${next_port}"
    break
  fi
  sleep 0.05
done

"${project_dir}/.venv/bin/python" "${script_dir}/esp32_capture_serial.py" \
  --port "${port}" --seconds 10 --require-prefix 'CATAMAZE_DIAG ' | \
  tee "${artifact_dir}/diagnostic-serial.log"

diag_json="$(sed -n 's/^CATAMAZE_DIAG //p' "${artifact_dir}/diagnostic-serial.log" | head -n 1)"
[[ -n "${diag_json}" ]]
jq -e '
  .schema == "catamaze.diag.v1" and
  .flash_bytes == 16777216 and
  .psram_found == true and
  .psram_bytes == 8388608 and
  .map_bus_started == true and .map_i2c_count == 1 and .map_i2c_address == 60 and
  .map_sda_high == true and .map_scl_high == true and
  .hud_bus_started == true and .hud_i2c_count == 1 and .hud_i2c_address == 60 and
  .hud_sda_high == true and .hud_scl_high == true and
  .gpio4_configured == false and .pass == true
' <<<"${diag_json}" >/dev/null

printf 'ESP32_DIAGNOSTIC_OK port=%s\n' "${port}"
