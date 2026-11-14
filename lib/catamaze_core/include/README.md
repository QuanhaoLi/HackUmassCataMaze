## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:11 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: expose stable public headers for the Game Core library.
- 架构思路：使用 namespaced include 路径，避免项目库之间的头文件命名冲突。

## folder structure
|-README.md — Documents the public include root.
|-catamaze/ — Provides the project namespace include hierarchy.

## To-Dos
- Keep implementation-only declarations out of the public include tree.
