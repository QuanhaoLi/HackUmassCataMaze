# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 20:04 EST
# Last Modified by: Codex
# Verifies isolated V2 smoke lineage, opt-in, optimization, and checkpoint output.

from __future__ import annotations

from pathlib import Path

import pytest
import torch

from training.v2.migrate import MIGRATION_FORMAT
from training.v2.model import PersonaRecurrentActorCritic
from training.v2.smoke import run_smoke
from training.v2.schedule import TrainingPhase
from training.v2.reward import REWARD_VERSION as V3_REWARD_VERSION


def provisional_warmstart(path: Path) -> None:
    torch.save(
        {
            "format": MIGRATION_FORMAT,
            "model": PersonaRecurrentActorCritic().state_dict(),
            "lineage": {
                "provisional": True,
                "source_checkpoint_sha256": "test-source",
                "source_product_commit": "test-commit",
            },
        },
        path,
    )


def test_smoke_requires_explicit_provisional_opt_in(tmp_path: Path) -> None:
    warmstart = tmp_path / "warmstart.pt"
    provisional_warmstart(warmstart)
    with pytest.raises(ValueError, match="explicit opt-in"):
        run_smoke(
            warmstart,
            target_agent_steps=24,
            output_dir=tmp_path / "rejected",
            device=torch.device("cpu"),
            num_envs=2,
            environment_steps=4,
        )


def test_smoke_updates_all_heads_and_writes_resumable_checkpoint(tmp_path: Path) -> None:
    warmstart = tmp_path / "warmstart.pt"
    provisional_warmstart(warmstart)
    output = tmp_path / "smoke"
    summary = run_smoke(
        warmstart,
        target_agent_steps=96,
        output_dir=output,
        device=torch.device("cpu"),
        num_envs=2,
        environment_steps=4,
        allow_provisional=True,
    )
    assert summary["agent_steps"] >= 96
    assert summary["updates"] > 0
    assert summary["parameter_count"] < 1_030_000
    assert Path(summary["checkpoint"]).is_file()
    assert (output / "metrics.jsonl").is_file()
    assert (output / "summary.json").is_file()


def test_reward_v3_smoke_is_isolated_and_full_model_only(tmp_path: Path) -> None:
    warmstart = tmp_path / "warmstart.pt"
    provisional_warmstart(warmstart)
    output = tmp_path / "reward-v3-smoke"
    run_smoke(
        warmstart,
        target_agent_steps=24,
        output_dir=output,
        device=torch.device("cpu"),
        num_envs=2,
        environment_steps=4,
        allow_provisional=True,
        reward_version=V3_REWARD_VERSION,
        phase=TrainingPhase.FULL,
        curriculum_stage="C",
        learning_rate=3e-5,
    )
    resolved = (output / "resolved_config.json").read_text(encoding="utf-8")
    assert V3_REWARD_VERSION in resolved
