# Created at: 2026-11-14 04:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:38 EST
# Last Modified by: Codex
# Coordinates batched Native episodes, player opponents, reward state, and partial resets.

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from training import _native
from training.opponents import OpponentPool
from training.reward import RewardCalculator, RewardResult


Snapshot = dict[str, npt.NDArray[np.generic]]


@dataclass(frozen=True)
class EnvironmentStep:
    observation: Snapshot
    reward: RewardResult
    player_actions: npt.NDArray[np.uint8]
    opponent_strategies: npt.NDArray[np.uint8]


class CataMazeBatchEnv:
    """Owns the complete seeded lifecycle of a fixed-size environment batch."""

    def __init__(
        self,
        num_envs: int,
        seed: int,
        *,
        curriculum_stage: str = "A",
        randomize_spawns: bool = True,
    ) -> None:
        if num_envs <= 0:
            raise ValueError("num_envs must be positive")
        self.num_envs = num_envs
        self.curriculum_stage = curriculum_stage
        self._seed_rng = np.random.Generator(np.random.PCG64(seed))
        initial_seeds = self._next_seeds(num_envs)
        self._native = _native.NativeBatch(initial_seeds, randomize_spawns=randomize_spawns)
        self._observation: Snapshot = self._native.snapshot()
        self._reward = RewardCalculator(self._observation)
        opponent_seed = int(self._seed_rng.integers(0, 2**63, dtype=np.uint64))
        self._opponents = OpponentPool(num_envs, opponent_seed)
        self._strategies = self._opponents.sample_strategies(curriculum_stage)

    @property
    def observation(self) -> Snapshot:
        return self._observation

    def step(self, ai_actions: npt.ArrayLike) -> EnvironmentStep:
        actions = np.asarray(ai_actions, dtype=np.uint8)
        if actions.shape != (self.num_envs, 3):
            raise ValueError("ai_actions must have shape [num_envs, 3]")
        alive = np.asarray(self._observation["alive"], dtype=np.bool_)
        masks = np.asarray(self._observation["action_mask"], dtype=np.bool_)
        env_indices, agent_indices = np.nonzero(alive)
        if np.any(~masks[env_indices, agent_indices, actions[env_indices, agent_indices]]):
            raise ValueError("living agent selected a masked action")
        actions = actions.copy()
        actions[~alive] = 8
        player_actions = self._opponents.actions(self._observation, self._strategies)
        previous = self._observation
        current: Snapshot = self._native.step(player_actions, actions)
        reward = self._reward.calculate(previous, current)
        self._observation = current
        return EnvironmentStep(
            observation=current,
            reward=reward,
            player_actions=player_actions,
            opponent_strategies=self._strategies.copy(),
        )

    def reset_finished(self) -> npt.NDArray[np.bool_]:
        finished = np.asarray(self._observation["status"]) != _native.STATUS_RUNNING
        indices = np.flatnonzero(finished).astype(np.int64)
        if indices.size == 0:
            return finished
        seeds = self._next_seeds(indices.size)
        self._observation = self._native.reset_at(indices, seeds)
        self._reward.reset(self._observation, finished)
        sampled = self._opponents.sample_strategies(self.curriculum_stage)
        self._strategies[finished] = sampled[finished]
        return finished

    def state_dict(self) -> dict[str, object]:
        return {
            "native": self._native.save_state(),
            "seed_rng": deepcopy(self._seed_rng.bit_generator.state),
            "reward": self._reward.state_dict(),
            "opponents": self._opponents.state_dict(),
            "strategies": self._strategies.copy(),
            "curriculum_stage": self.curriculum_stage,
        }

    def load_state_dict(self, state: dict[str, object]) -> None:
        if state["curriculum_stage"] != self.curriculum_stage:
            raise ValueError("checkpoint curriculum stage does not match environment")
        self._native.load_state(state["native"])
        self._observation = self._native.snapshot()
        self._seed_rng.bit_generator.state = deepcopy(state["seed_rng"])
        self._reward.load_state_dict(state["reward"])
        self._opponents.load_state_dict(state["opponents"])
        strategies = np.asarray(state["strategies"], dtype=np.uint8)
        if strategies.shape != (self.num_envs,):
            raise ValueError("checkpoint strategies do not match num_envs")
        self._strategies[:] = strategies

    def _next_seeds(self, count: int) -> npt.NDArray[np.uint64]:
        return self._seed_rng.integers(
            0,
            np.iinfo(np.uint64).max,
            size=count,
            dtype=np.uint64,
        )
