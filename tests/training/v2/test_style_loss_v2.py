# Created at: 2026-11-14 20:40 EST
# Created by: Codex
# Last Modified at: 2026-11-14 20:40 EST
# Last Modified by: Codex
# Verifies bounded local-observation V2 style constraints and gradients.

from __future__ import annotations

import torch

from training.v2.style_loss import STYLE_METRIC_NAMES, persona_style_loss


def inputs() -> tuple[torch.Tensor, ...]:
    logits = torch.zeros(2, 1, 3, 9, requires_grad=True)
    action_mask = torch.ones(2, 1, 9, dtype=torch.bool)
    spatial = torch.zeros(2, 1, 13, 5, 5)
    scalar = torch.ones(2, 1, 46)
    loss_mask = torch.ones(2, 1, dtype=torch.bool)
    spatial[0, 0, 5, 1, 2] = 1.0
    spatial[1, 0, 5, 2, 4] = 1.0
    scalar[:, :, 0] = 0.4
    return logits, action_mask, spatial, scalar, loss_mask


def test_style_loss_is_finite_complete_and_backpropagates() -> None:
    tensors = inputs()
    loss, components = persona_style_loss(*tensors)
    assert torch.isfinite(loss)
    assert set(components) == set(STYLE_METRIC_NAMES)
    assert components["aggressive_aligned_shot_count"] > 0
    assert components["cautious_low_hp_retreat_count"] > 0
    loss.backward()
    assert tensors[0].grad is not None
    assert torch.count_nonzero(tensors[0].grad) > 0


def test_aligned_shot_and_retreat_respect_legal_action_masks() -> None:
    logits, action_mask, spatial, scalar, loss_mask = inputs()
    action_mask[0, 0, 4] = False
    action_mask[1, 0, 2] = False
    _loss, components = persona_style_loss(
        logits, action_mask, spatial, scalar, loss_mask
    )
    assert torch.isfinite(components["aggressive_aligned_shot"])
    assert torch.isfinite(components["cautious_low_hp_retreat"])


def test_empty_active_subset_returns_differentiable_zero() -> None:
    logits, action_mask, spatial, scalar, loss_mask = inputs()
    loss_mask[:] = False
    loss, components = persona_style_loss(
        logits, action_mask, spatial, scalar, loss_mask
    )
    assert loss == 0
    assert all(value == 0 for value in components.values())
    loss.backward()
    assert logits.grad is not None
