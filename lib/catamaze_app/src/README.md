## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 04:37 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: implement the platform-independent application coordinator.
- 架构思路：单一 simulation owner 执行命令和 tick，adapters 只提交 bounded commands and consume snapshots.

## folder structure
|-README.md — Documents application implementation ownership.
|-application.cpp — Implements deterministic persona policies and one-owner tick coordination.
|-audio_event.cpp — Selects one highest-priority audio event without exposing hidden state.

## To-Dos
- Preserve legal-observation policy boundaries when future model policies are added.
