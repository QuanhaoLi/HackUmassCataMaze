# Created at: 2026-11-14 03:57 EST
# Created by: Codex
# Last Modified at: 2026-11-14 03:57 EST
# Last Modified by: Codex
# Verifies legal and reproducible curriculum player opponents.

from __future__ import annotations

import numpy as np

from training._native import NativeBatch
from training.opponents import OpponentPool, OpponentStrategy


def test_every_builtin_opponent_returns_legal_actions() -> None:
    seeds = np.arange(1, 65, dtype=np.uint64)
    snapshot = NativeBatch(seeds, randomize_spawns=True).snapshot()
    pool = OpponentPool(num_envs=64, seed=1234)

    for strategy in OpponentStrategy:
        actions = pool.actions(snapshot, np.full((64,), strategy, dtype=np.uint8))
        assert actions.shape == (64,)
        assert actions.dtype == np.uint8
        assert np.all(snapshot["player_action_mask"][np.arange(64), actions])


def test_opponent_sampling_replays_from_the_same_seed() -> None:
    seeds = np.arange(100, 116, dtype=np.uint64)
    snapshot = NativeBatch(seeds, randomize_spawns=True).snapshot()
    first = OpponentPool(num_envs=16, seed=77)
    second = OpponentPool(num_envs=16, seed=77)

    for stage in ("A", "B", "C", "D"):
        first_strategies = first.sample_strategies(stage)
        second_strategies = second.sample_strategies(stage)
        np.testing.assert_array_equal(first_strategies, second_strategies)
        np.testing.assert_array_equal(
            first.actions(snapshot, first_strategies),
            second.actions(snapshot, second_strategies),
        )
