#!/usr/bin/env bash
# Created at: 2026-11-14 05:02 EST
# Created by: Codex
# Last Modified at: 2026-11-14 07:42 EST
# Last Modified by: Codex
# Gates product upload behind a fresh passing diagnostic and validates product boot evidence.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
artifact_dir="${project_dir}/.artifacts/esp32"
mkdir -p "${artifact_dir}"

cd "${project_dir}"
"${project_dir}/.venv/bin/pio" test -e native -f native/test_core
"${project_dir}/.venv/bin/pio" run -e esp32s3
"${script_dir}/esp32_upload_diagnostic.sh"
port="$("${script_dir}/esp32_detect_port.sh")"
"${project_dir}/.venv/bin/pio" run -e esp32s3 -t upload --upload-port "${port}"

for _ in {1..100}; do
  if next_port="$("${script_dir}/esp32_detect_port.sh" 2>/dev/null)"; then
    port="${next_port}"
    break
  fi
  sleep 0.05
done

"${project_dir}/.venv/bin/python" "${script_dir}/esp32_capture_serial.py" \
  --port "${port}" --seconds 8 --require-prefix 'CATAMAZE_BOOT ' | \
  tee "${artifact_dir}/product-serial.log"

boot_json="$(sed -n 's/^CATAMAZE_BOOT //p' "${artifact_dir}/product-serial.log" | head -n 1)"
[[ -n "${boot_json}" ]]
jq -e '
  .schema == "catamaze.boot.v2" and
  .flash_bytes == 16777216 and
  .psram_found == true and
  .psram_bytes == 8388608 and
  .map_i2c_count == 1 and .map_i2c_address == 60 and
  .hud_i2c_count == 1 and .hud_i2c_address == 60 and
  .button_count == 6 and .gpio4_configured == false and .gpio10_configured == false and
  .system_mode == "HOME" and .confirmed_map_size == 30 and .tick_budget == 1200 and
  .loop_stack_high_water_words > 4096 and .ready == true
' <<<"${boot_json}" >/dev/null

printf 'ESP32_PRODUCT_OK port=%s\n' "${port}"
