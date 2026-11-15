## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 18:58 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: implement the platform-independent application coordinator.
- 架构思路：单一 simulation owner 执行命令和 tick，adapters 只提交 bounded commands and consume snapshots.

## folder structure
|-README.md — Documents application implementation ownership.
|-application.cpp — Implements deterministic persona policies and one-owner tick coordination.
|-audio_event.cpp — Selects one highest-priority audio event without exposing hidden state.
|-product_shell.cpp — Implements explicit-time companion animation, consumed Wake, and guarded inactivity transitions.
|-resident_policy.cpp — Implements stable Policy Health mode/failure names shared by product diagnostics.
|-six_button_input.cpp — Implements debounce, FIRE sampling, no-repeat input, and CLEAR short/long suppression.
|-system_controller.cpp — Implements portable launcher, preset, pause, result, and queue-preserving transitions.

## To-Dos
- Preserve legal-observation policy boundaries when future model policies are added.
