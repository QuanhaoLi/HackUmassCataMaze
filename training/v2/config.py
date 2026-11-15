# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:26 EST
# Last Modified by: Codex
# Validates the immutable V2 lineage, topology, phase, evaluation, and embedded budgets.

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from training import _native
from training.reward import REWARD_VERSION
from training.v2 import MODEL_ARCH_VERSION


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise ValueError("V2 config root must be a mapping")
    expected_versions = {
        "environment": _native.environment_version,
        "observation": _native.observation_schema_version,
        "action": "catamaze.action.v1",
        "reward": REWARD_VERSION,
        "model_arch": MODEL_ARCH_VERSION,
        "training_config": "catamaze.training.persona.v2.1",
        "export_contract": "catamaze.esp-step.persona.v2",
    }
    if config.get("versions") != expected_versions:
        raise ValueError("V2 versions do not match the frozen candidate contract")
    lineage = config.get("lineage", {})
    for name in (
        "v1_freeze_commit",
        "v1_checkpoint_sha256",
        "v1_evaluation_sha256",
        "v2_warmstart_sha256",
    ):
        value = lineage.get(name)
        if not isinstance(value, str) or not value or "PENDING" in value.upper():
            raise ValueError(f"lineage.{name} must be immutable")
    if int(lineage.get("v1_agent_steps", 0)) != 100_364_306:
        raise ValueError("V2 lineage must use the released 100,364,306-step checkpoint")
    model = config.get("model", {})
    expected_model = {
        "spatial_channels": 13,
        "scalar_features": 46,
        "persona_offset": 43,
        "persona_count": 3,
        "conv_channels": 64,
        "gru_hidden": 256,
        "action_count": 9,
        "maximum_parameters": 1_030_000,
    }
    if model != expected_model:
        raise ValueError("V2 model contract changed")
    distributed = config.get("distributed", {})
    if distributed.get("world_size") != 4:
        raise ValueError("V2 production training requires four ranks")
    if distributed.get("physical_gpu_indices") != [1, 2, 3, 4]:
        raise ValueError("V2 training must use physical V100 indices 1-4")
    if distributed.get("global_num_envs") != 256:
        raise ValueError("V2 global environment count must equal 256")
    if distributed.get("global_minibatch_sequences") != 120:
        raise ValueError("V2 global minibatch must equal 120 balanced sequences")
    if distributed.get("per_rank_minibatch_sequences") % 3:
        raise ValueError("V2 per-rank minibatch must be persona divisible")
    rollout = config.get("rollout", {})
    steps = rollout.get("environment_steps")
    length = rollout.get("sequence_length")
    if not isinstance(steps, int) or not isinstance(length, int) or steps % length:
        raise ValueError("V2 sequence length must divide rollout steps")
    phases = config.get("phases", {})
    if phases != {
        "heads_only_end": 5_000_000,
        "recurrent_end": 10_000_000,
        "full_candidate": 25_000_000,
        "optional_extension": 50_000_000,
        "curriculum": {
            "heads_only": "A",
            "recurrent": "B",
            "full_before_candidate": "C",
            "full_after_candidate": "D",
        },
        "learning_rates": {
            "heads_only": 0.0003,
            "recurrent": 0.0001,
            "full": 0.00003,
        },
    }:
        raise ValueError("V2 phase boundaries changed")
    quantization = config.get("quantization", {})
    if quantization.get("calibration_per_persona") < 512:
        raise ValueError("V2 calibration requires at least 512 samples per persona")
    if quantization.get("evaluation_per_persona") < 10_000:
        raise ValueError("V2 quantization requires 10,000 evaluations per persona")
    if quantization.get("minimum_action_agreement_per_persona") < 0.99:
        raise ValueError("V2 per-persona quantization gate cannot be relaxed")
    budgets = config.get("embedded_budgets", {})
    if budgets != {
        "maximum_espdl_bytes": 1_800_000,
        "maximum_internal_bytes": 190_000,
        "maximum_psram_bytes": 2_000_000,
        "maximum_three_agent_p95_us": 900_000,
    }:
        raise ValueError("V2 embedded budgets changed")
    expected_runtime = {
        "python": "3.12",
        "torch": "2.6.0",
        "numpy": "1.26.4",
        "cuda": "12.4",
        "pip_index": "https://pypi.tuna.tsinghua.edu.cn/simple",
        "environment_path": "/home/a/minimind-venv",
        "physical_gpu_indices": [1, 2, 3, 4],
        "expected_gpu_name": "Tesla V100-PCIE-16GB",
    }
    if config.get("runtime") != expected_runtime:
        raise ValueError("V2 runtime violates the V100/Tsinghua/reused-venv contract")
    return config
