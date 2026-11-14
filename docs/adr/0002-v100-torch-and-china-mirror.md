<!--
Created at: 2026-11-14 05:26 EST
Created by: Codex
Last Modified at: 2026-11-14 05:26 EST
Last Modified by: Codex
-->

# ADR-0002: V100 PyTorch build and China mirror

## Status

Accepted for the approved four-V100 training host on 2026-11-14.

## Context

The host is in China and must use the Tsinghua PyPI mirror. Its training GPUs are four Tesla V100 16GB devices with compute capability 7.0. Tsinghua PyPI's current `torch==2.14.1` Linux wheel depends on CUDA 13, which does not support Volta. The separate upstream `+cu126` wheel is not an approved download path for this host. The host already has physically observed working PyTorch 2.6.0 + CUDA 12.4 environments on the same V100 hardware.

## Decision

1. The V100 production baseline is PyTorch `2.6.0` with its PyPI CUDA `12.4` dependencies.
2. Remote pip operations use only `https://pypi.tuna.tsinghua.edu.cn/simple`.
3. Qualification verifies `torch.version.cuda == "12.4"`, CUDA availability, compute capability `(7, 0)`, and a real tensor forward/backward pass.
4. GPU index `0` is the host's GTX 750 and is excluded. Training uses physical GPUs `1,2,3,4`; isolated processes see their selected V100 as logical `cuda:0`.
5. Changing PyTorch, CUDA user-space libraries, or the mirror requires a new training-config version and repeat of CPU/GPU parity, smoke, and two-hour stability qualification.

## Consequences

- The training configuration version advances to `catamaze.training.ppo16gb.v2`.
- Existing v1 CPU smoke artifacts remain evidence for environment/PPO correctness but are not V100 release checkpoints.
- No system driver, CUDA toolkit, power state, SSH service, Tailscale service, or host network setting is changed.
