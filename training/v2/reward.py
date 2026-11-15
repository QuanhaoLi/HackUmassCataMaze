# Created at: 2026-11-14 20:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 20:04 EST
# Last Modified by: Codex
# Implements V2-only persona reward v3 on frozen Native transition events.

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from training import _native
from training.reward import EXPLORATION_CAP, GAMMA, RewardCalculator, Snapshot


REWARD_VERSION = "catamaze.reward.persona.v3"
PLAYER_DAMAGE = np.asarray([4.0, 1.0, 0.5], dtype=np.float32)
PLAYER_KILL = np.asarray([10.0, 5.0, 3.0], dtype=np.float32)
SELF_DAMAGE = np.asarray([-0.75, -3.0, -1.0], dtype=np.float32)
SELF_DEATH = np.asarray([-8.0, -25.0, -10.0], dtype=np.float32)
AMMO_COST = np.asarray([-0.05, -0.08, -0.06], dtype=np.float32)
NEW_CELL = np.asarray([0.001, 0.002, 0.050], dtype=np.float32)
REVISIT = np.asarray([0.0, 0.0, 0.0], dtype=np.float32)
TICK_COST = np.asarray([-0.0020, -0.0005, -0.0020], dtype=np.float32)
POTENTIAL_BETA = np.asarray([0.15, -0.02, 0.0], dtype=np.float32)


