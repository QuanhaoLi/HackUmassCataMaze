# Created at: 2026-11-14 04:16 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:16 EST
# Last Modified by: Codex
# Verifies a finite recurrent PPO optimization step with legal action masking.

from __future__ import annotations

import torch

from training.model import RecurrentActorCritic, masked_categorical
from training.ppo import PPOConfig, PPOTrainer
from training.rollout import RecurrentRollout


def test_ppo_update_changes_parameters_and_reports_finite_metrics() -> None:
    torch.manual_seed(23)
    model = RecurrentActorCritic()
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, eps=1e-5, weight_decay=1e-4)
    rollout = RecurrentRollout(environment_steps=4, num_envs=1, agents_per_env=1)
    hidden = torch.zeros((1, 1, 256))
    for step in range(4):
        spatial = torch.randint(0, 2, (1, 13, 5, 5), dtype=torch.uint8)
        scalar = torch.rand((1, 46))
        mask = torch.ones((1, 9), dtype=torch.bool)
        mask[:, 0] = False
        with torch.no_grad():
            output = model(
                spatial[:, None].float(),
                scalar[:, None],
                hidden=hidden,
                episode_starts=torch.tensor([[step == 0]]),
            )
            distribution = masked_categorical(output.logits[:, 0], mask)
            action = distribution.sample()
            log_prob = distribution.log_prob(action)
            value = output.values[:, 0]
            hidden_before = hidden[0].clone()
            hidden = output.hidden
            next_value = value + 0.1
        rollout.add(
            spatial=spatial,
            scalar=scalar,
            action_mask=mask,
            actions=action,
            old_log_prob=log_prob,
            values=value,
            rewards=torch.tensor([1.0]),
            next_values=next_value,
            terminated=torch.tensor([step == 3]),
            truncated=torch.tensor([False]),
            active=torch.tensor([True]),
            episode_starts=torch.tensor([step == 0]),
            hidden=hidden_before,
        )
    rollout.finish(gamma=0.995, gae_lambda=0.95)
    before = {name: parameter.detach().clone() for name, parameter in model.named_parameters()}
    trainer = PPOTrainer(
        model,
        optimizer,
        PPOConfig(update_epochs=2, sequence_length=2, sequences_per_batch=2),
        device=torch.device("cpu"),
    )

    metrics = trainer.update(rollout, generator=torch.Generator().manual_seed(29))

    assert metrics.updates > 0
    assert all(torch.isfinite(torch.tensor(value)) for value in metrics.as_dict().values())
    assert any(not torch.equal(before[name], parameter) for name, parameter in model.named_parameters())
