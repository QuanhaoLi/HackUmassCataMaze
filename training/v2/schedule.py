# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 21:09 EST
# Last Modified by: Codex
# Owns explicit parameter freezing for V2 warm-start phases.

from __future__ import annotations

from enum import Enum

from training.v2.model import PersonaRecurrentActorCritic


class TrainingPhase(str, Enum):
    HEADS_ONLY = "heads-only"
    HEADS_NEUTRAL = "heads-neutral"
    RECURRENT = "recurrent"
    FULL = "full"


def apply_training_phase(
    model: PersonaRecurrentActorCritic, phase: TrainingPhase
) -> tuple[str, ...]:
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    trainable_modules = [model.actors, model.critics]
    if phase in (TrainingPhase.RECURRENT, TrainingPhase.FULL):
        trainable_modules.extend((model.fusion, model.gru))
    if phase is TrainingPhase.FULL:
        trainable_modules.extend(
            (
                model.visual_stem,
                model.visual_residual,
                model.visual_projection,
                model.scalar_encoder,
            )
        )
    for module in trainable_modules:
        for parameter in module.parameters():
            parameter.requires_grad_(True)
    if phase is not TrainingPhase.HEADS_NEUTRAL:
        model.persona_gamma.requires_grad_(True)
        model.persona_beta.requires_grad_(True)
    trainable = tuple(name for name, value in model.named_parameters() if value.requires_grad)
    if not trainable:
        raise RuntimeError(f"V2 phase {phase.value} has no trainable parameters")
    return trainable
