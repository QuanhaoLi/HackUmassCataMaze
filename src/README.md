## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:51 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: contain thin executable entry points selected by PlatformIO environments.
- 架构思路：entry points compose adapters and reusable libraries; no game rules live here.

## folder structure
|-README.md — Introduces executable entry points.
|-native/ — Contains the macOS/Linux simulator executable.
|-tools/ — Contains bounded Native verification executables that are not product entry points.

## To-Dos
- Add `esp32/` with its README only when M4 begins.
