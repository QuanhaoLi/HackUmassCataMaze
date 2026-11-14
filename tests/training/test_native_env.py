# Created at: 2026-11-14 03:40 EST
# Created by: Codex
# Last Modified at: 2026-11-14 03:40 EST
# Last Modified by: Codex
# Verifies the zero-network batched C++ training boundary.

from __future__ import annotations

import numpy as np
import pytest

from training._native import NativeBatch


def test_snapshot_has_frozen_batch_shapes_and_dtypes() -> None:
    batch = NativeBatch(np.array([11, 22], dtype=np.uint64))

    snapshot = batch.snapshot()

    assert snapshot["spatial"].shape == (2, 3, 13, 5, 5)
    assert snapshot["spatial"].dtype == np.uint8
    assert snapshot["scalar"].shape == (2, 3, 46)
    assert snapshot["scalar"].dtype == np.float32
    assert snapshot["action_mask"].shape == (2, 3, 9)
    assert snapshot["action_mask"].dtype == np.bool_
    assert snapshot["alive"].shape == (2, 3)
    assert snapshot["positions"].shape == (2, 4, 2)
    assert snapshot["events"].shape == (2, 192, 7)
    assert snapshot["event_count"].shape == (2,)
    assert snapshot["distance_to_player"].shape == (2, 3)
    assert np.all(snapshot["action_mask"][:, :, 8])
    assert np.all(snapshot["tick"] == 0)


def test_reset_and_step_replay_exactly() -> None:
    seeds = np.array([101, 202], dtype=np.uint64)
    batch = NativeBatch(seeds)
    player_wait = np.full((2,), 8, dtype=np.uint8)
    ai_wait = np.full((2, 3), 8, dtype=np.uint8)

    first = batch.step(player_wait, ai_wait)
    first_hash = first["state_hash"].copy()
    first_spatial = first["spatial"].copy()
    assert np.all(first["tick"] == 1)

    reset = batch.reset(seeds)
    assert np.all(reset["tick"] == 0)
    replay = batch.step(player_wait, ai_wait)

    np.testing.assert_array_equal(replay["state_hash"], first_hash)
    np.testing.assert_array_equal(replay["spatial"], first_spatial)


def test_step_rejects_wrong_shapes_and_out_of_range_actions() -> None:
    batch = NativeBatch(np.array([1, 2], dtype=np.uint64))
    player_wait = np.full((2,), 8, dtype=np.uint8)
    ai_wait = np.full((2, 3), 8, dtype=np.uint8)

    with pytest.raises(ValueError, match="player_actions"):
        batch.step(player_wait.reshape(1, 2), ai_wait)
    with pytest.raises(ValueError, match="ai_actions"):
        batch.step(player_wait, ai_wait.reshape(3, 2))
    invalid = ai_wait.copy()
    invalid[0, 1] = 9
    with pytest.raises(ValueError, match="range"):
        batch.step(player_wait, invalid)
