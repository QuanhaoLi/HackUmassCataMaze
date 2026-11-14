# Created at: 2026-11-14 04:24 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:24 EST
# Last Modified by: Codex
# Verifies live environment collection and immediate PPO consumption.

from __future__ import annotations

import torch

from training.collector import RolloutCollector
from training.env import CataMazeBatchEnv
from training.model import RecurrentActorCritic
from training.ppo import PPOConfig, PPOTrainer


def test_collector_builds_finite_rollout_consumed_by_ppo() -> None:
    torch.manual_seed(31)
    environment = CataMazeBatchEnv(num_envs=2, seed=37)
    model = RecurrentActorCritic()
    collector = RolloutCollector(environment, model, device=torch.device("cpu"))

    rollout, metrics = collector.collect(environment_steps=4, gamma=0.995, gae_lambda=0.95)

    assert metrics.agent_steps > 0
    assert metrics.invalid_actions == 0
    assert torch.isfinite(rollout.rewards).all()
    assert torch.equal(
        rollout.action_mask.gather(-1, rollout.actions.unsqueeze(-1)).squeeze(-1)[rollout.active],
        torch.ones_like(rollout.active[rollout.active]),
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
    trainer = PPOTrainer(
        model,
        optimizer,
        PPOConfig(update_epochs=1, sequence_length=2, sequences_per_batch=4),
        device=torch.device("cpu"),
    )
    update = trainer.update(rollout, generator=torch.Generator().manual_seed(41))
    assert update.updates > 0
