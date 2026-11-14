#!/usr/bin/env bash
# Created at: 2026-11-14 04:44 EST
# Created by: Codex
# Last Modified at: 2026-11-14 05:43 EST
# Last Modified by: Codex
# Prefers the independent CH343 UART bridge, with native USB-Serial/JTAG as fallback.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
devices_json="$("${project_dir}/.venv/bin/pio" device list --json-output)"

if [[ -n "${CATAMAZE_ESP_SERIAL:-}" ]]; then
  filter='select(((.hwid | contains("VID:PID=1A86:55D3")) or (.hwid | contains("VID:PID=303A:1001"))) and (.hwid | contains($serial)))'
  ports="$(jq -r --arg serial "${CATAMAZE_ESP_SERIAL}" ".[] | ${filter} | .port" \
    <<<"${devices_json}")"
else
  ports="$(jq -r '.[] | select(.hwid | contains("VID:PID=1A86:55D3")) | .port' \
    <<<"${devices_json}")"
  if [[ -z "${ports}" ]]; then
    ports="$(jq -r '.[] | select(.hwid | contains("VID:PID=303A:1001")) | .port' \
      <<<"${devices_json}")"
  fi
fi

port_count="$(awk 'NF {count += 1} END {print count + 0}' <<<"${ports}")"
if [[ "${port_count}" -ne 1 ]]; then
  echo "expected exactly one CH343 UART or Espressif USB device; found ${port_count}" >&2
  jq -r '.[] | "\(.port) \(.description) \(.hwid)"' <<<"${devices_json}" >&2
  exit 1
fi

printf '%s\n' "${ports}"
