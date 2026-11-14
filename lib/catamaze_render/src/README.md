## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 07:09 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: implement driver-free monochrome rendering.
- 架构思路：fixed bitmap font and pixel primitives generate identical buffers on every target.

## folder structure
|-README.md — Documents renderer implementation ownership.
|-framebuffer.cpp — Implements bounds-safe pixel, primitive, and fixed-font drawing.
|-renderer.cpp — Implements the full-width 9×5 square-tile player Map and icon-based HP/AMMO HUD.
|-system_renderer.cpp — Implements retro dual-screen launcher and menu framebuffers.

## To-Dos
- Keep layout changes covered by deterministic framebuffer tests and screenshots.
