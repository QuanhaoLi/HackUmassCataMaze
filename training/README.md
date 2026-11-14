## header
Created at: 2026-11-14 03:34 EST
Created by: Codex
Last Modified at: 2026-11-14 03:49 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: implement the deterministic Native environment bridge, versioned policy contract, reward system, recurrent PPO, evaluation, checkpointing, and release tooling.
- 架构思路：C++ Game Core remains the only physics source; this Python package batches it in memory, consumes encoded legal observations, and keeps learning concerns out of the game runtime.

## folder structure
|-README.md — Introduces and indexes the training package.
|-__init__.py — Exposes versioned training package metadata without importing optional GPU dependencies.
|-native_bindings.cpp — Binds batched in-memory C++ Game Engines and policy-contract tensors to Python.
|-reward.py — Converts structured events and state deltas into independently logged per-agent reward components.

## To-Dos
- Add reward, model, rollout, PPO, curriculum, evaluation, checkpoint, benchmark, smoke, and training entry points in milestone order.
