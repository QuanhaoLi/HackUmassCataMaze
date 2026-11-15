## header
Created at: 2026-11-14 18:52 EST
Created by: Codex
Last Modified at: 2026-11-14 19:41 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: implement the isolated V2 persona-conditioned recurrent policy without modifying V1 training modules.
- 架构思路：共享 V1 感知/记忆主干，增加零初始化人格调制和三套 actor/critic heads，并用显式迁移保证 step-0 与 V1 数值等价。

## folder structure
|-README.md — Defines the V2 training-code boundary.
|-__init__.py — Exposes the V2 architecture version without importing V1 product code.
|-ablation.py — Creates explicit no-modulation, shared-head, and no-persona V2 comparison checkpoints.
|-checkpoint.py — Saves and restores complete V2 training, environment, collector, and RNG state.
|-config.py — Validates immutable V1 lineage and every V2 production-candidate contract.
|-ddp_smoke.py — Qualifies one shared V2 model across four V100 ranks with global persona statistics.
|-detailed_evaluator.py — Emits aggregate metrics plus immutable per-episode V2 evidence.
|-evaluator.py — Computes paired persona-style gates and counterfactual action divergence.
|-evaluate_checkpoint.py — Runs fixed-seed opponent reports and persona gates for a V2 checkpoint.
|-export_esp.py — Exports the V2 actor-only three-head recurrent step and validates ONNX parity/operators.
|-migrate.py — Verifies an immutable V1 checkpoint and emits a numerically equivalent V2 warm-start.
|-model.py — Implements the shared recurrent backbone, persona modulation, three heads, and V1 migration.
|-package_candidate.py — Validates all model-side gates and emits the checksummed stop-before-firmware handoff.
|-ppo.py — Applies persona-local advantage normalization and equal-weight recurrent PPO losses.
|-quantize_esp.py — Collects disjoint balanced recurrent samples and reports per-persona ESP-DL agreement.
|-rollout.py — Produces recurrent minibatches with equal sequence counts for every persona.
|-schedule.py — Freezes and unfreezes the exact parameter groups for each warm-start phase.
|-smoke.py — Runs an isolated end-to-end V2 collector/PPO/checkpoint correctness smoke.

## To-Dos
- Add persona-balanced PPO only after migration equivalence and gradient tests pass.
- Keep ESP32 export and quantization outside this folder until the Native candidate passes evaluation gates.
