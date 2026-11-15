## header
Created at: 2026-11-15 06:30 EST
Created by: Codex
Last Modified at: 2026-11-15 06:30 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: provide the backend-free, mobile-compatible Cloudflare Pages showcase for the dual-screen CataMaze experience.
- 架构思路：用独立的浏览器本地状态机演示 Companion Idle、双 OLED、六键和可玩迷宫，同时明确隔离于权威 C++ Game Core、ESP-DL 与硬件证据。

## folder structure
|-README.md — Documents the static showcase boundary, assets, and release ownership.
|-_headers — Applies Cloudflare static security and cache headers.
|-app.css — Defines the responsive handheld, accessible controls, immediate feedback, and reduced-motion behavior.
|-app.js — Runs the browser-local showcase state machine, deterministic maze, two OLED renderers, input gestures, and optional sound.
|-index.html — Defines the semantic, install-free two-screen showcase document.

## To-Dos
- Replace the browser-local demonstration with the portable C++ core only if a future WebAssembly ADR and deterministic equivalence suite are approved.
