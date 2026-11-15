# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:04 EST
# Last Modified by: Codex
# Verifies balanced, disjoint, recurrent V2 quantization samples.

from __future__ import annotations

import torch

from training.v2.model import PersonaRecurrentActorCritic
from training.v2.quantize_esp import collect_persona_samples


def test_quantization_samples_are_balanced_persona_correct_and_recurrent() -> None:
    samples = collect_persona_samples(
        PersonaRecurrentActorCritic().eval(),
        count_per_persona=8,
        environment_steps=4,
        num_envs=4,
        seed=103,
        device=torch.device("cpu"),
    )
    assert [len(items) for items in samples] == [8, 8, 8]
    saw_recurrent_hidden = False
    identities: set[tuple[int, float, float]] = set()
    for persona, persona_samples in enumerate(samples):
        for inputs, mask in persona_samples:
            assert inputs[0].shape == (1, 13, 5, 5)
            assert inputs[1].shape == (1, 46)
            assert inputs[2].shape == (1, 1, 256)
            assert inputs[1][0, 43 + persona] == 1.0
            assert mask.shape == (1, 9)
            assert mask[0, 8]
            saw_recurrent_hidden = saw_recurrent_hidden or bool(torch.count_nonzero(inputs[2]))
            identities.add(
                (
                    persona,
                    float(inputs[1][0, 3]),
                    float(inputs[1][0, 4]),
                )
            )
    assert saw_recurrent_hidden
    assert len(identities) > 8
