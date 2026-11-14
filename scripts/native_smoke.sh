#!/usr/bin/env bash
# Created at: 2026-11-14 02:26 EST
# Created by: Codex
# Last Modified at: 2026-11-14 11:38 EST
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
  '.schema == "catamaze.snapshot.v3" and .mode == "IDLE" and .system_mode == "HOME" and .companion_frame == "NEUTRAL" and .system.confirmed_map_size == 30 and (.left_frame_hex | length) == 2048 and (.right_frame_hex | length) == 2048 and .tick == 0' \
  >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"input":"FIRE"}' "${base_url}/api/v1/input" | \
  jq -e '.accepted == true' >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"input":"FIRE"}' "${base_url}/api/v1/input" | \
  jq -e '.accepted == true' >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"input":"RIGHT"}' "${base_url}/api/v1/input" | \
  jq -e '.accepted == true' >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"input":"SHOOT_LEFT"}' "${base_url}/api/v1/input" | \
  jq -e '.accepted == true' >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"input":"CLEAR_SHORT"}' "${base_url}/api/v1/input" | \
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

curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"input":"SHOOT_RIGHT"}' "${base_url}/api/v1/input" | \
  jq -e '.accepted == true' >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"command":"STEP"}' "${base_url}/api/v1/clock" | \
  jq -e '.accepted == true' >/dev/null
sound_tick="1"
for _ in {1..40}; do
  sound_snapshot="$(curl -fsS "${base_url}/api/v1/snapshot")"
  sound_tick="$(jq -r '.tick' <<<"${sound_snapshot}")"
  [[ "${sound_tick}" == "2" ]] && break
  sleep 0.05
done
[[ "${sound_tick}" == "2" ]]
jq -e '.last_events | any(.type == "PLAYER_SHOT")' <<<"${sound_snapshot}" >/dev/null

pre_prompt_hash="$(jq -r '.state_hash' <<<"${sound_snapshot}")"
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"command":"ELAPSE_INACTIVITY"}' "${base_url}/api/v1/clock" | \
  jq -e '.accepted == true' >/dev/null
prompt_snapshot=""
for _ in {1..40}; do
  prompt_snapshot="$(curl -fsS "${base_url}/api/v1/snapshot")"
  [[ "$(jq -r '.mode' <<<"${prompt_snapshot}")" == "INACTIVITY_PROMPT" ]] && break
  sleep 0.05
done
jq -e --arg hash "${pre_prompt_hash}" \
  '.mode == "INACTIVITY_PROMPT" and .system_mode == "PAUSED" and .tick == 2 and .state_hash == $hash and .system.prompt_focus == 0' \
  <<<"${prompt_snapshot}" >/dev/null
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"input":"CLEAR_SHORT"}' "${base_url}/api/v1/input" | \
  jq -e '.accepted == true' >/dev/null

curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"seed":"0x0000000000000042"}' "${base_url}/api/v1/reset" | \
  jq -e '.accepted == true' >/dev/null
for input in FIRE DOWN FIRE LEFT LEFT DOWN FIRE; do
  curl -fsS -X POST -H 'Content-Type: application/json' \
    -d "{\"input\":\"${input}\"}" "${base_url}/api/v1/input" | \
    jq -e '.accepted == true' >/dev/null
done
configured_snapshot=""
for _ in {1..40}; do
  configured_snapshot="$(curl -fsS "${base_url}/api/v1/snapshot")"
  [[ "$(jq -r '.system_mode' <<<"${configured_snapshot}")" == "PLAYING" ]] && break
  sleep 0.05
done
jq -e '.mode == "ACTIVE" and .system_mode == "PLAYING" and .system.confirmed_map_size == 12 and .system.tick_budget == 480' \
  <<<"${configured_snapshot}" >/dev/null

invalid_status="$(curl -sS -o "${artifact_dir}/invalid.json" -w '%{http_code}' \
  -X POST -H 'Content-Type: application/json' -d '{"input":"WAIT"}' \
  "${base_url}/api/v1/input")"
[[ "${invalid_status}" == "400" ]]
extra_status="$(curl -sS -o "${artifact_dir}/extra.json" -w '%{http_code}' \
  -X POST -H 'Content-Type: application/json' -d '{"input":"UP","extra":true}' \
  "${base_url}/api/v1/input")"
[[ "${extra_status}" == "400" ]]
curl -fsS "${base_url}/" | grep -q 'CataMaze'
trap - EXIT
kill -TERM "${server_pid}"
server_status=0
wait "${server_pid}" || server_status=$?
[[ "${server_status}" == "0" ]]
printf 'CATAMAZE_BROWSER_OK url=%s tick=%s sound=PLAYER_SHOT\n' \
  "${base_url}" "${sound_tick}"
