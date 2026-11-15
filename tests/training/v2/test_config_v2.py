# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:04 EST
# Last Modified by: Codex
# Verifies the immutable V2 production-candidate configuration.

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from training.v2.config import load_config


CONFIG = Path("configs/rl/v2/persona_v2.yaml")


def test_committed_v2_config_has_frozen_lineage_and_balanced_topology() -> None:
    config = load_config(CONFIG)
    assert config["lineage"]["v1_freeze_commit"] == "619ba18"
    assert config["distributed"]["global_num_envs"] == 256
    assert config["distributed"]["global_minibatch_sequences"] == 120
    assert config["quantization"]["evaluation_per_persona"] == 10_000


def test_v2_config_rejects_pending_lineage(tmp_path: Path) -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["lineage"]["v1_freeze_commit"] = "PENDING_V1_FREEZE_COMMIT"
    candidate = tmp_path / "invalid.yaml"
    candidate.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError, match="must be immutable"):
        load_config(candidate)


def test_v2_config_rejects_an_aggregate_only_quantization_gate(tmp_path: Path) -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["quantization"]["minimum_action_agreement_per_persona"] = 0.985
    candidate = tmp_path / "invalid.yaml"
    candidate.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError, match="cannot be relaxed"):
        load_config(candidate)
