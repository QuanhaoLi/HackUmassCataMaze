# Created at: 2026-11-14 19:41 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:41 EST
# Last Modified by: Codex
# Creates isolated causal V2 ablation checkpoints without retraining or V1 changes.

from __future__ import annotations

import argparse
from copy import deepcopy
from enum import Enum
from pathlib import Path

import torch

from training.v2.export_esp import load_v2_model
from training.v2.model import PersonaRecurrentActorCritic


class Ablation(str, Enum):
    NO_MODULATION = "no-modulation"
    SHARED_HEAD = "shared-head"
    NO_PERSONA = "no-persona"


def apply_ablation(
    model: PersonaRecurrentActorCritic, ablation: Ablation
) -> PersonaRecurrentActorCritic:
    candidate = deepcopy(model).cpu().eval()
    with torch.no_grad():
        if ablation in (Ablation.NO_MODULATION, Ablation.NO_PERSONA):
            candidate.persona_gamma.zero_()
            candidate.persona_beta.zero_()
        if ablation in (Ablation.SHARED_HEAD, Ablation.NO_PERSONA):
            actor = candidate.actors[0].state_dict()
            critic = candidate.critics[0].state_dict()
            for index in range(1, 3):
                candidate.actors[index].load_state_dict(actor)
                candidate.critics[index].load_state_dict(critic)
        if ablation is Ablation.NO_PERSONA:
            candidate.scalar_encoder[0].weight[:, 43:46] = 0.0
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ablation", choices=[item.value for item in Ablation], required=True)
    arguments = parser.parse_args()
    source = torch.load(arguments.checkpoint, map_location="cpu", weights_only=False)
    model = apply_ablation(
        load_v2_model(arguments.checkpoint), Ablation(arguments.ablation)
    )
    payload = {
        "format": "catamaze.persona-ablation.v2",
        "ablation": arguments.ablation,
        "source_checkpoint": str(arguments.checkpoint),
        "model": model.state_dict(),
        "source_training_state": source.get("training_state"),
    }
    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, output)


if __name__ == "__main__":
    main()
