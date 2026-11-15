# Created at: 2026-11-14 18:52 EST
# Created by: Codex
# Last Modified at: 2026-11-14 18:52 EST
# Last Modified by: Codex
# Verifies deterministic persona-balanced recurrent minibatches.

from __future__ import annotations

import torch

from training.rollout import RecurrentRollout
from training.v2.rollout import persona_sequence_batches


def completed_rollout() -> RecurrentRollout:
    rollout = RecurrentRollout(environment_steps=4, num_envs=2, agents_per_env=3)
    for step in range(4):
        scalar = torch.zeros(6, 46)
        for agent in range(6):
            scalar[agent, 43 + (agent % 3)] = 1.0
        rollout.add(
            spatial=torch.zeros(6, 13, 5, 5, dtype=torch.uint8),
            scalar=scalar,
            action_mask=torch.ones(6, 9, dtype=torch.bool),
            actions=torch.full((6,), 8, dtype=torch.int64),
            old_log_prob=torch.zeros(6),
            values=torch.zeros(6),
            rewards=torch.ones(6),
            next_values=torch.zeros(6),
            terminated=torch.full((6,), step == 3),
            truncated=torch.zeros(6, dtype=torch.bool),
            active=torch.ones(6, dtype=torch.bool),
            episode_starts=torch.full((6,), step == 0),
            hidden=torch.zeros(6, 256),
        )
    rollout.finish(gamma=0.995, gae_lambda=0.95)
    return rollout


def test_every_batch_has_equal_persona_sequence_counts() -> None:
    batches = list(
        persona_sequence_batches(
            completed_rollout(),
            sequence_length=2,
            sequences_per_batch=7,
            generator=torch.Generator().manual_seed(11),
        )
    )
    assert batches
    for batch in batches:
        persona = batch.scalar[:, 0, 43:46].argmax(dim=-1)
        counts = torch.bincount(persona, minlength=3)
        assert counts[0] == counts[1] == counts[2]


def test_batch_order_is_reproducible_for_the_same_generator_seed() -> None:
    def signatures() -> list[torch.Tensor]:
        return [
            batch.initial_hidden.clone()
            for batch in persona_sequence_batches(
                completed_rollout(),
                sequence_length=2,
                sequences_per_batch=6,
                generator=torch.Generator().manual_seed(19),
            )
        ]

    first = signatures()
    second = signatures()
    assert len(first) == len(second)
    for left, right in zip(first, second):
        torch.testing.assert_close(left, right, rtol=0.0, atol=0.0)
