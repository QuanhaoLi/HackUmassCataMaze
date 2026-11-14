## header
Created at: 2026-11-14 02:19 EST
Created by: Codex
Last Modified at: 2026-11-14 07:18 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: prove the complete deterministic Game Core behavior required by M1.
- 架构思路：使用显式 seed 和小型场景构造器覆盖规则边界；失败必须暴露 tick 与状态 hash。

## folder structure
|-README.md — Documents the M1 Game Core test suite.
|-test_audio_event.cpp — Exhaustively verifies canonical event names, hearing range, and same-tick priority.
|-test_main.cpp — Provides the isolated GoogleTest entry point.
|-test_application.cpp — Verifies deterministic legal-observation heuristic coordination.
|-test_system_controller.cpp — Verifies launcher flow, presets, tick freeze, restart, confirmation, and queue preservation.
|-test_map.cpp — Verifies PCG32, every `dfs-grid-v2` preset, connectivity, exit, and spawn determinism.
|-test_policy_contract.cpp — Verifies every spatial/scalar feature index and legal-action mask rule.
|-test_queue.cpp — Verifies FIFO capacity, rejection, CLEAR, and fallback WAIT.
|-test_types.cpp — Exhaustively verifies stable direction, action, and status mappings.
|-test_engine.cpp — Verifies movement, conflicts, bullets, damage, ammo, victory, death, timeout, and replay hashes.

## To-Dos
- Add regression cases whenever a Game Core defect is found.
