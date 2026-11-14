# Created at: 2026-11-14 04:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:38 EST
# Last Modified by: Codex
# Verifies coordinated Native transitions, opponents, and reward calculation.

from __future__ import annotations

import numpy as np
import pytest

from training.env import CataMazeBatchEnv


def first_legal_actions(mask: np.ndarray) -> np.ndarray:
    return np.argmax(mask, axis=-1).astype(np.uint8)


def test_environment_step_is_seeded_and_returns_independent_agent_rewards() -> None:
    first = CataMazeBatchEnv(num_envs=4, seed=1234)
    second = CataMazeBatchEnv(num_envs=4, seed=1234)
    actions = first_legal_actions(first.observation["action_mask"])

    first_step = first.step(actions)
    second_step = second.step(actions)

    assert first_step.reward.total.shape == (4, 3)
    assert first_step.reward.terminated.shape == (4, 3)
    assert first_step.reward.truncated.shape == (4, 3)
    assert set(first_step.reward.components) == {
        "terminal",
        "player_combat",
        "self_damage",
        "friendly_fire",
        "ammo",
        "exploration",
        "potential",
        "efficiency",
    }
    np.testing.assert_array_equal(
        first_step.observation["state_hash"], second_step.observation["state_hash"]
    )
    np.testing.assert_allclose(first_step.reward.total, second_step.reward.total)


def test_environment_rejects_masked_actions_for_living_agents() -> None:
    environment = CataMazeBatchEnv(num_envs=2, seed=55)
    actions = first_legal_actions(environment.observation["action_mask"])
    illegal = np.argwhere(~environment.observation["action_mask"])
    env, agent, action = map(int, illegal[0])
    actions[env, agent] = action

    with pytest.raises(ValueError, match="masked action"):
        environment.step(actions)
