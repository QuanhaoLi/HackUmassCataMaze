## header
Created at: 2026-11-14 04:44 EST
Created by: Codex
Last Modified at: 2026-11-14 18:51 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: compose the production ESP32-S3 firmware from shared Game Core, application, and framebuffer libraries.
- 架构思路：硬件适配器只负责时钟、按钮、双 I²C 屏幕和非阻塞 Serial 音频；所有游戏规则与像素布局继续复用跨平台库。

## folder structure
|-README.md — Documents production firmware ownership and hardware boundaries.
|-button_adapter.cpp — Samples six active-low GPIO inputs and forwards timed intents into the portable companion shell.
|-button_adapter.hpp — Declares the bounded six-button physical-input adapter.
|-display_adapter.cpp — Initializes and writes independent SSD1306-compatible framebuffers over two I²C controllers.
|-display_adapter.hpp — Declares the dual-display adapter and diagnostics.
|-hardware_config.hpp — Freezes verified pins, bus rate, address, and timing without assigning GPIO4.
|-main.cpp — Composes Companion Idle/Home/Game coordination, exact dual-screen rendering, resident model inference, audio, and ESP32 adapters.
|-model/ — Owns the released `.espdl` artifact and its single machine-readable release manifest.
|-policy_adapter.cpp — Loads one resident ESP-DL model and performs masked recurrent inference for all three AI.
|-policy_adapter.hpp — Declares policy health, memory, latency, and fallback diagnostics.
|-policy_release.hpp — Generated release identity, tensor contract, compatibility, and acceptance constants.
|-serial_audio_adapter.cpp — Emits best-effort canonical audio lines without blocking or replay.
|-serial_audio_adapter.hpp — Declares the USB Serial audio adapter and drop counter.

## To-Dos
- Keep M5 open until physical press/release, FIRE-before-direction, CLEAR short/long, and complete-game checks pass.
- Do not upload the companion/model image while GPIO7 starts LOW or GPIO15/GPIO16 lack raw diagnostic transitions.
