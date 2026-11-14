## header
Created at: 2026-11-14 02:34 EST
Created by: Codex
Last Modified at: 2026-11-14 07:02 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: verify authoritative framebuffer storage and both virtual OLED renderers.
- 架构思路：像素级单测验证 byte order 与确定性，HTTP 端点和浏览器交互由 black-box smoke and screenshot scripts 验证。

## folder structure
|-README.md — Documents the M2 renderer test suite.
|-test_main.cpp — Provides the isolated GoogleTest entry point.
|-test_renderer.cpp — Verifies 9×5 square tiles, page order, fog/walls, projectile omission, and icon HUD output.
|-test_system_renderer.cpp — Verifies deterministic dual-screen framebuffers for every system mode.

## To-Dos
- Promote any visually discovered regression into a focused pixel test.
