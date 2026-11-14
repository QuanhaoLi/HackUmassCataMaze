# Created at: 2026-11-14 18:52 EST
# Created by: Codex
# Last Modified at: 2026-11-14 18:52 EST
# Last Modified by: Codex
# Verifies V2 migration equivalence and isolated persona-head behavior.

from __future__ import annotations

from io import BytesIO

import torch

from training.model import RecurrentActorCritic
from training.v2.model import PersonaRecurrentActorCritic


def persona_scalars(batch: int, time: int) -> torch.Tensor:
    scalar = torch.rand(batch, time, 46)
    scalar[..., 43:46] = 0.0
    for item in range(batch):
        scalar[item, :, 43 + (item % 3)] = 1.0
    return scalar


def test_v2_shapes_and_parameter_budget() -> None:
    model = PersonaRecurrentActorCritic()
    spatial = torch.rand(3, 4, 13, 5, 5)
    scalar = persona_scalars(3, 4)
    output = model(spatial, scalar)
    assert output.logits.shape == (3, 4, 9)
    assert output.logits_all.shape == (3, 4, 3, 9)
    assert output.values.shape == (3, 4)
    assert output.values_all.shape == (3, 4, 3)
    assert output.hidden.shape == (1, 3, 256)
    parameters = sum(parameter.numel() for parameter in model.parameters())
    assert 1_010_826 < parameters < 1_030_000


def test_v1_migration_is_exact_for_every_persona_at_step_zero() -> None:
    torch.manual_seed(20261114)
    v1 = RecurrentActorCritic().eval()
    v2 = PersonaRecurrentActorCritic.from_v1(v1).eval()
    spatial = torch.rand(3, 5, 13, 5, 5)
    scalar = persona_scalars(3, 5)
    hidden = torch.randn(1, 3, 256) * 0.1
    with torch.no_grad():
        expected = v1(spatial, scalar, hidden=hidden)
        actual = v2(spatial, scalar, hidden=hidden)
    torch.testing.assert_close(actual.logits, expected.logits, rtol=0.0, atol=1e-6)
    torch.testing.assert_close(actual.values, expected.values, rtol=0.0, atol=1e-6)
    torch.testing.assert_close(actual.hidden, expected.hidden, rtol=0.0, atol=1e-6)
    for persona in range(3):
        torch.testing.assert_close(
            actual.logits_all[:, :, persona], expected.logits, rtol=0.0, atol=1e-6
        )
        torch.testing.assert_close(
            actual.values_all[:, :, persona], expected.values, rtol=0.0, atol=1e-6
        )
    assert torch.count_nonzero(v2.persona_gamma).item() == 0
    assert torch.count_nonzero(v2.persona_beta).item() == 0


def test_selected_head_and_every_persona_parameter_receive_gradients() -> None:
    model = PersonaRecurrentActorCritic()
    spatial = torch.rand(3, 2, 13, 5, 5)
    scalar = persona_scalars(3, 2)
    output = model(spatial, scalar)
    expected_logits = torch.stack(
        [output.logits_all[index, :, index] for index in range(3)], dim=0
    )
    expected_values = torch.stack(
        [output.values_all[index, :, index] for index in range(3)], dim=0
    )
    torch.testing.assert_close(output.logits, expected_logits)
    torch.testing.assert_close(output.values, expected_values)
    (output.logits.square().mean() + output.values.square().mean()).backward()
    for actor, critic in zip(model.actors, model.critics):
        assert actor.weight.grad is not None
        assert torch.count_nonzero(actor.weight.grad).item() > 0
        assert critic.weight.grad is not None
        assert torch.count_nonzero(critic.weight.grad).item() > 0
    assert model.persona_gamma.grad is not None
    assert torch.count_nonzero(model.persona_gamma.grad).item() > 0
    assert model.persona_beta.grad is not None
    assert torch.count_nonzero(model.persona_beta.grad).item() > 0


def test_episode_starts_reset_hidden_and_state_dict_round_trips() -> None:
    torch.manual_seed(7)
    model = PersonaRecurrentActorCritic().eval()
    spatial = torch.rand(2, 3, 13, 5, 5)
    scalar = persona_scalars(2, 3)
    hidden = torch.randn(1, 2, 256)
    starts = torch.tensor([[True, False, False], [False, True, False]])
    with torch.no_grad():
        original = model(spatial, scalar, hidden=hidden, episode_starts=starts)
    payload = BytesIO()
    torch.save(model.state_dict(), payload)
    payload.seek(0)
    restored = PersonaRecurrentActorCritic().eval()
    restored.load_state_dict(torch.load(payload, weights_only=True))
    with torch.no_grad():
        replay = restored(spatial, scalar, hidden=hidden, episode_starts=starts)
    torch.testing.assert_close(replay.logits_all, original.logits_all, rtol=0.0, atol=0.0)
    torch.testing.assert_close(replay.values_all, original.values_all, rtol=0.0, atol=0.0)
    torch.testing.assert_close(replay.hidden, original.hidden, rtol=0.0, atol=0.0)
