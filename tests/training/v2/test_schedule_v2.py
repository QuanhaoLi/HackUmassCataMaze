# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 21:09 EST
# Last Modified by: Codex
# Verifies the exact V2 parameter ownership of each warm-start phase.

from __future__ import annotations

from training.v2.model import PersonaRecurrentActorCritic
from training.v2.schedule import TrainingPhase, apply_training_phase


def test_heads_only_phase_does_not_modify_the_shared_v1_trunk() -> None:
    names = apply_training_phase(
        PersonaRecurrentActorCritic(), TrainingPhase.HEADS_ONLY
    )
    assert all(
        name.startswith(("actors.", "critics.", "persona_gamma", "persona_beta"))
        for name in names
    )


def test_recurrent_phase_adds_only_fusion_and_gru() -> None:
    names = apply_training_phase(PersonaRecurrentActorCritic(), TrainingPhase.RECURRENT)
    assert any(name.startswith("fusion.") for name in names)
    assert any(name.startswith("gru.") for name in names)
    assert not any(name.startswith("visual_stem.") for name in names)
    assert not any(name.startswith("scalar_encoder.") for name in names)


def test_full_phase_enables_every_parameter() -> None:
    model = PersonaRecurrentActorCritic()
    names = apply_training_phase(model, TrainingPhase.FULL)
    assert len(names) == len(tuple(model.named_parameters()))


def test_persona_neutral_phase_trains_only_heads() -> None:
    model = PersonaRecurrentActorCritic()
    names = apply_training_phase(model, TrainingPhase.HEADS_NEUTRAL)
    assert all(name.startswith(("actors.", "critics.")) for name in names)
    assert model.persona_gamma.requires_grad is False
    assert model.persona_beta.requires_grad is False
