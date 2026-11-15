## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 18:51 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: hold reproducible developer and acceptance commands that compose project tools.
- 架构思路：scripts stay thin, fail fast, resolve paths from the repository, and never hide test or upload behavior.

## folder structure
|-README.md — Documents acceptance-script ownership.
|-capture_chrome.mjs — Applies an exact CSS viewport through Chrome DevTools, rejects overflow, and saves a PNG.
|-esp32_capture_serial.py — Captures bounded ESP32 Serial output without hard-coding a port.
|-esp32_detect_port.sh — Resolves exactly one Espressif native USB-Serial/JTAG device.
|-esp32_preflight.sh — Runs read-only chip and Flash identity checks before any upload.
|-esp32_upload_product.sh — Refuses product upload unless fresh diagnostic v2 evidence passes, then validates Home-mode product boot.
|-esp32_upload_diagnostic.sh — Uploads only bounded six-input diagnostic firmware and validates dual buses, memory, idle inputs, and spare GPIOs.
|-mac_audio_companion.py — Auto-discovers ESP32 Serial audio events, reconnects, validates, and plays through Mac speakers.
|-generate_policy_release.py — Validates one model release manifest/artifact and deterministically generates C++ constants.
|-native_smoke.sh — Builds and runs a bounded headless Native gameplay smoke check.
|-pio_coverage.py — Adds Clang's profile runtime to the final Native coverage link.
|-pio_native_deps.py — Fetches and SHA-256-verifies pinned cpp-httplib and nlohmann/json single headers for Native builds.
|-pio_policy_release.py — Refuses ESP32 product builds when the manifest, artifact, or generated header drifts.
|-run_coverage.sh — Measures portable core/application coverage and enforces M3 thresholds.
|-run_randomized.sh — Runs and repeats the deterministic randomized invariant executable.
|-run_sanitizers.sh — Executes the full Native suite under ASan and UBSan.
|-screenshot_native.sh — Starts the loopback simulator and captures desktop and narrow Chrome screenshots.

## To-Dos
- Add ESP32 scripts only when their documented milestones begin.
