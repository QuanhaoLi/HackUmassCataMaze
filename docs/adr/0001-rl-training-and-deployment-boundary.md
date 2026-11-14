<!--
Created at: 2026-11-14 03:29 EST
Created by: Codex
Last Modified at: 2026-11-14 06:49 EST
Last Modified by: Codex
-->

# ADR-0001: RL training and deployment boundary

## Status

Accepted for the RL implementation phase beginning 2026-11-14.

## Context

`docs/reward.md` specifies a PyTorch recurrent PPO model and previously described an online inference service. The product contract in `docs/gamerules.md`, `docs/structure.md`, and `docs/restrictions.md` instead defines a standalone ESP32-S3 game with no network or cloud inference requirement. The planned CNN, GroupNorm, SiLU, and GRU export has no approved embedded runtime, quantization contract, device memory measurement, or physical latency evidence.

The approved training host provides four NVIDIA V100 GPUs. The operator prioritizes the fastest path to one usable production model over multi-seed statistical replication and explicitly requires all four V100s to participate in that model's training.

## Decision

1. The first RL product loop targets deterministic Native training, evaluation, export, and optional Native gameplay inference.
2. ESP32 gameplay continues to use the deterministic heuristic policy unless a later ADR approves an embedded model format, quantization method, runtime, memory budget, latency budget, and physical-device validation plan.
3. No network service is required for RL inference. TorchScript or ONNX artifacts are Native artifacts only in this phase.
4. The heuristic policy remains the mandatory fallback when a model is absent, incompatible, times out, or returns invalid output.
5. Correctness is established on CPU and then one V100 before using all four GPUs.
6. The four V100s use DistributedDataParallel to train one shared model. Each rank owns an independent environment shard and recurrent state; gradients, advantage statistics, PPO denominators, KL, clipping, and evaluation metrics use explicit global reductions.
7. One-card and four-card benchmarks determine the global environment and minibatch scale. The accepted four-card configuration must improve end-to-end agent transitions per second; merely showing higher GPU utilization is insufficient.
8. Remote execution may not start until environment, observation, action-mask, reward, recurrent-state, checkpoint, and 100k-agent-step smoke gates pass locally or in a bounded CPU-only CI job.
9. Automation never performs a power transition or disables SSH, Tailscale, or host networking on the training server.

## Consequences

- Training work cannot silently add a cloud dependency to the handheld game.
- Four GPUs improve wall-clock time through one synchronized training job. Multi-seed replication is optional evidence, not a release blocker.
- The initial RL implementation does not claim embedded deployability.
- A later embedded policy will require its own architecture decision and may use quantization, distillation, or a smaller architecture while preserving the legal observation and action contracts.
