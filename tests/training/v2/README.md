## header
Created at: 2026-11-14 18:52 EST
Created by: Codex
Last Modified at: 2026-11-14 18:52 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: enforce the isolated V2 model, migration, persona-head, recurrent-state, and serialization contracts.
- 架构思路：先证明 V2 在零训练步与 V1 完全等价，再允许任何 PPO实现或远程训练。

## folder structure
|-README.md — Defines V2 model test ownership.
|-test_checkpoint_v2.py — Verifies a V2 checkpoint reproduces the exact next recurrent rollout.
|-test_migrate_v2.py — Verifies V1 hash enforcement, lineage, and equivalent V2 warm-start output.
|-test_model_v2.py — Verifies shapes, V1 migration equivalence, head selection, gradients, reset, and serialization.
|-test_ppo_v2.py — Verifies persona-local normalization, equal-weight updates, and finite per-persona metrics.
|-test_rollout_v2.py — Verifies every V2 recurrent minibatch contains equal persona sequence counts.
|-test_schedule_v2.py — Verifies heads-only, recurrent, and full fine-tuning ownership.
|-test_smoke_v2.py — Verifies provisional opt-in and bounded end-to-end V2 smoke output.

## To-Dos
- Add persona-balanced rollout and PPO golden tests before Phase 4 exits.
