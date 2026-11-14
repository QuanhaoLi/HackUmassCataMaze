#!/usr/bin/env bash
# Created at: 2026-11-14 02:26 EST
# Created by: Codex
# Last Modified at: 2026-11-14 02:56 EST
# Last Modified by: Codex
# Builds and executes a bounded headless Native gameplay acceptance check.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
mode="${2:-${1:-headless}}"

if [[ "${1:-}" == "--mode" ]]; then
  mode="${2:-}"
fi
if [[ "${mode}" != "headless" && "${mode}" != "browser" ]]; then
  echo "native_smoke.sh supports --mode headless or --mode browser" >&2
  exit 2
fi

cd "${project_dir}"
"${project_dir}/.venv/bin/pio" run -e native >/dev/null

if [[ "${mode}" == "headless" ]]; then
  output="$("${project_dir}/.pio/build/native/program" --seed 0x134fd5a --auto 32)"
  printf '%s\n' "${output}"
  grep -q '^CATAMAZE_HEADLESS_OK tick=' <<<"${output}"
  exit 0
fi

artifact_dir="${project_dir}/.artifacts/native-smoke"
mkdir -p "${artifact_dir}"
server_log="${artifact_dir}/server.log"
"${project_dir}/.pio/build/native/program" --serve --port 0 --paused \
  >"${server_log}" 2>&1 &
server_pid=$!
cleanup() {
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

curl -fsS "${base_url}/health" | jq -e '.status == "ok"' >/dev/null
curl -fsS "${base_url}/api/v1/snapshot" | jq -e \
  '.schema == "catamaze.snapshot.v1" and (.map_frame_hex | length) == 2048 and (.hud_frame_hex | length) == 2048 and .tick == 0' \
  >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"action":"MOVE_RIGHT"}' "${base_url}/api/v1/action" | \
  jq -e '.accepted == true' >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"action":"SHOOT_LEFT"}' "${base_url}/api/v1/action" | \
  jq -e '.accepted == true' >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"action":"WAIT"}' "${base_url}/api/v1/action" | \
  jq -e '.accepted == true' >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"action":"CLEAR"}' "${base_url}/api/v1/action" | \
  jq -e '.accepted == true' >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"mode":"PAUSED"}' "${base_url}/api/v1/clock" | \
  jq -e '.accepted == true' >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"command":"STEP"}' "${base_url}/api/v1/clock" | \
  jq -e '.accepted == true' >/dev/null

tick_value="0"
for _ in {1..40}; do
  tick_value="$(curl -fsS "${base_url}/api/v1/snapshot" | jq -r '.tick')"
  [[ "${tick_value}" == "1" ]] && break
  sleep 0.05
done
[[ "${tick_value}" == "1" ]]

invalid_status="$(curl -sS -o "${artifact_dir}/invalid.json" -w '%{http_code}' \
  -X POST -H 'Content-Type: application/json' -d '{"action":"FLY"}' \
  "${base_url}/api/v1/action")"
[[ "${invalid_status}" == "400" ]]
curl -fsS "${base_url}/" | grep -q 'CataMaze'
trap - EXIT
kill -TERM "${server_pid}"
server_status=0
wait "${server_pid}" || server_status=$?
[[ "${server_status}" == "0" ]]
printf 'CATAMAZE_BROWSER_OK url=%s tick=%s\n' "${base_url}" "${tick_value}"
