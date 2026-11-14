#!/usr/bin/env bash
# Created at: 2026-11-14 02:44 EST
# Created by: Codex
# Last Modified at: 2026-11-14 02:48 EST
# Last Modified by: Codex
# Captures desktop and narrow Native simulator screenshots with system Chrome.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
chrome_bin="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
artifact_dir="${project_dir}/.artifacts/screenshots"
server_log="${artifact_dir}/server.log"

[[ -x "${chrome_bin}" ]]
mkdir -p "${artifact_dir}"
cd "${project_dir}"
"${project_dir}/.venv/bin/pio" run -e native >/dev/null
"${project_dir}/.pio/build/native/program" --serve --port 0 --paused \
  >"${server_log}" 2>&1 &
server_pid=$!
chrome_pid=""
cleanup() {
  if [[ -n "${chrome_pid}" ]]; then
    kill "${chrome_pid}" 2>/dev/null || true
    wait "${chrome_pid}" 2>/dev/null || true
  fi
  kill "${server_pid}" 2>/dev/null || true
  wait "${server_pid}" 2>/dev/null || true
}
trap cleanup EXIT

base_url=""
for _ in {1..100}; do
  base_url="$(sed -n 's/^CATAMAZE_URL=//p' "${server_log}" | tail -n 1)"
  [[ -n "${base_url}" ]] && break
  sleep 0.05
done
[[ -n "${base_url}" ]]

profile_dir="$(mktemp -d "${artifact_dir}/chrome-profile.XXXXXX")"
"${chrome_bin}" --headless=new --disable-gpu --hide-scrollbars \
  --remote-debugging-port=0 --user-data-dir="${profile_dir}" about:blank \
  >"${artifact_dir}/chrome.log" 2>&1 &
chrome_pid=$!

debug_port=""
for _ in {1..100}; do
  if [[ -f "${profile_dir}/DevToolsActivePort" ]]; then
    debug_port="$(head -n 1 "${profile_dir}/DevToolsActivePort")"
    break
  fi
  sleep 0.05
done
[[ -n "${debug_port}" ]]

node "${project_dir}/scripts/capture_chrome.mjs" "${debug_port}" \
  "${base_url}/" 1440 1050 "${artifact_dir}/desktop.png"
node "${project_dir}/scripts/capture_chrome.mjs" "${debug_port}" \
  "${base_url}/" 390 1800 "${artifact_dir}/narrow.png"

file "${artifact_dir}/desktop.png" "${artifact_dir}/narrow.png"
printf 'CATAMAZE_SCREENSHOTS_OK desktop=%s narrow=%s\n' \
  "${artifact_dir}/desktop.png" "${artifact_dir}/narrow.png"
