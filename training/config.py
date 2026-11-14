# Created at: 2026-11-14 04:26 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:26 EST
# Last Modified by: Codex
# Loads immutable YAML training configuration and validates frozen contracts.

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from training import _native
from training.model import MODEL_ARCH_VERSION
from training.reward import REWARD_VERSION


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as stream:
        loaded = yaml.safe_load(stream)
    if not isinstance(loaded, dict):
        raise ValueError("training config root must be a mapping")
    _validate_versions(loaded)
    _validate_shapes(loaded)
    return loaded


def _validate_versions(config: dict[str, Any]) -> None:
    versions = config.get("versions")
    if not isinstance(versions, dict):
        raise ValueError("config versions must be a mapping")
    expected = {
        "environment": _native.environment_version,
        "observation": _native.observation_schema_version,
        "reward": REWARD_VERSION,
        "model_arch": MODEL_ARCH_VERSION,
    }
    for name, value in expected.items():
        if versions.get(name) != value:
            raise ValueError(
                f"{name} version mismatch: expected {value}, got {versions.get(name)}"
            )
    if not isinstance(versions.get("training_config"), str):
        raise ValueError("training_config version must be present")


def _validate_shapes(config: dict[str, Any]) -> None:
    model = config.get("model")
    environment = config.get("environment")
    rollout = config.get("rollout")
    if not all(isinstance(section, dict) for section in (model, environment, rollout)):
        raise ValueError("model, environment, and rollout sections are required")
    expected_model = {
        "spatial_channels": 13,
        "scalar_features": 46,
        "gru_hidden": 256,
        "action_count": 9,
    }
    for name, value in expected_model.items():
        if model.get(name) != value:
            raise ValueError(f"model.{name} must equal {value}")
    if environment.get("agents_per_env") != 3:
        raise ValueError("environment.agents_per_env must equal 3")
    steps = rollout.get("environment_steps")
    sequence_length = rollout.get("sequence_length")
    if not isinstance(steps, int) or not isinstance(sequence_length, int):
        raise ValueError("rollout lengths must be integers")
    if steps <= 0 or sequence_length <= 0 or steps % sequence_length != 0:
        raise ValueError("sequence_length must evenly divide environment_steps")
    runtime = config.get("runtime")
    expected_runtime = {
        "python": "3.12",
        "torch": "2.6.0",
        "cuda": "12.4",
        "pip_index": "https://pypi.tuna.tsinghua.edu.cn/simple",
        "physical_gpu_indices": [1, 2, 3, 4],
        "expected_gpu_name": "Tesla V100-PCIE-16GB",
    }
    if runtime != expected_runtime:
        raise ValueError("runtime section does not match the frozen V100/Tsinghua contract")
