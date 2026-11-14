# Created at: 2026-11-14 04:16 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:16 EST
# Last Modified by: Codex
# Verifies exact GAE boundary semantics and recurrent sequence construction.

from __future__ import annotations

import torch

from training.rollout import RecurrentRollout, compute_gae


def test_gae_bootstraps_truncation_but_not_termination_and_stops_recursion() -> None:
    rewards = torch.tensor([[1.0], [1.0]])
    values = torch.tensor([[1.0], [2.0]])
    next_values = torch.tensor([[2.0], [3.0]])
    active = torch.ones((2, 1), dtype=torch.bool)

    terminated_advantage, _ = compute_gae(
        rewards,
        values,
        next_values,
        terminated=torch.tensor([[False], [True]]),
        truncated=torch.zeros((2, 1), dtype=torch.bool),
        active=active,
        gamma=0.99,
        gae_lambda=0.95,
    )
    truncated_advantage, _ = compute_gae(
        rewards,
        values,
        next_values,
        terminated=torch.zeros((2, 1), dtype=torch.bool),
        truncated=torch.tensor([[False], [True]]),
        active=active,
        gamma=0.99,
        gae_lambda=0.95,
    )

    expected_terminated = torch.tensor([[1.98 + 0.99 * 0.95 * -1.0], [-1.0]])
    expected_truncated = torch.tensor([[1.98 + 0.99 * 0.95 * 1.97], [1.97]])
    torch.testing.assert_close(terminated_advantage, expected_terminated)
    torch.testing.assert_close(truncated_advantage, expected_truncated)


def test_sequence_batches_preserve_chunk_initial_hidden_and_loss_masks() -> None:
    rollout = RecurrentRollout(environment_steps=4, num_envs=1, agents_per_env=1)
    for step in range(4):
        rollout.add(
            spatial=torch.full((1, 13, 5, 5), step, dtype=torch.uint8),
            scalar=torch.full((1, 46), float(step)),
            action_mask=torch.ones((1, 9), dtype=torch.bool),
            actions=torch.tensor([8]),
            old_log_prob=torch.tensor([float(step)]),
            values=torch.tensor([float(step)]),
            rewards=torch.tensor([1.0]),
            next_values=torch.tensor([float(step + 1)]),
            terminated=torch.tensor([False]),
            truncated=torch.tensor([False]),
            active=torch.tensor([step != 3]),
            episode_starts=torch.tensor([step == 2]),
            hidden=torch.full((1, 256), float(step)),
        )
    rollout.finish(gamma=0.99, gae_lambda=0.95)

    batches = list(
        rollout.sequence_batches(
            sequence_length=2,
            sequences_per_batch=2,
            generator=torch.Generator().manual_seed(0),
            shuffle=False,
        )
    )

    assert len(batches) == 1
    batch = batches[0]
    assert batch.spatial.shape == (2, 2, 13, 5, 5)
    torch.testing.assert_close(batch.initial_hidden[:, 0], torch.zeros((1, 256)))
    torch.testing.assert_close(batch.initial_hidden[:, 1], torch.full((1, 256), 2.0))
    assert batch.loss_mask.tolist() == [[True, True], [True, False]]
    assert batch.episode_starts.tolist() == [[False, False], [True, False]]
