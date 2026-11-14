## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:48 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: hold reproducible developer and acceptance commands that compose project tools.
- 架构思路：scripts stay thin, fail fast, resolve paths from the repository, and never hide test or upload behavior.

## folder structure
|-README.md — Documents acceptance-script ownership.
|-capture_chrome.mjs — Applies an exact CSS viewport through Chrome DevTools, rejects overflow, and saves a PNG.
|-native_smoke.sh — Builds and runs a bounded headless Native gameplay smoke check.
|-pio_native_deps.py — Fetches and SHA-256-verifies pinned cpp-httplib and nlohmann/json single headers for Native builds.
|-screenshot_native.sh — Starts the loopback simulator and captures desktop and narrow Chrome screenshots.

## To-Dos
- Add later hardening scripts only when their milestones begin.
