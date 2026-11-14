#!/usr/bin/env bash
# Created at: 2026-11-14 04:44 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:44 EST
# Last Modified by: Codex
# Performs read-only ESP32-S3 chip and Flash identity checks before any upload.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
artifact_dir="${project_dir}/.artifacts/esp32"
port="$("${script_dir}/esp32_detect_port.sh")"
core_dir="$("${project_dir}/.venv/bin/pio" system info --json-output | jq -r '.core_dir.value')"
esptool_bin="${core_dir}/packages/tool-esptool/esptool"

[[ -x "${esptool_bin}" ]]
mkdir -p "${artifact_dir}"
{
  "${esptool_bin}" --port "${port}" chip-id
  "${esptool_bin}" --port "${port}" flash-id
} | tee "${artifact_dir}/preflight.log"

grep -q 'Chip type:.*ESP32-S3' "${artifact_dir}/preflight.log"
grep -q 'Embedded PSRAM 8MB' "${artifact_dir}/preflight.log"
grep -q 'Detected flash size: 16MB' "${artifact_dir}/preflight.log"
grep -q 'Flash type set in eFuse: quad' "${artifact_dir}/preflight.log"
printf 'ESP32_PREFLIGHT_OK port=%s\n' "${port}"
