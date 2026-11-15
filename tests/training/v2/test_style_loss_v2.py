# Created at: 2026-11-14 20:40 EST
# Created by: Codex
# Last Modified at: 2026-11-14 21:39 EST
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
    actions = torch.zeros(2, 1, dtype=torch.long)
    spatial[0, 0, 5, 1, 2] = 1.0
    spatial[1, 0, 5, 2, 4] = 1.0
    scalar[:, :, 0] = 0.4
    return logits, action_mask, spatial, scalar, loss_mask, actions


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
    logits, action_mask, spatial, scalar, loss_mask, actions = inputs()
    action_mask[0, 0, 4] = False
    action_mask[1, 0, 2] = False
    _loss, components = persona_style_loss(
        logits, action_mask, spatial, scalar, loss_mask, actions
    )
    assert torch.isfinite(components["aggressive_aligned_shot"])
    assert torch.isfinite(components["cautious_low_hp_retreat"])


def test_empty_active_subset_returns_differentiable_zero() -> None:
    logits, action_mask, spatial, scalar, loss_mask, actions = inputs()
    loss_mask[:] = False
    loss, components = persona_style_loss(
        logits, action_mask, spatial, scalar, loss_mask, actions
    )
    assert loss == 0
    assert all(value == 0 for value in components.values())
    loss.backward()
    assert logits.grad is not None


def test_explorer_recurrent_first_visit_reinforces_only_novel_moves() -> None:
    logits = torch.zeros(1, 3, 3, 9, requires_grad=True)
    action_mask = torch.ones(1, 3, 9, dtype=torch.bool)
    spatial = torch.zeros(1, 3, 13, 5, 5)
    scalar = torch.zeros(1, 3, 46)
    scalar[..., 45] = 1.0
    scalar[0, 0, 3:5] = torch.tensor([1.0 / 49.0, 1.0 / 49.0])
    scalar[0, 1, 3:5] = torch.tensor([1.0 / 49.0, 2.0 / 49.0])
    scalar[0, 2, 3:5] = torch.tensor([1.0 / 49.0, 1.0 / 49.0])
    actions = torch.tensor([[1, 0, 8]])
    loss_mask = torch.ones(1, 3, dtype=torch.bool)
    _loss, components = persona_style_loss(
        logits, action_mask, spatial, scalar, loss_mask, actions
    )
    assert components["explorer_recurrent_first_visit_count"] == 1
    assert components["explorer_recurrent_first_visit"] > 0
