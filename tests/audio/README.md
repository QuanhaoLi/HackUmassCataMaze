## header
Created at: 2026-11-14 04:59 EST
Created by: Codex
Last Modified at: 2026-11-14 04:59 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: verify the optional Mac speaker companion without requiring an ESP32 or audio device.
- 架构思路：纯协议、序列号和 WAV 结构测试使用临时目录与 dry-run，不播放声音、不访问硬件。

## folder structure
|-README.md — Documents Mac audio companion test ownership.
|-test_mac_audio_companion.py — Verifies strict lines, hidden-field rejection, sequence wrap, and generated WAV assets.

## To-Dos
- Add measured end-to-end Serial-to-speaker latency evidence during physical M5 acceptance.
