# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:04 EST
# Last Modified by: Codex
# Verifies immutable V1 lineage and exact V2 warm-start migration.

from __future__ import annotations

from pathlib import Path

import pytest
import torch

from training.model import MODEL_ARCH_VERSION as V1_MODEL_ARCH_VERSION
from training.model import RecurrentActorCritic
from training.v2 import MODEL_ARCH_VERSION
from training.v2.migrate import file_sha256, migrate_checkpoint


def write_v1_checkpoint(path: Path) -> None:
    torch.save(
        {
            "format": "catamaze.ddp-training.v1",
            "model": RecurrentActorCritic().state_dict(),
            "world_size": 4,
            "training_state": {"agent_steps": 100_364_306},
            "config": {
                "versions": {
                    "environment": "catamaze.environment.v1",
                    "observation": "catamaze.observation.v1",
                    "reward": "catamaze.reward.v2",
                    "model_arch": V1_MODEL_ARCH_VERSION,
                }
            },
        },
        path,
    )


def test_migration_records_lineage_and_equivalent_model(tmp_path: Path) -> None:
    source = tmp_path / "v1.pt"
    output = tmp_path / "v2.pt"
    write_v1_checkpoint(source)
    report = migrate_checkpoint(
        source,
        output,
        expected_sha256=file_sha256(source),
        source_product_commit="freeze-test-commit",
    )
    payload = torch.load(output, map_location="cpu", weights_only=False)
    assert payload["model_arch"] == MODEL_ARCH_VERSION
    assert payload["lineage"]["source_product_commit"] == "freeze-test-commit"
    assert payload["lineage"]["source_agent_steps"] == 100_364_306
    assert payload["lineage"]["provisional"] is False
    assert max(payload["migration"].values()) == 0
    assert report["parameter_count"] < 1_030_000


def test_migration_rejects_a_checkpoint_hash_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "v1.pt"
    write_v1_checkpoint(source)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        migrate_checkpoint(
            source,
            tmp_path / "v2.pt",
            expected_sha256="0" * 64,
            source_product_commit="freeze-test-commit",
        )
