# Created at: 2026-11-14 04:09 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:09 EST
# Last Modified by: Codex
# Verifies the recurrent actor-critic architecture and masked policy contract.

from __future__ import annotations

import io

import torch

from training.model import RecurrentActorCritic, masked_categorical


def inputs(batch: int = 2, time: int = 4) -> tuple[torch.Tensor, ...]:
    generator = torch.Generator().manual_seed(7)
    spatial = torch.randint(0, 2, (batch, time, 13, 5, 5), generator=generator).float()
    scalar = torch.rand((batch, time, 46), generator=generator)
    starts = torch.zeros((batch, time), dtype=torch.bool)
    return spatial, scalar, starts


def test_model_shapes_parameter_budget_and_finite_outputs() -> None:
    torch.manual_seed(11)
    model = RecurrentActorCritic()
    spatial, scalar, starts = inputs()

    output = model(spatial, scalar, episode_starts=starts)

    assert output.logits.shape == (2, 4, 9)
    assert output.values.shape == (2, 4)
    assert output.hidden.shape == (1, 2, 256)
    assert torch.isfinite(output.logits).all()
    assert torch.isfinite(output.values).all()
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    assert 900_000 <= parameter_count <= 1_200_000


def test_masked_categorical_assigns_exact_zero_probability_to_illegal_actions() -> None:
    logits = torch.tensor([[100.0, 2.0, -1.0, 4.0, 3.0, 2.0, 1.0, 0.0, -3.0]])
    mask = torch.tensor([[False, True, False, True, False, False, False, False, True]])

    distribution = masked_categorical(logits, mask)

    assert torch.equal(distribution.probs[~mask], torch.zeros_like(distribution.probs[~mask]))
    assert torch.allclose(distribution.probs.sum(dim=-1), torch.ones(1))


def test_episode_start_resets_hidden_state_inside_sequence() -> None:
    torch.manual_seed(13)
    model = RecurrentActorCritic()
    spatial, scalar, starts = inputs(batch=1, time=4)
    starts[:, 2] = True

    combined = model(spatial, scalar, episode_starts=starts)
    suffix = model(
        spatial[:, 2:],
        scalar[:, 2:],
        episode_starts=torch.tensor([[True, False]]),
    )

    torch.testing.assert_close(combined.logits[:, 2:], suffix.logits)
    torch.testing.assert_close(combined.values[:, 2:], suffix.values)
    torch.testing.assert_close(combined.hidden, suffix.hidden)


def test_persona_features_receive_gradient_and_state_dict_round_trips() -> None:
    torch.manual_seed(17)
    model = RecurrentActorCritic()
    spatial, scalar, starts = inputs(batch=1, time=2)
    scalar.requires_grad_(True)
    expected = model(spatial, scalar, episode_starts=starts)
    (expected.logits.sum() + expected.values.sum()).backward()
    assert scalar.grad is not None
    assert torch.count_nonzero(scalar.grad[..., 43:46]) > 0

    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    buffer.seek(0)
    restored = RecurrentActorCritic()
    restored.load_state_dict(torch.load(buffer, weights_only=True))
    actual = restored(spatial.detach(), scalar.detach(), episode_starts=starts)
    torch.testing.assert_close(actual.logits, expected.logits.detach(), rtol=0, atol=0)
    torch.testing.assert_close(actual.values, expected.values.detach(), rtol=0, atol=0)
