## header
Created at: 2026-11-14 03:34 EST
Created by: Codex
Last Modified at: 2026-11-14 03:49 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: verify the complete RL implementation from Native environment transitions through exported policies.
- 架构思路：tests are layered by contract and use golden trajectories for reward semantics, property checks for masks, and exact replay checks for recurrent state and checkpoints.

## folder structure
|-README.md — Introduces training tests.
|-test_native_env.py — Verifies Native batch tensor shapes, deterministic reset/step replay, and input validation.
|-test_reward.py — Verifies damage credit, kill splits, friendly fire, exploration, potential shaping, and component totals.

## To-Dos
- Add reward tests before implementing the reward calculator.
