# Created at: 2026-11-14 10:40 EST
# Created by: Codex
# Last Modified at: 2026-11-14 10:40 EST
# Last Modified by: Codex
# Verifies the fixed-shape ESP policy export and ONNX numerical parity.

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn

from training.export_esp import (
    EmbeddedPolicyStep,
    FixedGroupNorm,
    export_onnx,
    make_esp_compatible,
    validate_onnx,
)
from training.model import RecurrentActorCritic


def test_fixed_group_norm_matches_pytorch_group_norm() -> None:
    torch.manual_seed(101)
    original = nn.GroupNorm(8, 64).eval()
    replacement = FixedGroupNorm.from_group_norm(original, height=5, width=5).eval()
    inputs = torch.randn(1, 64, 5, 5)

    torch.testing.assert_close(replacement(inputs), original(inputs), rtol=1e-6, atol=1e-6)


def test_esp_wrapper_has_single_agent_single_tick_contract() -> None:
    torch.manual_seed(103)
    wrapper = EmbeddedPolicyStep(make_esp_compatible(RecurrentActorCritic())).eval()

    logits, value, hidden = wrapper(
        torch.zeros(1, 13, 5, 5),
        torch.zeros(1, 46),
        torch.zeros(1, 1, 256),
    )

    assert logits.shape == (1, 9)
    assert value.shape == (1,)
    assert hidden.shape == (1, 1, 256)


def test_onnx_export_uses_supported_ops_and_matches_pytorch(tmp_path: Path) -> None:
    torch.manual_seed(107)
    wrapper = EmbeddedPolicyStep(make_esp_compatible(RecurrentActorCritic())).eval()
    output = tmp_path / "policy.onnx"

    export_onnx(wrapper, output)
    report = validate_onnx(wrapper, output, trials=8, seed=109)

    assert report["unsupported_operators"] == []
    assert report["max_logit_error"] <= 1e-5
    assert report["max_value_error"] <= 1e-5
    assert report["max_hidden_error"] <= 1e-5
