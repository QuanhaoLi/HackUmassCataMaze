## header
Created at: 2026-11-14 18:52 EST
Created by: Codex
Last Modified at: 2026-11-14 18:52 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: implement the isolated V2 persona-conditioned recurrent policy without modifying V1 training modules.
- 架构思路：共享 V1 感知/记忆主干，增加零初始化人格调制和三套 actor/critic heads，并用显式迁移保证 step-0 与 V1 数值等价。

## folder structure
|-README.md — Defines the V2 training-code boundary.
|-__init__.py — Exposes the V2 architecture version without importing V1 product code.
|-checkpoint.py — Saves and restores complete V2 training, environment, collector, and RNG state.
|-model.py — Implements the shared recurrent backbone, persona modulation, three heads, and V1 migration.
|-ppo.py — Applies persona-local advantage normalization and equal-weight recurrent PPO losses.
|-rollout.py — Produces recurrent minibatches with equal sequence counts for every persona.

## To-Dos
- Add persona-balanced PPO only after migration equivalence and gradient tests pass.
- Keep ESP32 export and quantization outside this folder until the Native candidate passes evaluation gates.
