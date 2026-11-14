## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 03:11 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: render authoritative 128×64 monochrome Map and HUD framebuffers.
- 架构思路：像素输出独立于 OLED、Canvas 和 HTTP；Map 使用空白道路、实心墙、单斜线迷雾且永不绘制子弹，HUD 使用五颗心和三枚弹药图标，Native 与 ESP32 consume identical page-order bytes.

## folder structure
|-README.md — Defines the renderer library boundary.
|-include/ — Contains public framebuffer and renderer headers.
|-library.json — Declares PlatformIO metadata and the public include directory.
|-src/ — Contains font and pixel-rendering implementations.

## To-Dos
- Keep physical OLED and browser Canvas consumers byte-identical.
