# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 22:12 EST
# Last Modified by: Codex
# Validates the immutable V2 lineage, topology, phase, evaluation, and embedded budgets.

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from training import _native
from training.reward import REWARD_VERSION as V2_REWARD_VERSION
from training.v2 import MODEL_ARCH_VERSION, PERSONA_HEADS_MODEL_ARCH_VERSION
from training.v2.reward import REWARD_VERSION as V3_REWARD_VERSION


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise ValueError("V2 config root must be a mapping")
    versions = config.get("versions", {})
    reward_version = versions.get("reward")
    if reward_version == V2_REWARD_VERSION:
        training_config = "catamaze.training.persona.v2.1"
    elif reward_version == V3_REWARD_VERSION:
        training_config = "catamaze.training.persona.v2.reward3.1"
    else:
        raise ValueError("unsupported V2 reward version")
    model_arch_version = (
        MODEL_ARCH_VERSION
        if reward_version == V2_REWARD_VERSION
        else PERSONA_HEADS_MODEL_ARCH_VERSION
    )
    expected_versions = {
        "environment": _native.environment_version,
        "observation": _native.observation_schema_version,
        "action": "catamaze.action.v1",
        "reward": reward_version,
        "model_arch": model_arch_version,
        "training_config": training_config,
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
    if reward_version == V3_REWARD_VERSION:
        if lineage.get("reward_v3_source_phase") != "recurrent":
            raise ValueError("reward v3 must start from the recurrent checkpoint")
        if lineage.get("reward_v3_source_checkpoint_sha256") != (
            "d155f283f73754c9dbb9d7142f8221bde4a6de27dc8b8c1385f63137bf85c597"
        ):
            raise ValueError("reward v3 source checkpoint changed")
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
    expected_phases: dict[str, Any]
    if reward_version == V2_REWARD_VERSION:
        expected_phases = {
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
        }
    else:
        expected_phases = {
            "first_evaluation": 5_000_000,
            "full_target": 15_000_000,
            "curriculum": "C",
            "learning_rate": 0.00003,
            "controlled_heads_only_steps": 5_000_000,
        }
    if phases != expected_phases:
        raise ValueError("V2 phase boundaries changed")
    style_constraints = config.get("style_constraints")
    if reward_version == V3_REWARD_VERSION:
        if style_constraints != {
            "coefficient": 0.02,
            "reward_v3_heads_source_checkpoint_sha256": (
                "0b45c37551aa7bf533e59ec77212fbc6c15c14dab97dde9efcc8228285e75f85"
            ),
            "raw_scale_source_checkpoint_sha256": (
                "f9b6c54422a825388ddb3d164c07cf0dfbd45178963273866004e8b52fdc5567"
            ),
            "persona_neutral_source_checkpoint_sha256": (
                "d155f283f73754c9dbb9d7142f8221bde4a6de27dc8b8c1385f63137bf85c597"
            ),
            "js_margin_source_checkpoint_sha256": (
                "e6a521a10b54f44a9f3e7ad55dbbeaebabe0db564725050884a4c6f3b022c0ad"
            ),
            "recurrent_novelty_source_checkpoint_sha256": (
                "3faccbc0a29c00f51cabe14b18e47187a4d919b01de8a5a047d2cec51be58a4d"
            ),
            "transition_credit_source_checkpoint_sha256": (
                "7a972f9a97aecd7fa394004e09fbafeb65dce5e322c4c3deb9ab227dc4fe61fd"
            ),
            "source_checkpoint_sha256": (
                "6947c4bc4a5bade4c92ba5d389e5de1211409d6894fa95e7ee177fabfbc3fef1"
            ),
            "training_js_target": 0.05,
            "release_js_gate": 0.02,
            "first_evaluation": 5_000_000,
            "trainable_scope": "heads_neutral",
            "model_variant": "catamaze.model.persona-heads.v2.1",
        }:
            raise ValueError("V2 style constraint contract changed")
    elif style_constraints is not None:
        raise ValueError("reward-v2 architecture config cannot enable style constraints")
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
