## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 03:36 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: contain private implementations for deterministic Game Core headers.
- 架构思路：实现只依赖标准 C++17 与本库公开头，禁止 Arduino、HTTP、clock and filesystem dependencies.

## folder structure
|-README.md — Documents private Game Core implementation ownership.
|-engine.cpp — Implements tick resolution, visibility, sound observations, terminal conditions, and hashing.
|-map.cpp — Implements fixed terrain operations, maze generation, and breadth-first distances.
|-policy_contract.cpp — Implements allocation-free observation encoding and legal-action masking shared by training and inference.
|-random.cpp — Implements PCG32 with unbiased bounded sampling.
|-types.cpp — Implements stable action, direction, and status helpers.

## To-Dos
- Preserve allocation-free steady-state ticks and encodes while focused tests expand.
