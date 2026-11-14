# Created at: 2026-11-14 04:36 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:38 EST
# Last Modified by: Codex
# Saves and restores complete atomic training state, including Native environments and RNGs.

from __future__ import annotations

import os
from pathlib import Path
import random
import tempfile
from typing import Any

import numpy as np
import torch

from training import _native
from training.collector import RolloutCollector
from training.env import CataMazeBatchEnv
from training.model import MODEL_ARCH_VERSION, RecurrentActorCritic
from training.reward import REWARD_VERSION


CHECKPOINT_FORMAT_VERSION = "catamaze.checkpoint.v1"


def save_checkpoint(
    path: str | Path,
    *,
    model: RecurrentActorCritic,
    optimizer: torch.optim.Optimizer,
    environment: CataMazeBatchEnv,
    collector: RolloutCollector,
    policy_generator: torch.Generator,
    training_state: dict[str, Any],
    resolved_config: dict[str, Any],
    scheduler: Any | None = None,
    return_normalizer: Any | None = None,
    best_metrics: dict[str, float] | None = None,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format": CHECKPOINT_FORMAT_VERSION,
        "contracts": {
            "environment": _native.environment_version,
            "observation": _native.observation_schema_version,
            "reward": REWARD_VERSION,
            "model_arch": MODEL_ARCH_VERSION,
        },
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict() if scheduler is not None else None,
        "return_normalizer": (
            return_normalizer.state_dict() if return_normalizer is not None else None
        ),
        "environment": environment.state_dict(),
        "collector": collector.state_dict(),
        "policy_generator": policy_generator.get_state(),
        "training_state": training_state,
        "resolved_config": resolved_config,
        "best_metrics": best_metrics or {},
        "rng": {
            "python": random.getstate(),
            "numpy_global": np.random.get_state(),
            "torch_cpu": torch.get_rng_state(),
            "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        },
        "training_state": training_state,
        "resolved_config": resolved_config,
        "best_metrics": best_metrics or {},
    }
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        torch.save(payload, temporary_path)
        with temporary_path.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def load_checkpoint(
    path: str | Path,
    *,
    model: RecurrentActorCritic,
    optimizer: torch.optim.Optimizer,
    environment: CataMazeBatchEnv,
    collector: RolloutCollector,
    policy_generator: torch.Generator,
    scheduler: Any | None = None,
    return_normalizer: Any | None = None,
) -> dict[str, Any]:
    payload = torch.load(Path(path), map_location="cpu", weights_only=False)
    if payload.get("format") != CHECKPOINT_FORMAT_VERSION:
        raise ValueError("unsupported checkpoint format")
    expected_contracts = {
        "environment": _native.environment_version,
        "observation": _native.observation_schema_version,
        "reward": REWARD_VERSION,
        "model_arch": MODEL_ARCH_VERSION,
    }
    if payload.get("contracts") != expected_contracts:
        raise ValueError("checkpoint contract versions are incompatible")
    model.load_state_dict(payload["model"])
    optimizer.load_state_dict(payload["optimizer"])
    model_device = next(model.parameters()).device
    for optimizer_state in optimizer.state.values():
        for name, value in optimizer_state.items():
            if isinstance(value, torch.Tensor):
                optimizer_state[name] = value.to(model_device)
    if scheduler is not None:
        if payload["scheduler"] is None:
            raise ValueError("checkpoint does not contain scheduler state")
        scheduler.load_state_dict(payload["scheduler"])
    if return_normalizer is not None:
        if payload["return_normalizer"] is None:
            raise ValueError("checkpoint does not contain return-normalizer state")
        return_normalizer.load_state_dict(payload["return_normalizer"])
    environment.load_state_dict(payload["environment"])
    collector.load_state_dict(payload["collector"])
    policy_generator.set_state(payload["policy_generator"])
    random.setstate(payload["rng"]["python"])
    np.random.set_state(payload["rng"]["numpy_global"])
    torch.set_rng_state(payload["rng"]["torch_cpu"])
    if payload["rng"]["torch_cuda"] is not None:
        if not torch.cuda.is_available():
            raise ValueError("checkpoint contains CUDA RNG state but CUDA is unavailable")
        torch.cuda.set_rng_state_all(payload["rng"]["torch_cuda"])
    return payload["training_state"]
