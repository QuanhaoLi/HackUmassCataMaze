## header
Created at: 2026-11-14 03:28 EST
Created by: Codex
Last Modified at: 2026-11-14 18:52 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: record durable architecture decisions that change or clarify CataMaze's frozen product, training, and deployment contracts.
- 架构思路：每个 ADR 只处理一个重要决策，记录背景、选择、后果和后续门槛；规范文件仍是最终执行合同，ADR 解释为何这样规定。

## folder structure
|-README.md — Introduces and indexes architecture decision records.
|-0001-rl-training-and-deployment-boundary.md — Selects Native-first RL training/inference, preserves the standalone ESP32 fallback, and defines four-GPU run isolation.
|-0002-v100-torch-and-china-mirror.md — Pins the Volta-compatible PyTorch/CUDA build and Tsinghua-only remote package source.
|-0003-six-button-system-navigation.md — Removes the physical WAIT button while preserving Wait Action and separates CLEAR short/long intent.
|-0004-zero-revisit-shaping.md — Removes revisit penalties that made dead-end backtracking worse than waiting.
|-0005-distance-banded-training-spawns.md — Uses near-to-far training spawns while keeping full-map evaluation uniform.
|-0006-calibrate-stage-a-promotion.md — Calibrates combat mastery before widening the search curriculum.
|-0006-calibrate-stage-a-promotion.md — Calibrates the A→B gate so the search stage is not blocked by a search-dependent metric.
|-0007-esp32-local-policy-inference.md — Defines ESP-DL export, quantization, sequential inference, fallback, and physical acceptance.
|-0008-companion-shell-outside-game-core.md — Keeps expressive idle animation and inactivity timing outside deterministic game/model state.
|-0009-atomic-resident-policy.md — Makes three-AI inference atomic and selects one released model with automatic latched heuristic fallback only.
|-0010-isolate-v2-persona-policy-candidate.md — Isolates V2 model preparation from V1 deployment and freezes the multi-head persona architecture and handoff boundary.

## To-Dos
- Add and index an ADR before implementing any future change to a frozen environment, reward, model, deployment, or hardware contract.
