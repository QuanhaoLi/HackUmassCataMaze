## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:11 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: implement the platform-independent application coordinator.
- 架构思路：单一 simulation owner 执行命令和 tick，adapters 只提交 bounded commands and consume snapshots.

## folder structure
|-README.md — Documents application implementation ownership.

## To-Dos
- Add deterministic heuristic AI and coordination after core transitions pass focused tests.
