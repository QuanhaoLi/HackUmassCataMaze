# Created at: 2026-11-14 03:40 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:38 EST
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
    assert snapshot["player_spatial"].shape == (2, 13, 5, 5)
    assert snapshot["player_action_mask"].shape == (2, 9)
    assert snapshot["shortest_path_action"].shape == (2,)
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


def test_randomized_spawns_and_partial_reset_are_seeded_and_isolated() -> None:
    seeds = np.array([31, 32, 33], dtype=np.uint64)
    batch = NativeBatch(seeds, randomize_spawns=True)
    initial = batch.snapshot()
    for env in range(3):
        assert len({tuple(position) for position in initial["positions"][env]}) == 4

    waits = np.full((3,), 8, dtype=np.uint8)
    ai_waits = np.full((3, 3), 8, dtype=np.uint8)
    stepped = batch.step(waits, ai_waits)
    preserved_hashes = stepped["state_hash"].copy()
    reset = batch.reset_at(
        np.array([1], dtype=np.int64), np.array([999], dtype=np.uint64)
    )

    assert reset["tick"].tolist() == [1, 0, 1]
    assert reset["state_hash"][0] == preserved_hashes[0]
    assert reset["state_hash"][2] == preserved_hashes[2]
    assert reset["state_hash"][1] != preserved_hashes[1]

    replay = NativeBatch(seeds, randomize_spawns=True)
    np.testing.assert_array_equal(replay.snapshot()["positions"], initial["positions"])


def test_canonical_state_restore_replays_the_next_transition() -> None:
    source = NativeBatch(np.array([71, 72], dtype=np.uint64), randomize_spawns=True)
    source.step(
        np.array([4, 8], dtype=np.uint8),
        np.array([[8, 8, 8], [0, 4, 8]], dtype=np.uint8),
    )
    serialized = source.save_state()
    restored = NativeBatch(np.array([1, 2], dtype=np.uint64), randomize_spawns=True)

    restored.load_state(serialized)

    np.testing.assert_array_equal(
        restored.snapshot()["state_hash"], source.snapshot()["state_hash"]
    )
    player_actions = np.array([8, 3], dtype=np.uint8)
    ai_actions = np.array([[0, 8, 8], [8, 8, 8]], dtype=np.uint8)
    expected = source.step(player_actions, ai_actions)
    actual = restored.step(player_actions, ai_actions)
    np.testing.assert_array_equal(actual["state_hash"], expected["state_hash"])
    np.testing.assert_array_equal(actual["events"], expected["events"])
