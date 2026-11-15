## header
Created at: 2026-11-14 18:52 EST
Created by: Codex
Last Modified at: 2026-11-14 20:40 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: enforce the isolated V2 model, migration, persona-head, recurrent-state, and serialization contracts.
- 架构思路：先证明 V2 在零训练步与 V1 完全等价，再允许任何 PPO实现或远程训练。

## folder structure
|-README.md — Defines V2 model test ownership.
|-test_ablation_v2.py — Verifies every causal comparison removes only its declared persona mechanism.
|-test_checkpoint_v2.py — Verifies a V2 checkpoint reproduces the exact next recurrent rollout.
|-test_consolidate_v2.py — Verifies cumulative phase lineage without changing final model tensors.
|-test_config_v2.py — Verifies the committed V2 lineage, topology, phase, quantization, and budget contract.
|-test_detailed_evaluator_v2.py — Verifies aggregate and raw episode evidence agree.
|-test_evaluator_v2.py — Verifies persona behavior gates and counterfactual JS divergence.
|-test_export_esp_v2.py — Verifies actor-only shapes, critic pruning, supported operators, and ONNX parity.
|-test_migrate_v2.py — Verifies V1 hash enforcement, lineage, and equivalent V2 warm-start output.
|-test_model_v2.py — Verifies shapes, V1 migration equivalence, head selection, gradients, reset, and serialization.
|-test_package_candidate_v2.py — Verifies failed gates cannot produce a handoff and passing bundles are checksummed.
|-test_ppo_v2.py — Verifies persona-local normalization, equal-weight updates, and finite per-persona metrics.
|-test_quantize_esp_v2.py — Verifies balanced disjoint recurrent samples with nonzero hidden state.
|-test_reward_v3.py — Verifies isolated timeout, combat, survival, exploration, potential, and ammo values.
|-test_rollout_v2.py — Verifies every V2 recurrent minibatch contains equal persona sequence counts.
|-test_schedule_v2.py — Verifies heads-only, recurrent, and full fine-tuning ownership.
|-test_smoke_v2.py — Verifies provisional opt-in and bounded end-to-end V2 smoke output.
|-test_style_loss_v2.py — Verifies tactical targets, legal masks, finite empty subsets, margins, and gradients.

## To-Dos
- Add persona-balanced rollout and PPO golden tests before Phase 4 exits.
