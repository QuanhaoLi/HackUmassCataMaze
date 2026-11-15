# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:04 EST
# Last Modified by: Codex
# Exports an ESP-DL-compatible V2 actor-only recurrent step with three persona heads.

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from training.export_esp import ESP_DL_SUPPORTED_OPERATORS, make_esp_compatible
from training.v2.model import PersonaRecurrentActorCritic


class EmbeddedPersonaPolicyStep(nn.Module):
    def __init__(self, model: PersonaRecurrentActorCritic) -> None:
        super().__init__()
        self.model = model

    def forward(
        self,
        spatial: torch.Tensor,
        scalar: torch.Tensor,
        hidden: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        output = self.model(
            spatial.unsqueeze(1),
            scalar.unsqueeze(1),
            hidden=hidden,
        )
        return output.logits_all[:, 0], output.hidden


def load_v2_model(checkpoint: str | Path) -> PersonaRecurrentActorCritic:
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    if "model" not in payload:
        raise ValueError("V2 checkpoint does not contain model state")
    model = PersonaRecurrentActorCritic()
    model.load_state_dict(payload["model"])
    return model.eval()


def export_onnx(wrapper: EmbeddedPersonaPolicyStep, destination: str | Path) -> Path:
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    wrapper = wrapper.cpu().eval()
    inputs = (
        torch.zeros(1, 13, 5, 5, dtype=torch.float32),
        torch.zeros(1, 46, dtype=torch.float32),
        torch.zeros(1, 1, 256, dtype=torch.float32),
    )
    torch.onnx.export(
        wrapper,
        inputs,
        output,
        input_names=("spatial", "scalar", "hidden"),
        output_names=("logits_all", "next_hidden"),
        opset_version=18,
        do_constant_folding=True,
        dynamo=False,
    )
    return output


def validate_onnx(
    wrapper: EmbeddedPersonaPolicyStep,
    model_path: str | Path,
    *,
    trials: int,
    seed: int,
) -> dict[str, Any]:
    import onnx
    import onnxruntime as ort

    path = Path(model_path)
    graph = onnx.load(path)
    onnx.checker.check_model(graph)
    operators = sorted({node.op_type for node in graph.graph.node})
    unsupported = sorted(set(operators) - ESP_DL_SUPPORTED_OPERATORS)
    initializers = [initializer.name for initializer in graph.graph.initializer]
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    generator = torch.Generator().manual_seed(seed)
    maximum = {"logits": 0.0, "hidden": 0.0}
    wrapper = wrapper.cpu().eval()
    for trial in range(trials):
        spatial = torch.randint(0, 2, (1, 13, 5, 5), generator=generator).float()
        scalar = torch.rand((1, 46), generator=generator)
        scalar[:, 43:46] = 0.0
        scalar[:, 43 + (trial % 3)] = 1.0
        hidden = torch.randn((1, 1, 256), generator=generator) * 0.1
        with torch.no_grad():
            expected = wrapper(spatial, scalar, hidden)
        actual = session.run(
            None,
            {
                "spatial": spatial.numpy(),
                "scalar": scalar.numpy(),
                "hidden": hidden.numpy(),
            },
        )
        maximum["logits"] = max(
            maximum["logits"],
            float(np.max(np.abs(expected[0].numpy() - actual[0]))),
        )
        maximum["hidden"] = max(
            maximum["hidden"],
            float(np.max(np.abs(expected[1].numpy() - actual[1]))),
        )
    return {
        "operators": operators,
        "unsupported_operators": unsupported,
        "critic_initializers": sorted(name for name in initializers if "critics" in name),
        "max_logit_error": maximum["logits"],
        "max_hidden_error": maximum["hidden"],
        "onnx_bytes": path.stat().st_size,
        "onnx_sha256": sha256(path.read_bytes()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--trials", type=int, default=256)
    arguments = parser.parse_args()
    model = load_v2_model(arguments.checkpoint)
    wrapper = EmbeddedPersonaPolicyStep(make_esp_compatible(model)).eval()
    output = export_onnx(wrapper, arguments.output)
    report = validate_onnx(wrapper, output, trials=arguments.trials, seed=20261114)
    report["checkpoint"] = str(arguments.checkpoint)
    report["model_arch"] = "catamaze.model.persona-rppo.v2"
    report_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    Path(arguments.report).write_text(report_text, encoding="utf-8")
    print(report_text, end="")


if __name__ == "__main__":
    main()
