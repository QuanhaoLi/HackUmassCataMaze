## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:26 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: coordinate commands, clocks, heuristic policies, rendering, and adapter snapshots.
- 架构思路：应用层依赖 Game Core 并定义 ports；Native/ESP32 adapters implement ports without changing rules.

## folder structure
|-README.md — Defines the application library boundary.
|-include/ — Contains public application and port interfaces.
|-library.json — Declares PlatformIO metadata and the public include directory.
|-src/ — Contains platform-independent coordination implementations.

## To-Dos
- Keep policy decisions constrained to legal observations while Native gameplay matures.
