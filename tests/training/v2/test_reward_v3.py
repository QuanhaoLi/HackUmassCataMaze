# Created at: 2026-11-14 20:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 20:04 EST
# Last Modified by: Codex
# Verifies every frozen V2-only persona reward-v3 change.

from __future__ import annotations

from typing import Any

import numpy as np

from training import _native
from training.v2.env import PersonaV3BatchEnv
from training.v2.reward import PersonaRewardCalculator, REWARD_VERSION


def snapshot() -> dict[str, Any]:
    return {
        "alive": np.ones((1, 3), dtype=np.bool_),
        "positions": np.array([[[1, 1], [2, 2], [3, 3], [4, 4]]], dtype=np.int16),
        "status": np.array([_native.STATUS_RUNNING], dtype=np.uint8),
        "events": np.full((1, 192, 7), -1, dtype=np.int16),
        "event_count": np.zeros(1, dtype=np.uint16),
        "distance_to_player": np.array([[10, 20, 30]], dtype=np.int16),
        "last_result": np.zeros((1, 4), dtype=np.uint8),
    }


def event(event_type: int, actor: int, target: int, value: int = 0) -> list[int]:
    return [event_type, actor, target, 0, 0, 0, value]


def set_events(state: dict[str, Any], rows: list[list[int]]) -> None:
    state["event_count"][0] = len(rows)
    state["events"][0, : len(rows)] = np.asarray(rows, dtype=np.int16)


def test_timeout_is_negative_for_every_surviving_persona() -> None:
    previous = snapshot()
    current = snapshot()
    current["status"][0] = _native.STATUS_TIMEOUT
    result = PersonaRewardCalculator(previous).calculate(previous, current)
    np.testing.assert_allclose(result.components["terminal"], [[-5.0, -5.0, -5.0]])


def test_combat_ammo_and_cautious_death_values_are_frozen() -> None:
    previous = snapshot()
    current = snapshot()
    current["alive"][0, 1] = False
    set_events(
        current,
        [
            event(_native.EVENT_SHOT, 1, -1),
            event(_native.EVENT_SHOT, 2, -1),
            event(_native.EVENT_SHOT, 3, -1),
            event(_native.EVENT_DAMAGE_APPLIED, 0, 0, 1),
            event(_native.EVENT_DAMAGE_CREDIT, 1, 0, 1),
            event(_native.EVENT_DAMAGE_APPLIED, 2, 2, 1),
            event(_native.EVENT_DAMAGE_CREDIT, 1, 2, 1),
            event(_native.EVENT_ENTITY_DIED, 2, 2),
        ],
    )
    result = PersonaRewardCalculator(previous).calculate(previous, current)
    np.testing.assert_allclose(result.components["ammo"], [[-0.05, -0.08, -0.06]])
    np.testing.assert_allclose(result.components["player_combat"], [[4.0, 0.0, 0.0]])
    np.testing.assert_allclose(result.components["self_damage"], [[0.0, -28.0, 0.0]])


def test_explorer_coverage_and_cautious_distance_shaping_are_distinct() -> None:
    previous = snapshot()
    current = snapshot()
    calculator = PersonaRewardCalculator(previous)
    for persona in range(3):
        current["positions"][0, persona + 1, 1] += 1
        current["last_result"][0, persona + 1] = _native.RESULT_MOVED
    current["distance_to_player"][0] = [9, 21, 30]
    result = calculator.calculate(previous, current)
    np.testing.assert_allclose(result.components["exploration"], [[0.001, 0.002, 0.050]])
    assert result.components["potential"][0, 0] > 0
    assert result.components["potential"][0, 1] > 0
    assert result.components["potential"][0, 2] == 0


def test_v3_environment_replaces_only_the_reward_calculator() -> None:
    environment = PersonaV3BatchEnv(2, 127, curriculum_stage="C")
    assert isinstance(environment._reward, PersonaRewardCalculator)
    assert REWARD_VERSION == "catamaze.reward.persona.v3"
    assert environment.observation["spatial"].shape == (2, 3, 13, 5, 5)
