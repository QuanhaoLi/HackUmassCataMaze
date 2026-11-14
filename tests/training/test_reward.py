# Created at: 2026-11-14 03:49 EST
# Created by: Codex
# Last Modified at: 2026-11-14 05:02 EST
# Last Modified by: Codex
# Verifies exact vectorized reward components from reviewed synthetic transitions.

from __future__ import annotations

from typing import Any

import numpy as np

from training import _native
from training.reward import RewardCalculator


def snapshot() -> dict[str, Any]:
    events = np.full((1, 192, 7), -1, dtype=np.int16)
    return {
        "alive": np.ones((1, 3), dtype=np.bool_),
        "positions": np.array([[[1, 1], [2, 2], [3, 3], [4, 4]]], dtype=np.int16),
        "status": np.array([_native.STATUS_RUNNING], dtype=np.uint8),
        "events": events,
        "event_count": np.zeros((1,), dtype=np.uint16),
        "distance_to_player": np.array([[10, 20, 30]], dtype=np.int16),
        "last_result": np.zeros((1, 4), dtype=np.uint8),
    }


def set_events(state: dict[str, Any], rows: list[list[int]]) -> None:
    state["event_count"][0] = len(rows)
    state["events"][0, : len(rows)] = np.asarray(rows, dtype=np.int16)


def event(event_type: int, actor: int, target: int, value: int = 0) -> list[int]:
    return [event_type, actor, target, 0, 0, 0, value]


def test_player_lethal_damage_and_kill_credit_split_between_contributors() -> None:
    previous = snapshot()
    current = snapshot()
    current["status"][0] = _native.STATUS_DEATH
    set_events(
        current,
        [
            event(_native.EVENT_DAMAGE_APPLIED, 0, 0, 1),
            event(_native.EVENT_DAMAGE_CREDIT, 1, 0, 1),
            event(_native.EVENT_DAMAGE_CREDIT, 2, 0, 1),
            event(_native.EVENT_ENTITY_DIED, 0, 0),
        ],
    )
    calculator = RewardCalculator(previous)

    result = calculator.calculate(previous, current)

    np.testing.assert_allclose(result.components["terminal"], [[20.0, 20.0, 20.0]])
    np.testing.assert_allclose(result.components["player_combat"], [[5.0, 3.0, 0.0]])
    np.testing.assert_allclose(result.total, [[25.0, 23.0, 20.0]])
    assert np.all(result.terminated)


def test_friendly_fire_damage_and_kill_penalty_preserve_target_death_cost() -> None:
    previous = snapshot()
    current = snapshot()
    current["alive"][0, 2] = False
    set_events(
        current,
        [
            event(_native.EVENT_DAMAGE_APPLIED, 3, 3, 1),
            event(_native.EVENT_DAMAGE_CREDIT, 1, 3, 1),
            event(_native.EVENT_DAMAGE_CREDIT, 2, 3, 1),
            event(_native.EVENT_ENTITY_DIED, 3, 3),
        ],
    )
    calculator = RewardCalculator(previous)

    result = calculator.calculate(previous, current)

    np.testing.assert_allclose(result.components["friendly_fire"], [[-2.0, -2.0, 0.0]])
    np.testing.assert_allclose(result.components["self_damage"], [[0.0, 0.0, -11.0]])
    assert result.terminated[0, 2]
    assert not result.terminated[0, 0]


def test_movement_exploration_potential_efficiency_and_block_costs() -> None:
    previous = snapshot()
    current = snapshot()
    current["positions"][0, 1] = [2, 3]
    current["positions"][0, 2] = [3, 4]
    current["last_result"][0, 1] = _native.RESULT_MOVED
    current["last_result"][0, 2] = _native.RESULT_BLOCKED_WALL
    current["distance_to_player"][0] = [9, 20, 30]
    calculator = RewardCalculator(previous)

    result = calculator.calculate(previous, current)

    np.testing.assert_allclose(result.components["exploration"], [[0.002, 0.0, 0.0]])
    expected_potential = 0.10 * (0.995 * -0.09 - -0.10)
    np.testing.assert_allclose(
        result.components["potential"], [[expected_potential, 0.00002, 0.0]], atol=1e-7
    )
    np.testing.assert_allclose(
        result.components["efficiency"], [[-0.002, -0.0205, -0.0015]]
    )
    summed = sum(result.components.values(), start=np.zeros_like(result.total))
    np.testing.assert_allclose(result.total, summed, atol=1e-7)


def test_explorer_positive_coverage_reward_is_capped_at_five() -> None:
    previous = snapshot()
    calculator = RewardCalculator(previous)
    exploration_total = 0.0
    for cell in range(400):
        if cell == 4 * 50 + 4:
            continue
        current = snapshot()
        current["positions"][0, 3] = [cell % 50, cell // 50]
        current["last_result"][0, 3] = _native.RESULT_MOVED
        result = calculator.calculate(previous, current)
        exploration_total += float(result.components["exploration"][0, 2])
        previous = current

    assert np.isclose(exploration_total, 5.0, atol=1e-6)


def test_dead_historical_shooter_receives_no_delayed_reward() -> None:
    previous = snapshot()
    current = snapshot()
    previous["alive"][0, 0] = False
    current["alive"][0, 0] = False
    set_events(
        current,
        [
            event(_native.EVENT_DAMAGE_APPLIED, 0, 0, 1),
            event(_native.EVENT_DAMAGE_CREDIT, 1, 0, 1),
        ],
    )
    result = RewardCalculator(previous).calculate(previous, current)
    assert result.total[0, 0] == 0.0
    assert result.components["player_combat"][0, 0] == 0.0
