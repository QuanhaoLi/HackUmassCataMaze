## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 07:09 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: contain public framebuffer and screen-renderer contracts.
- 架构思路：固定 1,024-byte SSD1306 page-order buffers are the only visible output truth.

## folder structure
|-README.md — Documents public renderer headers.
|-framebuffer.hpp — Declares the fixed 128×64 one-bit SSD1306 page-order buffer and pixel primitives.
|-renderer.hpp — Declares the player Map and fixed-field HUD renderers.
|-system_renderer.hpp — Declares dual-screen Home, Setup, Pause, confirmation, System, About, and Result rendering.

## To-Dos
- Preserve the 1,024-byte output contract when layouts evolve.
