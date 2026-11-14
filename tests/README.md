## header
Created at: 2026-11-14 03:34 EST
Created by: Codex
Last Modified at: 2026-11-14 04:59 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: contain host-side Python tests and immutable fixtures for the RL stack.
- 架构思路：fast contract tests run locally; bounded integration and GPU tests use explicit markers and never hide remote or long-running work.

## folder structure
|-README.md — Introduces Python test ownership.
|-audio/ — Tests Mac Serial audio parsing, sequence handling, and generated sound assets.
|-training/ — Tests observations, masking, rewards, model, rollout, PPO, and checkpoints.
|-fixtures/ — Contains reviewed immutable test inputs and expected outputs.

## To-Dos
- Keep every test deterministic through explicit seeds.
