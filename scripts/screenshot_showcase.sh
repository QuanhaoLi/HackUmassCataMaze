#!/usr/bin/env bash
# Created at: 2026-11-15 06:48 EST
# Created by: Codex
# Last Modified at: 2026-11-15 06:48 EST
# Last Modified by: Codex
# Serves and validates the backend-free showcase in desktop and mobile Chrome viewports.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
chrome_bin="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
artifact_dir="${project_dir}/.artifacts/showcase"
server_log="${artifact_dir}/server.log"

[[ -x "${chrome_bin}" ]]
mkdir -p "${artifact_dir}"
node --check "${project_dir}/showcase/app.js"
node --check "${project_dir}/scripts/capture_showcase.mjs"

python3 -u -m http.server 0 --bind 127.0.0.1 --directory "${project_dir}/showcase" \
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

server_port=""
for _ in {1..100}; do
  server_port="$(sed -n 's/.*port \([0-9][0-9]*\).*/\1/p' "${server_log}" | head -n 1)"
  [[ -n "${server_port}" ]] && break
  sleep 0.05
done
[[ -n "${server_port}" ]]
base_url="http://127.0.0.1:${server_port}"

curl --fail --silent --show-error "${base_url}/" | grep -q 'data-release="2026.11.15.1"'
curl --fail --silent --show-error "${base_url}/app.css" | grep -q 'prefers-reduced-motion'
curl --fail --silent --show-error "${base_url}/app.js" | grep -q '__CATAMAZE_SHOWCASE__'

profile_dir="$(mktemp -d "${artifact_dir}/chrome-profile.XXXXXX")"
"${chrome_bin}" --headless=new --disable-gpu --hide-scrollbars --mute-audio \
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

node "${project_dir}/scripts/capture_showcase.mjs" "${debug_port}" \
  "${base_url}/" 1440 1050 "${artifact_dir}/desktop-idle.png"
node "${project_dir}/scripts/capture_showcase.mjs" "${debug_port}" \
  "${base_url}/" 390 844 "${artifact_dir}/mobile-idle.png"

file "${artifact_dir}/desktop-idle.png" "${artifact_dir}/desktop-idle-playing.png" \
  "${artifact_dir}/mobile-idle.png" "${artifact_dir}/mobile-idle-playing.png"
printf 'CATAMAZE_SHOWCASE_OK url=%s desktop=%s mobile=%s\n' \
  "${base_url}" "${artifact_dir}/desktop-idle.png" "${artifact_dir}/mobile-idle.png"
