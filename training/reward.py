# Created at: 2026-11-14 03:51 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:38 EST
# Last Modified by: Codex
# Computes versioned per-agent reward components from structured Native transitions.

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import numpy.typing as npt

from training import _native


REWARD_VERSION = "catamaze.reward.v1"
GAMMA = np.float32(0.995)
EXPLORATION_CAP = np.float32(5.0)

PLAYER_DAMAGE = np.asarray([2.0, 1.0, 0.5], dtype=np.float32)
PLAYER_KILL = np.asarray([8.0, 5.0, 3.0], dtype=np.float32)
SELF_DAMAGE = np.asarray([-0.75, -1.5, -1.0], dtype=np.float32)
SELF_DEATH = np.asarray([-8.0, -15.0, -10.0], dtype=np.float32)
AMMO_COST = np.asarray([-0.01, -0.05, -0.03], dtype=np.float32)
NEW_CELL = np.asarray([0.002, 0.005, 0.015], dtype=np.float32)
REVISIT = np.asarray([-0.002, -0.002, -0.008], dtype=np.float32)
TICK_COST = np.asarray([-0.002, -0.0005, -0.0015], dtype=np.float32)
POTENTIAL_BETA = np.asarray([0.10, 0.02, 0.0], dtype=np.float32)

COMPONENT_NAMES = (
    "terminal",
    "player_combat",
    "self_damage",
    "friendly_fire",
    "ammo",
    "exploration",
    "potential",
    "efficiency",
)

Snapshot = Mapping[str, npt.NDArray[np.generic]]


@dataclass(frozen=True)
class RewardResult:
    total: npt.NDArray[np.float32]
    components: dict[str, npt.NDArray[np.float32]]
    terminated: npt.NDArray[np.bool_]
    truncated: npt.NDArray[np.bool_]


class RewardCalculator:
    """Maintains episode-local reward state for a fixed Native environment batch."""

    def __init__(self, initial: Snapshot) -> None:
        alive = np.asarray(initial["alive"], dtype=np.bool_)
        if alive.ndim != 2 or alive.shape[1] != 3:
            raise ValueError("initial alive must have shape [num_envs, 3]")
        self._num_envs = alive.shape[0]
        self._visited = np.zeros((self._num_envs, 3, 2500), dtype=np.bool_)
        self._exploration_positive = np.zeros((self._num_envs, 3), dtype=np.float32)
        self.reset(initial)

    def reset(
        self,
        initial: Snapshot,
        env_mask: npt.NDArray[np.bool_] | None = None,
    ) -> None:
        positions = np.asarray(initial["positions"], dtype=np.int16)
        if positions.shape != (self._num_envs, 4, 2):
            raise ValueError("initial positions must have shape [num_envs, 4, 2]")
        selected = (
            np.ones((self._num_envs,), dtype=np.bool_)
            if env_mask is None
            else np.asarray(env_mask, dtype=np.bool_)
        )
        if selected.shape != (self._num_envs,):
            raise ValueError("env_mask must have shape [num_envs]")
        for env in np.flatnonzero(selected):
            self._visited[env] = False
            self._exploration_positive[env] = 0.0
            for agent in range(3):
                x, y = positions[env, agent + 1]
                self._visited[env, agent, int(y) * 50 + int(x)] = True

    def state_dict(self) -> dict[str, npt.NDArray[np.generic]]:
        return {
            "visited": self._visited.copy(),
            "exploration_positive": self._exploration_positive.copy(),
        }

    def load_state_dict(self, state: Mapping[str, npt.NDArray[np.generic]]) -> None:
        visited = np.asarray(state["visited"], dtype=np.bool_)
        exploration = np.asarray(state["exploration_positive"], dtype=np.float32)
        if visited.shape != self._visited.shape or exploration.shape != self._exploration_positive.shape:
            raise ValueError("reward state shape does not match environment batch")
        self._visited[:] = visited
        self._exploration_positive[:] = exploration

    def calculate(self, previous: Snapshot, current: Snapshot) -> RewardResult:
        previous_alive = np.asarray(previous["alive"], dtype=np.bool_)
        current_alive = np.asarray(current["alive"], dtype=np.bool_)
        status = np.asarray(current["status"], dtype=np.uint8)
        if previous_alive.shape != (self._num_envs, 3):
            raise ValueError("previous alive batch does not match calculator")
        if current_alive.shape != previous_alive.shape or status.shape != (self._num_envs,):
            raise ValueError("current snapshot batch does not match calculator")

        active = previous_alive
        components = {
            name: np.zeros((self._num_envs, 3), dtype=np.float32)
            for name in COMPONENT_NAMES
        }
        self._terminal_rewards(status, current_alive, components["terminal"])
        self._event_rewards(previous, current, active, current_alive, components)
        self._movement_rewards(previous, current, active, components)
        self._potential_rewards(previous, current, active, current_alive, status, components)
        self._efficiency_rewards(current, active, status, components["efficiency"])

        total = np.zeros((self._num_envs, 3), dtype=np.float32)
        for values in components.values():
            total += values
        total[~active] = 0.0
        for values in components.values():
            values[~active] = 0.0
        if not np.all(np.isfinite(total)):
            raise FloatingPointError("reward produced NaN or Inf")
        if np.any(np.abs(total) > 100.0):
            raise RuntimeError("single-transition absolute reward exceeded 100")
        terminal_status = (status == _native.STATUS_DEATH) | (status == _native.STATUS_VICTORY)
        terminated = active & ((~current_alive) | terminal_status[:, None])
        truncated = active & (status[:, None] == _native.STATUS_TIMEOUT)
        return RewardResult(
            total=total,
            components=components,
            terminated=terminated,
            truncated=truncated,
        )

    def _terminal_rewards(
        self,
        status: npt.NDArray[np.uint8],
        current_alive: npt.NDArray[np.bool_],
        output: npt.NDArray[np.float32],
    ) -> None:
        terminal_values = np.zeros((self._num_envs,), dtype=np.float32)
        terminal_values[status == _native.STATUS_DEATH] = 20.0
        terminal_values[status == _native.STATUS_VICTORY] = -20.0
        terminal_values[status == _native.STATUS_TIMEOUT] = 10.0
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
                        components["self_damage"][env, target - 1] += SELF_DEATH[target - 1]

                eligible_ai_shooters = [
                    shooter
                    for shooter in credits
                    if 1 <= shooter <= 3 and current_alive[env, shooter - 1]
                ]
                for shooter in eligible_ai_shooters:
                    effective_damage = np.float32(damage * credits[shooter] / total_hits)
                    if target == 0:
                        components["player_combat"][env, shooter - 1] += (
                            PLAYER_DAMAGE[shooter - 1] * effective_damage
                        )
                    elif shooter != target:
                        components["friendly_fire"][env, shooter - 1] -= effective_damage

                if target in died and eligible_ai_shooters:
                    contributor_count = np.float32(len(eligible_ai_shooters))
                    for shooter in eligible_ai_shooters:
                        if target == 0:
                            components["player_combat"][env, shooter - 1] += (
                                PLAYER_KILL[shooter - 1] / contributor_count
                            )
                        elif shooter != target:
                            components["friendly_fire"][env, shooter - 1] -= (
                                np.float32(3.0) / contributor_count
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
                if not active[env, agent] or results[env, agent + 1] != _native.RESULT_MOVED:
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
        output += active * (results == _native.RESULT_INVALID_FALLBACK) * np.float32(-0.10)
