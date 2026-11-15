# Created at: 2026-11-14 19:41 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:41 EST
# Last Modified by: Codex
# Verifies causal V2 ablations remove only declared persona mechanisms.

from __future__ import annotations

import torch

from training.v2.ablation import Ablation, apply_ablation
from training.v2.model import PersonaRecurrentActorCritic


def specialized_model() -> PersonaRecurrentActorCritic:
    model = PersonaRecurrentActorCritic()
    with torch.no_grad():
        model.persona_gamma.fill_(0.1)
        model.persona_beta.fill_(0.2)
        model.actors[1].bias.add_(1.0)
        model.actors[2].bias.sub_(1.0)
    return model


def test_no_modulation_preserves_heads_but_zeros_affine_persona_state() -> None:
    source = specialized_model()
    candidate = apply_ablation(source, Ablation.NO_MODULATION)
    assert torch.count_nonzero(candidate.persona_gamma) == 0
    assert torch.count_nonzero(candidate.persona_beta) == 0
    assert not torch.equal(candidate.actors[0].bias, candidate.actors[1].bias)


def test_shared_head_preserves_modulation_but_copies_head_zero() -> None:
    source = specialized_model()
    candidate = apply_ablation(source, Ablation.SHARED_HEAD)
    assert torch.count_nonzero(candidate.persona_gamma) > 0
    for index in (1, 2):
        torch.testing.assert_close(candidate.actors[index].weight, candidate.actors[0].weight)
        torch.testing.assert_close(candidate.actors[index].bias, candidate.actors[0].bias)


def test_no_persona_removes_input_modulation_and_head_differences() -> None:
    candidate = apply_ablation(specialized_model(), Ablation.NO_PERSONA)
    assert torch.count_nonzero(candidate.persona_gamma) == 0
    assert torch.count_nonzero(candidate.persona_beta) == 0
    assert torch.count_nonzero(candidate.scalar_encoder[0].weight[:, 43:46]) == 0
    for index in (1, 2):
        torch.testing.assert_close(candidate.actors[index].weight, candidate.actors[0].weight)
        torch.testing.assert_close(candidate.actors[index].bias, candidate.actors[0].bias)
