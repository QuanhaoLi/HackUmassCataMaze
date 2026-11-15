# Created at: 2026-11-14 18:52 EST
# Created by: Codex
# Last Modified at: 2026-11-14 18:52 EST
# Last Modified by: Codex
# Verifies persona-balanced recurrent PPO without changing the V1 optimizer.

from __future__ import annotations

import torch

from training.model import masked_categorical
from training.ppo import PPOConfig
from training.rollout import RecurrentRollout
from training.v2.model import PersonaRecurrentActorCritic
from training.v2.ppo import PersonaPPOTrainer, normalize_advantages_per_persona


def test_advantages_are_normalized_independently_per_persona() -> None:
    advantages = torch.tensor([1.0, 100.0, -7.0, 3.0, 300.0, 5.0])
    personas = torch.tensor([0, 1, 2, 0, 1, 2])
    normalized = normalize_advantages_per_persona(
        advantages, personas, torch.ones_like(personas, dtype=torch.bool)
    )
    for persona in range(3):
        selected = normalized[personas == persona]
        torch.testing.assert_close(selected.mean(), torch.tensor(0.0), atol=1e-6, rtol=0.0)
        torch.testing.assert_close(
            selected.square().mean(), torch.tensor(1.0), atol=1e-6, rtol=0.0
        )


def make_rollout(model: PersonaRecurrentActorCritic) -> RecurrentRollout:
    rollout = RecurrentRollout(environment_steps=4, num_envs=1, agents_per_env=3)
    hidden = torch.zeros((1, 3, 256))
    for step in range(4):
        spatial = torch.randint(0, 2, (3, 13, 5, 5), dtype=torch.uint8)
        scalar = torch.rand((3, 46))
        scalar[:, 43:46] = torch.eye(3)
        mask = torch.ones((3, 9), dtype=torch.bool)
        with torch.no_grad():
            output = model(
                spatial[:, None].float(),
                scalar[:, None],
                hidden=hidden,
                episode_starts=torch.full((3, 1), step == 0),
            )
            distribution = masked_categorical(output.logits[:, 0], mask)
            actions = distribution.sample()
            log_prob = distribution.log_prob(actions)
            values = output.values[:, 0]
            hidden_before = hidden[0].clone()
            hidden = output.hidden
        rollout.add(
            spatial=spatial,
            scalar=scalar,
            action_mask=mask,
            actions=actions,
            old_log_prob=log_prob,
            values=values,
            rewards=torch.tensor([1.0, 2.0, 3.0]),
            next_values=values + 0.1,
            terminated=torch.full((3,), step == 3),
            truncated=torch.zeros(3, dtype=torch.bool),
            active=torch.ones(3, dtype=torch.bool),
            episode_starts=torch.full((3,), step == 0),
            hidden=hidden_before,
        )
    rollout.finish(gamma=0.995, gae_lambda=0.95)
    return rollout


def test_persona_ppo_updates_every_head_and_reports_finite_metrics() -> None:
    torch.manual_seed(31)
    model = PersonaRecurrentActorCritic()
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, eps=1e-5)
    rollout = make_rollout(model)
    before = {
        name: parameter.detach().clone()
        for name, parameter in model.named_parameters()
        if name.startswith("actors.") or name.startswith("critics.")
    }
    trainer = PersonaPPOTrainer(
        model,
        optimizer,
        PPOConfig(update_epochs=2, sequence_length=2, sequences_per_batch=6),
        device=torch.device("cpu"),
    )
    metrics = trainer.update(rollout, generator=torch.Generator().manual_seed(37))
    assert metrics.updates > 0
    assert all(torch.isfinite(torch.tensor(value)) for value in metrics.as_dict().values())
    for persona in range(3):
        assert any(
            not torch.equal(before[name], parameter)
            for name, parameter in model.named_parameters()
            if name.startswith(f"actors.{persona}.")
            or name.startswith(f"critics.{persona}.")
        )
        assert f"persona/{persona}/policy_loss" in metrics.as_dict()
