## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 04:44 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: contain thin executable entry points selected by PlatformIO environments.
- 架构思路：entry points compose adapters and reusable libraries; no game rules live here.

## folder structure
|-README.md — Introduces executable entry points.
|-esp32/ — Contains the production ESP32-S3 firmware composition and hardware adapters.
|-esp32_diagnostic/ — Contains the bounded preflight firmware used before product upload.
|-native/ — Contains the macOS/Linux simulator executable.
|-tools/ — Contains bounded Native verification executables that are not product entry points.

## To-Dos
- Keep diagnostic and production firmware entry points separate so hardware evidence cannot be confused with gameplay acceptance.