class PersonaRewardCalculator(RewardCalculator):
    def _terminal_rewards(
        self,
        status: npt.NDArray[np.uint8],
        current_alive: npt.NDArray[np.bool_],
        output: npt.NDArray[np.float32],
    ) -> None:
        terminal_values = np.zeros((self._num_envs,), dtype=np.float32)
        terminal_values[status == _native.STATUS_DEATH] = 20.0
        terminal_values[status == _native.STATUS_VICTORY] = -20.0
        terminal_values[status == _native.STATUS_TIMEOUT] = -5.0
        output[:] = terminal_values[:, None] * current_alive

    def _event_rewards(
        self,
        previous: Snapshot,
        current: Snapshot,
        active: npt.NDArray[np.bool_],
        current_alive: npt.NDArray[np.bool_],
        components: dict[str, npt.NDArray[np.float32]],
    ) -> None:
        del previous
        events = np.asarray(current["events"], dtype=np.int16)
        counts = np.asarray(current["event_count"], dtype=np.uint16)
        for env in range(self._num_envs):
            damage_by_target: dict[int, int] = {}
            credits_by_target: dict[int, dict[int, int]] = {}
            died: set[int] = set()
            for row in events[env, : int(counts[env])]:
                event_type, actor, target, _x, _y, _direction, value = map(int, row)
                if event_type == _native.EVENT_SHOT and 1 <= actor <= 3:
                    if active[env, actor - 1]:
                        components["ammo"][env, actor - 1] += AMMO_COST[actor - 1]
                elif event_type == _native.EVENT_DAMAGE_APPLIED:
                    damage_by_target[target] = damage_by_target.get(target, 0) + value
                elif event_type == _native.EVENT_DAMAGE_CREDIT:
                    target_credits = credits_by_target.setdefault(target, {})
                    target_credits[actor] = target_credits.get(actor, 0) + value
                elif event_type == _native.EVENT_ENTITY_DIED:
                    died.add(target)
            for target, damage in damage_by_target.items():
                credits = credits_by_target.get(target, {})
                total_hits = sum(credits.values())
                if damage > 0 and total_hits <= 0:
                    raise RuntimeError("damage event had no shooter credit")
                if 1 <= target <= 3 and active[env, target - 1]:
                    components["self_damage"][env, target - 1] += (
                        SELF_DAMAGE[target - 1] * damage
                    )
                    if target in died:
                        components["self_damage"][env, target - 1] += SELF_DEATH[
                            target - 1
                        ]
                eligible = [
                    shooter
                    for shooter in credits
                    if 1 <= shooter <= 3 and current_alive[env, shooter - 1]
                ]
                for shooter in eligible:
                    effective = np.float32(damage * credits[shooter] / total_hits)
                    if target == 0:
                        components["player_combat"][env, shooter - 1] += (
                            PLAYER_DAMAGE[shooter - 1] * effective
                        )
                    elif shooter != target:
                        components["friendly_fire"][env, shooter - 1] -= effective
                if target in died and eligible:
                    count = np.float32(len(eligible))
                    for shooter in eligible:
                        if target == 0:
                            components["player_combat"][env, shooter - 1] += (
                                PLAYER_KILL[shooter - 1] / count
                            )
                        elif shooter != target:
                            components["friendly_fire"][env, shooter - 1] -= (
                                np.float32(3.0) / count
                            )

    def _movement_rewards(
        self,
        previous: Snapshot,
        current: Snapshot,
        active: npt.NDArray[np.bool_],
        components: dict[str, npt.NDArray[np.float32]],
    ) -> None:
        del previous
        positions = np.asarray(current["positions"], dtype=np.int16)
        results = np.asarray(current["last_result"], dtype=np.uint8)
        for env in range(self._num_envs):
            for agent in range(3):
                if not active[env, agent] or results[
                    env, agent + 1
                ] != _native.RESULT_MOVED:
                    continue
                x, y = positions[env, agent + 1]
                cell = int(y) * 50 + int(x)
                if self._visited[env, agent, cell]:
                    components["exploration"][env, agent] += REVISIT[agent]
                else:
                    remaining = max(
                        np.float32(0.0),
                        EXPLORATION_CAP - self._exploration_positive[env, agent],
                    )
                    awarded = min(NEW_CELL[agent], remaining)
                    components["exploration"][env, agent] += awarded
                    self._exploration_positive[env, agent] += awarded
                    self._visited[env, agent, cell] = True

    def _potential_rewards(
        self,
        previous: Snapshot,
        current: Snapshot,
        active: npt.NDArray[np.bool_],
        current_alive: npt.NDArray[np.bool_],
        status: npt.NDArray[np.uint8],
        components: dict[str, npt.NDArray[np.float32]],
    ) -> None:
        previous_distance = np.asarray(previous["distance_to_player"], dtype=np.int16)
        current_distance = np.asarray(current["distance_to_player"], dtype=np.int16)
        for env in range(self._num_envs):
            player_alive = status[env] != _native.STATUS_DEATH
            for agent in range(3):
                if (
                    not active[env, agent]
                    or not current_alive[env, agent]
                    or not player_alive
                    or POTENTIAL_BETA[agent] == 0.0
                    or previous_distance[env, agent] < 0
                    or current_distance[env, agent] < 0
                ):
                    continue
                old_phi = -np.clip(previous_distance[env, agent] / 100.0, 0.0, 1.0)
                new_phi = -np.clip(current_distance[env, agent] / 100.0, 0.0, 1.0)
                components["potential"][env, agent] = POTENTIAL_BETA[agent] * (
                    GAMMA * new_phi - old_phi
                )

    def _efficiency_rewards(
        self,
        current: Snapshot,
        active: npt.NDArray[np.bool_],
        status: npt.NDArray[np.uint8],
        output: npt.NDArray[np.float32],
    ) -> None:
        results = np.asarray(current["last_result"], dtype=np.uint8)[:, 1:]
        output[:] = active * (status[:, None] == _native.STATUS_RUNNING) * TICK_COST
        output += active * np.isin(
            results, [_native.RESULT_BLOCKED_WALL, _native.RESULT_BLOCKED_BOUNDS]
        ) * np.float32(-0.02)
        output += active * np.isin(
            results, [_native.RESULT_BLOCKED_ENTITY, _native.RESULT_BLOCKED_CONFLICT]
        ) * np.float32(-0.005)
        output += active * (results == _native.RESULT_INVALID_FALLBACK) * np.float32(
            -0.10
        )
