# Created at: 2026-11-14 04:51 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:51 EST
# Last Modified by: Codex
# Verifies the standalone environment validator on explicit seeds.

from training.validate_env import validate_environment


def test_environment_validator_completes_explicit_seed_range() -> None:
    summary = validate_environment(episodes=5, seeds=range(1, 6), num_envs=3)
    assert summary["episodes"] == 5
    assert sum(summary["outcomes"].values()) == 5
    assert summary["agent_steps"] > 0
