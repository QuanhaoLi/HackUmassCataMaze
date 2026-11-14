## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:19 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: contain public domain types and deterministic engine interfaces.
- 架构思路：按稳定概念拆分头文件，避免 platform symbols and hidden mutable globals.

## folder structure
|-README.md — Documents public Game Core headers.
|-action_queue.hpp — Declares the fixed-capacity player FIFO.
|-engine.hpp — Declares deterministic world state, tick transitions, observations, and state hashing.
|-map.hpp — Declares fixed-size terrain storage and `dfs-grid-v1` generation.
|-random.hpp — Declares repository-owned PCG32 randomness.
|-types.hpp — Declares stable coordinates, actions, entities, bullets, events, and constants.
|-version.hpp — Exposes stable product, rules, and Game Core version identifiers.

## To-Dos
- Keep public contracts stable while M1 implementation and tests mature.
