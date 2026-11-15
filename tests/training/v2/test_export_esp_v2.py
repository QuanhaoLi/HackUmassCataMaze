# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:04 EST
# Last Modified by: Codex
# Verifies V2 actor-only ESP export without modifying the V1 export path.

from __future__ import annotations

from pathlib import Path

import torch

from training.export_esp import make_esp_compatible
from training.v2.export_esp import (
    EmbeddedPersonaPolicyStep,
    export_onnx,
    validate_onnx,
)
from training.v2.model import PersonaRecurrentActorCritic


def test_actor_only_step_has_three_heads_and_no_value_output() -> None:
    wrapper = EmbeddedPersonaPolicyStep(PersonaRecurrentActorCritic().eval())
    logits, hidden = wrapper(
        torch.zeros(1, 13, 5, 5),
        torch.zeros(1, 46),
        torch.zeros(1, 1, 256),
    )
    assert logits.shape == (1, 3, 9)
    assert hidden.shape == (1, 1, 256)


def test_v2_onnx_is_supported_matches_pytorch_and_prunes_critics(
    tmp_path: Path,
) -> None:
    wrapper = EmbeddedPersonaPolicyStep(
        make_esp_compatible(PersonaRecurrentActorCritic())
    ).eval()
    model_path = export_onnx(wrapper, tmp_path / "persona-v2.onnx")
    report = validate_onnx(wrapper, model_path, trials=8, seed=101)
    assert report["unsupported_operators"] == []
    assert report["critic_initializers"] == []
    assert report["max_logit_error"] <= 1e-5
    assert report["max_hidden_error"] <= 1e-5
