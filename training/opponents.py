# Created at: 2026-11-14 04:01 EST
# Created by: Codex
# Last Modified at: 2026-11-14 05:02 EST
# Last Modified by: Codex
# Implements seeded legal-action player opponents for curriculum training.

from __future__ import annotations

from copy import deepcopy
from enum import IntEnum
from typing import Mapping

import numpy as np
import numpy.typing as npt


class OpponentStrategy(IntEnum):
    STATIONARY = 0
    RANDOM_VALID = 1
    WALL_FOLLOWER = 2
    SHORTEST_PATH_NOISY = 3
    COMBAT_PLANNER = 4
    FROZEN_POOL = 5


MOVE_ACTIONS = np.array([0, 3, 1, 2], dtype=np.uint8)  # N, E, S, W
WAIT = np.uint8(8)

Snapshot = Mapping[str, npt.NDArray[np.generic]]


class OpponentPool:
    """Samples curriculum strategies and produces only masked player actions."""

    def __init__(self, num_envs: int, seed: int) -> None:
        if num_envs <= 0:
            raise ValueError("num_envs must be positive")
        self._num_envs = num_envs
        self._rng = np.random.Generator(np.random.PCG64(seed))
        self._heading = self._rng.integers(0, 4, size=num_envs, dtype=np.uint8)

    def sample_strategies(self, stage: str) -> npt.NDArray[np.uint8]:
        distributions: dict[str, tuple[list[OpponentStrategy], list[float]]] = {
            "A": (
                [OpponentStrategy.STATIONARY, OpponentStrategy.RANDOM_VALID],
                [0.70, 0.30],
            ),
            "B": (
                [OpponentStrategy.RANDOM_VALID, OpponentStrategy.WALL_FOLLOWER],
                [0.40, 0.60],
            ),
            "C": (
                [
                    OpponentStrategy.WALL_FOLLOWER,
                    OpponentStrategy.SHORTEST_PATH_NOISY,
                    OpponentStrategy.COMBAT_PLANNER,
                ],
                [0.30, 0.50, 0.20],
            ),
            "D": (
                list(OpponentStrategy),
                [0.05, 0.10, 0.20, 0.25, 0.30, 0.10],
            ),
        }
        if stage not in distributions:
            raise ValueError(f"unknown curriculum stage: {stage}")
        strategies, probabilities = distributions[stage]
        return self._rng.choice(
            np.asarray(strategies, dtype=np.uint8),
            size=self._num_envs,
            p=probabilities,
        ).astype(np.uint8, copy=False)

    def state_dict(self) -> dict[str, object]:
        return {
            "rng": deepcopy(self._rng.bit_generator.state),
            "heading": self._heading.copy(),
        }

    def load_state_dict(self, state: Mapping[str, object]) -> None:
        heading = np.asarray(state["heading"], dtype=np.uint8)
        if heading.shape != (self._num_envs,):
            raise ValueError("opponent heading state does not match num_envs")
        self._rng.bit_generator.state = deepcopy(state["rng"])
        self._heading[:] = heading

    def reset(self, env_mask: npt.ArrayLike) -> None:
        selected = np.asarray(env_mask, dtype=np.bool_)
        if selected.shape != (self._num_envs,):
            raise ValueError("opponent reset mask must have shape [num_envs]")
        self._heading[selected] = self._rng.integers(
            0, 4, size=int(selected.sum()), dtype=np.uint8
        )

    def actions(
        self,
        snapshot: Snapshot,
        strategies: npt.NDArray[np.uint8],
    ) -> npt.NDArray[np.uint8]:
        strategy_values = np.asarray(strategies, dtype=np.uint8)
        masks = np.asarray(snapshot["player_action_mask"], dtype=np.bool_)
        if strategy_values.shape != (self._num_envs,):
            raise ValueError("strategies must have shape [num_envs]")
        if masks.shape != (self._num_envs, 9):
            raise ValueError("player_action_mask must have shape [num_envs, 9]")
        output = np.full((self._num_envs,), WAIT, dtype=np.uint8)
        for env in range(self._num_envs):
            strategy = OpponentStrategy(int(strategy_values[env]))
            if strategy == OpponentStrategy.STATIONARY:
                candidate = WAIT
            elif strategy == OpponentStrategy.RANDOM_VALID:
                candidate = self._random_valid(masks[env])
            elif strategy == OpponentStrategy.WALL_FOLLOWER:
                candidate = self._wall_follower(env, masks[env])
            elif strategy == OpponentStrategy.SHORTEST_PATH_NOISY:
                candidate = self._shortest_noisy(env, snapshot, masks[env])
            else:
                # FROZEN_POOL deliberately falls back to the verified combat planner
                # until a versioned frozen player model is registered.
                candidate = self._combat(env, snapshot, masks[env])
            output[env] = candidate if masks[env, candidate] else WAIT
        return output

    def _random_valid(self, mask: npt.NDArray[np.bool_]) -> np.uint8:
        legal = np.flatnonzero(mask)
        return np.uint8(self._rng.choice(legal))

    def _wall_follower(self, env: int, mask: npt.NDArray[np.bool_]) -> np.uint8:
        heading = int(self._heading[env])
        for turn in (1, 0, -1, 2):
            direction = (heading + turn) % 4
            action = MOVE_ACTIONS[direction]
            if mask[action]:
                self._heading[env] = direction
                return action
        return WAIT

    def _shortest_noisy(
        self,
        env: int,
        snapshot: Snapshot,
        mask: npt.NDArray[np.bool_],
    ) -> np.uint8:
        if self._rng.random() < 0.10:
            return self._random_valid(mask)
        action = np.uint8(snapshot["shortest_path_action"][env])
        return action if mask[action] else self._random_valid(mask)

    def _combat(
        self,
        env: int,
        snapshot: Snapshot,
        mask: npt.NDArray[np.bool_],
    ) -> np.uint8:
        spatial = np.asarray(snapshot["player_spatial"][env], dtype=np.uint8)
        visible_ai = np.any(spatial[6:9] != 0, axis=0)
        shot_candidates: list[tuple[int, int]] = []
        for y, x in np.argwhere(visible_ai):
            dx = int(x) - 2
            dy = int(y) - 2
            if dx == 0 and dy < 0:
                shot_candidates.append((abs(dy), 4))
            elif dx == 0 and dy > 0:
                shot_candidates.append((abs(dy), 5))
            elif dy == 0 and dx < 0:
                shot_candidates.append((abs(dx), 6))
            elif dy == 0 and dx > 0:
                shot_candidates.append((abs(dx), 7))
        for _distance, action in sorted(shot_candidates):
            if mask[action]:
                return np.uint8(action)

        bullets = np.any(spatial[9:13] != 0, axis=0)
        bullet_cells = np.argwhere(bullets)
        if bullet_cells.size:
            choices: list[tuple[int, np.uint8]] = []
            for direction, action in enumerate(MOVE_ACTIONS):
                if not mask[action]:
                    continue
                step = ((-1, 0), (0, 1), (1, 0), (0, -1))[direction]
                y = 2 + step[0]
                x = 2 + step[1]
                nearest = min(abs(int(by) - y) + abs(int(bx) - x) for by, bx in bullet_cells)
                choices.append((nearest, action))
            if choices:
                return max(choices, key=lambda item: item[0])[1]
        return self._shortest_noisy(env, snapshot, mask)
