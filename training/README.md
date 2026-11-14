## header
Created at: 2026-11-14 03:34 EST
Created by: Codex
Last Modified at: 2026-11-14 06:58 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: implement the deterministic Native environment bridge, versioned policy contract, reward system, recurrent PPO, evaluation, checkpointing, and release tooling.
- 架构思路：C++ Game Core remains the only physics source; this Python package batches it in memory, consumes encoded legal observations, and keeps learning concerns out of the game runtime.

## folder structure
|-README.md — Introduces and indexes the training package.
|-__init__.py — Exposes versioned training package metadata without importing optional GPU dependencies.
|-collector.py — Collects masked recurrent rollouts from live batched environments and resets terminal state safely.
|-benchmark_env.py — Measures batched CPU environment throughput without model-update noise.
|-checkpoint.py — Atomically saves and restores model, optimizer, environment, recurrent, curriculum, and RNG state.
|-config.py — Loads and validates immutable YAML run configurations.
|-curriculum.py — Enforces step-plus-evaluation promotion gates without lowering failed criteria.
|-ddp_smoke.py — Qualifies one shared model across four synchronized environment and PPO ranks.
|-native_bindings.cpp — Binds batched in-memory C++ Game Engines and policy-contract tensors to Python.
|-env.py — Owns batched episode lifecycle, partial resets, opponent actions, and reward state.
|-evaluator.py — Runs fixed-seed stochastic/deterministic evaluation and emits per-persona metrics.
|-model.py — Implements the CNN, scalar MLP, GRU actor-critic, initialization, and masked categorical policy.
|-opponents.py — Implements the deterministic curriculum player-policy pool.
|-rollout.py — Stores recurrent on-policy transitions and builds masked fixed-length sequence minibatches.
|-ppo.py — Implements GAE, clipped recurrent PPO updates, KL stopping, and optimizer metrics.
|-reward.py — Converts structured events and state deltas into independently logged per-agent reward components.
|-smoke.py — Runs the bounded end-to-end correctness qualification before long GPU work.
|-train_ppo.py — Runs resumable production training, schedules, evaluation gates, metrics, and checkpoint retention.
|-train_ddp.py — Runs one resumable production model across four synchronized V100 ranks.
|-validate_env.py — Runs bounded seeded environment invariants without a neural policy.
|-validate_reward.py — Executes reviewed YAML reward trajectories independently from pytest.
|-validate_system.py — Verifies the pinned V100 runtime, real CUDA compute, and CPU/GPU numerical parity.

## To-Dos
- Add export and release-report entry points in milestone order.
