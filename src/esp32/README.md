## header
Created at: 2026-11-14 04:44 EST
Created by: Codex
Last Modified at: 2026-11-14 07:22 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: compose the production ESP32-S3 firmware from shared Game Core, application, and framebuffer libraries.
- 架构思路：硬件适配器只负责时钟、按钮、双 I²C 屏幕和非阻塞 Serial 音频；所有游戏规则与像素布局继续复用跨平台库。

## folder structure
|-README.md — Documents production firmware ownership and hardware boundaries.
|-button_adapter.cpp — Retains the previously deployed seven-button adapter; it is not the accepted six-button Home/Setup revision.
|-button_adapter.hpp — Declares the bounded physical-input adapter.
|-display_adapter.cpp — Initializes and writes independent SSD1306-compatible framebuffers over two I²C controllers.
|-display_adapter.hpp — Declares the dual-display adapter and diagnostics.
|-hardware_config.hpp — Freezes verified pins, bus rate, address, and timing without assigning GPIO4.
|-main.cpp — Composes the shared game/application/render libraries with ESP32 adapters.
|-serial_audio_adapter.cpp — Emits best-effort canonical audio lines without blocking or replay.
|-serial_audio_adapter.hpp — Declares the USB Serial audio adapter and drop counter.

## To-Dos
- After explicit user approval, migrate the adapter to `SystemController`, six buttons, 800 ms CLEAR short/long suppression, and GPIO10 spare status.
- Do not build or upload the Home/Setup ESP32 revision before that approval; the current Native revision is the acceptance reference.
