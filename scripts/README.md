## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:26 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: hold reproducible developer and acceptance commands that compose project tools.
- 架构思路：scripts stay thin, fail fast, resolve paths from the repository, and never hide test or upload behavior.

## folder structure
|-README.md — Documents acceptance-script ownership.
|-native_smoke.sh — Builds and runs a bounded headless Native gameplay smoke check.
|-pio_native_deps.py — Fetches and SHA-256-verifies the pinned cpp-httplib single header for Native builds.

## To-Dos
- Add the screenshot script during M2.
