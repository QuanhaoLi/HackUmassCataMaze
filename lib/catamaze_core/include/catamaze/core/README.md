## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 06:40 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: contain public domain types and deterministic engine interfaces.
- 架构思路：按稳定概念拆分头文件，避免 platform symbols and hidden mutable globals.

## folder structure
|-README.md — Documents public Game Core headers.
|-action_queue.hpp — Declares the fixed-capacity player FIFO.
|-engine.hpp — Declares deterministic state, 9×5 player view, unchanged 5×5 AI observations, transitions, and hashing.
|-map.hpp — Declares fixed-size terrain storage and `dfs-grid-v1` generation.
|-policy_contract.hpp — Declares the versioned 13×5×5 observation encoder, 46-scalar schema, and legal-action mask.
|-random.hpp — Declares repository-owned PCG32 randomness.
|-types.hpp — Declares stable coordinates, actions, entities, bullets, events, and constants.
|-version.hpp — Exposes stable product, rules, and Game Core version identifiers.

## To-Dos
- Version every observation or action-mask contract change before retraining a policy.
