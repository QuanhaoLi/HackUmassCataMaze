## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:55 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: hold reproducible developer and acceptance commands that compose project tools.
- 架构思路：scripts stay thin, fail fast, resolve paths from the repository, and never hide test or upload behavior.

## folder structure
|-README.md — Documents acceptance-script ownership.
|-capture_chrome.mjs — Applies an exact CSS viewport through Chrome DevTools, rejects overflow, and saves a PNG.
|-native_smoke.sh — Builds and runs a bounded headless Native gameplay smoke check.
|-pio_coverage.py — Adds Clang's profile runtime to the final Native coverage link.
|-pio_native_deps.py — Fetches and SHA-256-verifies pinned cpp-httplib and nlohmann/json single headers for Native builds.
|-run_coverage.sh — Measures portable core/application coverage and enforces M3 thresholds.
|-run_randomized.sh — Runs and repeats the deterministic randomized invariant executable.
|-run_sanitizers.sh — Executes the full Native suite under ASan and UBSan.
|-screenshot_native.sh — Starts the loopback simulator and captures desktop and narrow Chrome screenshots.

## To-Dos
- Add ESP32 scripts only when their documented milestones begin.
