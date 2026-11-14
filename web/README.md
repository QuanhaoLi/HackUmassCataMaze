## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 07:16 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: provide the dependency-free browser UI for the Native simulator.
- 架构思路：HTML/CSS/JavaScript consume versioned APIs and paint authoritative framebuffer bits onto Canvas.

## folder structure
|-README.md — Documents browser asset ownership.
|-app.css — Styles the responsive handheld simulator and pixel-perfect OLED surfaces.
|-app.js — Resolves FIRE sampling and CLEAR short/long gestures, calls versioned APIs, and paints exact framebuffer bytes.
|-index.html — Defines the accessible two-screen simulator shell and controls.

## To-Dos
- Keep assets dependency-free, allow-listed, and compatible with headless screenshot QA.
