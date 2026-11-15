## header
Created at: 2026-11-14 04:44 EST
Created by: Codex
Last Modified at: 2026-11-15 01:59 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: provide a bounded, non-game diagnostic firmware for first-write hardware verification.
- 架构思路：报告 chip/Flash/PSRAM、扫描两条 I²C 总线、独立初始化两块面板、写入有界可视测试图案并采样按钮；不实现游戏、不驱动 GPIO4/GPIO10、不虚构人工观察结果。

## folder structure
|-README.md — Documents diagnostic firmware scope and acceptance boundaries.
|-main.cpp — Reports Flash/PSRAM, two I²C scans and line levels, independent panel initialization/pattern writes, six idle inputs, and untouched GPIO4/GPIO10 status.

## To-Dos
- Do not promote the product image until both buses, panel initializations, pattern writes, six released inputs, and both spare-GPIO claims pass; visual pattern appearance still requires human confirmation.
