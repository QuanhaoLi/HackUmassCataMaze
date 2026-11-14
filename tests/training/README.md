## header
Created at: 2026-11-14 03:34 EST
Created by: Codex
Last Modified at: 2026-11-14 04:38 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: verify the complete RL implementation from Native environment transitions through exported policies.
- 架构思路：tests are layered by contract and use golden trajectories for reward semantics, property checks for masks, and exact replay checks for recurrent state and checkpoints.

## folder structure
|-README.md — Introduces training tests.
|-test_native_env.py — Verifies Native batch tensor shapes, deterministic reset/step replay, and input validation.
|-test_env.py — Verifies batched episode coordination, policy legality checks, rewards, and deterministic replay.
|-test_collector.py — Verifies real recurrent rollout collection, terminal resets, and a subsequent PPO update.
|-test_checkpoint.py — Verifies save/resume reproduces the exact next recurrent rollout.
|-test_model.py — Verifies network shapes, recurrent resets, masking, initialization scale, gradients, and serialization.
|-test_opponents.py — Verifies curriculum opponent actions remain legal and reproducible.
|-test_ppo.py — Verifies a masked recurrent PPO update changes parameters and emits finite metrics.
|-test_reward.py — Verifies damage credit, kill splits, friendly fire, exploration, potential shaping, and component totals.
|-test_rollout.py — Verifies terminated/truncated GAE semantics and recurrent sequence slicing.

## To-Dos
- Add evaluator, export, and long-run qualification tests before their implementations.
