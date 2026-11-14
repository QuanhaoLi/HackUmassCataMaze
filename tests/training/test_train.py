# Created at: 2026-11-14 04:48 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:49 EST
# Last Modified by: Codex
# Verifies the production runner executes a bounded update and persists its state.

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import torch

from training.config import load_config
from training.train_ppo import train


def test_bounded_production_runner_writes_metrics_and_checkpoint(tmp_path: Path) -> None:
    config = deepcopy(load_config("configs/rl/ppo_16gb.yaml"))
    config["total_agent_steps"] = 1
    config["environment"]["num_envs"] = 2
    config["rollout"]["environment_steps"] = 4
    config["rollout"]["sequence_length"] = 2
    config["minibatch"]["sequences"] = 2
    config["minibatch"]["update_epochs"] = 1
    config["evaluation"]["every_agent_steps"] = 1_000_000
    config["checkpoint"]["every_agent_steps"] = 1

    train(config, run_dir=tmp_path, device=torch.device("cpu"), resume=None)

    assert (tmp_path / "metrics.jsonl").is_file()
    latest = tmp_path / "checkpoints" / "latest.pt"
    assert latest.is_file()
    assert not (tmp_path / "checkpoints" / "failure.pt").exists()
    first = torch.load(latest, map_location="cpu", weights_only=False)
    config["total_agent_steps"] = int(first["training_state"]["agent_steps"]) + 1

    train(config, run_dir=tmp_path, device=torch.device("cpu"), resume=latest)

    resumed = torch.load(latest, map_location="cpu", weights_only=False)
    assert resumed["training_state"]["update"] > first["training_state"]["update"]
