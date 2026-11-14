#!/usr/bin/env bash
# Created at: 2026-11-14 04:44 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:44 EST
# Last Modified by: Codex
# Resolves exactly one Espressif native USB-Serial/JTAG device without hard-coded paths.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
devices_json="$("${project_dir}/.venv/bin/pio" device list --json-output)"

if [[ -n "${CATAMAZE_ESP_SERIAL:-}" ]]; then
  filter='select((.hwid | contains("VID:PID=303A:1001")) and (.hwid | contains($serial)))'
  ports="$(jq -r --arg serial "${CATAMAZE_ESP_SERIAL}" ".[] | ${filter} | .port" \
    <<<"${devices_json}")"
else
  ports="$(jq -r '.[] | select(.hwid | contains("VID:PID=303A:1001")) | .port' \
    <<<"${devices_json}")"
fi

port_count="$(awk 'NF {count += 1} END {print count + 0}' <<<"${ports}")"
if [[ "${port_count}" -ne 1 ]]; then
  echo "expected exactly one Espressif USB-Serial/JTAG device; found ${port_count}" >&2
  jq -r '.[] | "\(.port) \(.description) \(.hwid)"' <<<"${devices_json}" >&2
  exit 1
fi

printf '%s\n' "${ports}"
