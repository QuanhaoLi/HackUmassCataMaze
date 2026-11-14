## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:13 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: implement the deterministic, platform-independent CataMaze game domain.
- 架构思路：公开 C++17 头文件与私有实现分离；所有状态变化通过显式命令和 tick，保持 Native/ESP32 一致。

## folder structure
|-README.md — Defines the Game Core library boundary.
|-include/ — Contains public Game Core headers.
|-library.json — Declares PlatformIO library metadata and nonstandard include directory.
|-src/ — Contains private Game Core implementations.

## To-Dos
- Implement rules incrementally in the order defined by M1 in `../../plan.md`.
