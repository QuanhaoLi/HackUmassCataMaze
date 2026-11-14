## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:11 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: contain reusable C++ libraries shared by Native and future ESP32 targets.
- 架构思路：按领域核心、应用协调和像素渲染分库，依赖只能向内，平台适配代码不得进入这里。

## folder structure
|-README.md — Introduces and indexes reusable project libraries.
|-catamaze_core/ — Owns deterministic game state, rules, map generation, AI contracts, and events.
|-catamaze_app/ — Owns application commands, clock coordination, snapshots, and adapter ports.
|-catamaze_render/ — Owns platform-independent 128×64 monochrome framebuffer rendering.

## To-Dos
- Keep the dependency direction `render/app → core`; never let core depend on adapters.
