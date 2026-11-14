## header
Created at: 2026-11-14 04:44 EST
Created by: Codex
Last Modified at: 2026-11-14 05:03 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: provide a bounded, non-game diagnostic firmware for first-write hardware verification.
- 架构思路：只报告 chip/Flash/PSRAM、扫描两条 I²C 总线并采样按钮；不实现游戏、不驱动 GPIO4、不虚构人工按键结果。

## folder structure
|-README.md — Documents diagnostic firmware scope and acceptance boundaries.
|-main.cpp — Reports Flash/PSRAM, two I²C scans and line levels, released GPIO4, and idle button states.

## To-Dos
- Re-run after displays are connected; do not promote the product image until both buses pass.
