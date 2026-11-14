## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:11 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: coordinate commands, clocks, heuristic policies, rendering, and adapter snapshots.
- 架构思路：应用层依赖 Game Core 并定义 ports；Native/ESP32 adapters implement ports without changing rules.

## folder structure
|-README.md — Defines the application library boundary.
|-include/ — Contains public application and port interfaces.
|-src/ — Contains platform-independent coordination implementations.

## To-Dos
- Implement after the initial Game Core types and transitions stabilize.
