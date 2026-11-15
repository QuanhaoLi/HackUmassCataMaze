# Created at: 2026-11-14 18:52 EST
# Created by: Codex
# Last Modified at: 2026-11-14 18:52 EST
# Last Modified by: Codex
# Builds persona-balanced recurrent sequence batches from the frozen V1 rollout storage.

from __future__ import annotations

from collections.abc import Iterator

import torch

from training.rollout import RecurrentRollout, SequenceBatch
from training.v2.model import PERSONA_COUNT


def persona_sequence_batches(
    rollout: RecurrentRollout,
    *,
    sequence_length: int,
    sequences_per_batch: int,
    generator: torch.Generator | None,
    shuffle: bool = True,
    include_inactive: bool = False,
) -> Iterator[SequenceBatch]:
    if rollout.advantages is None or rollout.returns is None:
        raise RuntimeError("finish must be called before V2 batching")
    if rollout.agents_per_env != PERSONA_COUNT:
        raise ValueError("V2 rollout must contain exactly three persona agents per environment")
    if sequence_length <= 0 or rollout.environment_steps % sequence_length != 0:
        raise ValueError("sequence_length must evenly divide environment_steps")
    sequences_per_persona = sequences_per_batch // PERSONA_COUNT
    if sequences_per_persona <= 0:
        raise ValueError("sequences_per_batch must include every persona")

    candidates: list[list[tuple[int, int]]] = [
        [] for _ in range(PERSONA_COUNT)
    ]
    for batch_agent in range(rollout.batch_agents):
        persona = batch_agent % PERSONA_COUNT
        for start in range(0, rollout.environment_steps, sequence_length):
            if include_inactive or rollout.active[
                start : start + sequence_length, batch_agent
            ].any():
                candidates[persona].append((batch_agent, start))
    if any(not persona_candidates for persona_candidates in candidates):
        raise RuntimeError("V2 rollout has no active sequence for at least one persona")
    if shuffle:
        for persona in range(PERSONA_COUNT):
            order = torch.randperm(
                len(candidates[persona]), generator=generator
            ).tolist()
            candidates[persona] = [candidates[persona][index] for index in order]

    balanced_count = min(len(persona_candidates) for persona_candidates in candidates)
    for offset in range(0, balanced_count, sequences_per_persona):
        count = min(sequences_per_persona, balanced_count - offset)
        selected = [
            candidate
            for persona in range(PERSONA_COUNT)
            for candidate in candidates[persona][offset : offset + count]
        ]

        def stack(source: torch.Tensor) -> torch.Tensor:
            return torch.stack(
                [
                    source[start : start + sequence_length, agent]
                    for agent, start in selected
                ]
            )

        initial_hidden = torch.stack(
            [rollout.hidden[start, agent] for agent, start in selected], dim=0
        ).unsqueeze(0)
        yield SequenceBatch(
            spatial=stack(rollout.spatial),
            scalar=stack(rollout.scalar),
            action_mask=stack(rollout.action_mask),
            actions=stack(rollout.actions),
            old_log_prob=stack(rollout.old_log_prob),
            old_values=stack(rollout.values),
            advantages=stack(rollout.advantages),
            returns=stack(rollout.returns),
            episode_starts=stack(rollout.episode_starts),
            initial_hidden=initial_hidden,
            loss_mask=stack(rollout.active),
        )
