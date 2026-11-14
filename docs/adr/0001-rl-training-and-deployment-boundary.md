<!--
Created at: 2026-11-14 03:29 EST
Created by: Codex
Last Modified at: 2026-11-14 03:29 EST
Last Modified by: Codex
-->

# ADR-0001: RL training and deployment boundary

## Status

Accepted for the RL implementation phase beginning 2026-11-14.

## Context

`docs/reward.md` specifies a PyTorch recurrent PPO model and previously described an online inference service. The product contract in `docs/gamerules.md`, `docs/structure.md`, and `docs/restrictions.md` instead defines a standalone ESP32-S3 game with no network or cloud inference requirement. The planned CNN, GroupNorm, SiLU, and GRU export has no approved embedded runtime, quantization contract, device memory measurement, or physical latency evidence.

The approved training host provides four NVIDIA V100 GPUs. Recurrent PPO uses a small model and CPU-bound environment sampling, so synchronous four-GPU data parallelism adds complexity before it proves a throughput benefit. Release acceptance already requires five independent training seeds.

## Decision

1. The first RL product loop targets deterministic Native training, evaluation, export, and optional Native gameplay inference.
2. ESP32 gameplay continues to use the deterministic heuristic policy unless a later ADR approves an embedded model format, quantization method, runtime, memory budget, latency budget, and physical-device validation plan.
3. No network service is required for RL inference. TorchScript or ONNX artifacts are Native artifacts only in this phase.
4. The heuristic policy remains the mandatory fallback when a model is absent, incompatible, times out, or returns invalid output.
5. Correctness is established on CPU and then one V100 before using all four GPUs.
6. The four V100s run isolated single-GPU training seeds concurrently. Synchronous DDP is deferred unless profiling demonstrates that it improves end-to-end agent transitions per second without changing PPO batch semantics or reproducibility.
7. Remote execution may not start until environment, observation, action-mask, reward, recurrent-state, checkpoint, and 100k-agent-step smoke gates pass locally or in a bounded CPU-only CI job.
8. Automation never performs a power transition or disables SSH, Tailscale, or host networking on the training server.

## Consequences

- Training work cannot silently add a cloud dependency to the handheld game.
- Four GPUs improve wall-clock time primarily by evaluating independent seeds, which directly supports the release gate.
- The initial RL implementation does not claim embedded deployability.
- A later embedded policy will require its own architecture decision and may use quantization, distillation, or a smaller architecture while preserving the legal observation and action contracts.
