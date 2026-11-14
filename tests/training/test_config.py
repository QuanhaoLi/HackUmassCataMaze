# Created at: 2026-11-14 04:38 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:38 EST
# Last Modified by: Codex
# Verifies the production configuration matches compiled contract versions and shapes.

from training.config import load_config


def test_production_config_matches_frozen_contracts() -> None:
    config = load_config("configs/rl/ppo_16gb.yaml")
    assert config["environment"]["num_envs"] == 64
    assert config["rollout"]["environment_steps"] == 128
    assert config["rollout"]["sequence_length"] == 64
    assert config["model"]["gru_hidden"] == 256
    assert config["total_agent_steps"] == 100_000_000
