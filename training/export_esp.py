# Created at: 2026-11-14 10:41 EST
# Created by: Codex
# Last Modified at: 2026-11-14 10:41 EST
# Last Modified by: Codex
# Exports a fixed-shape one-step policy graph compatible with ESP-DL operators.

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from training.model import RecurrentActorCritic


ESP_DL_SUPPORTED_OPERATORS = {
    "Add",
    "Concat",
    "Constant",
    "Conv",
    "Div",
    "Flatten",
    "Gather",
    "Gemm",
    "GRU",
    "Identity",
    "LayerNormalization",
    "MatMul",
    "Mul",
    "ReduceMean",
    "Reshape",
    "Sigmoid",
    "Slice",
    "Sqrt",
    "Squeeze",
    "Sub",
    "Transpose",
    "Unsqueeze",
}


class FixedGroupNorm(nn.Module):
    """GroupNorm expressed only through ESP-DL primitive operators."""

    def __init__(
        self,
        groups: int,
        channels: int,
        *,
        height: int,
        width: int,
        eps: float,
    ) -> None:
        super().__init__()
        if channels % groups != 0:
            raise ValueError("channels must be divisible by groups")
        self.groups = groups
        self.channels = channels
        self.height = height
        self.width = width
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(channels))
        self.bias = nn.Parameter(torch.zeros(channels))

    @classmethod
    def from_group_norm(
        cls, module: nn.GroupNorm, *, height: int, width: int
    ) -> "FixedGroupNorm":
        if not module.affine:
            raise ValueError("non-affine GroupNorm is not supported by the policy exporter")
        replacement = cls(
            module.num_groups,
            module.num_channels,
            height=height,
            width=width,
            eps=module.eps,
        )
        replacement.weight.data.copy_(module.weight.detach())
        replacement.bias.data.copy_(module.bias.detach())
        return replacement

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        grouped = inputs.reshape(
            1,
            self.groups,
            self.channels // self.groups,
            self.height,
            self.width,
        )
        mean = grouped.mean(dim=(2, 3, 4), keepdim=True)
        centered = grouped - mean
        variance = (centered * centered).mean(dim=(2, 3, 4), keepdim=True)
        normalized = centered / torch.sqrt(variance + self.eps)
        normalized = normalized.reshape(1, self.channels, self.height, self.width)
        return normalized * self.weight.reshape(1, self.channels, 1, 1) + self.bias.reshape(
            1, self.channels, 1, 1
        )


def make_esp_compatible(model: RecurrentActorCritic) -> RecurrentActorCritic:
    converted = deepcopy(model).cpu().eval()

    def replace(module: nn.Module) -> None:
        for name, child in list(module.named_children()):
            if isinstance(child, nn.GroupNorm):
                setattr(
                    module,
                    name,
                    FixedGroupNorm.from_group_norm(child, height=5, width=5),
                )
            else:
                replace(child)

    replace(converted)
    return converted


class EmbeddedPolicyStep(nn.Module):
    def __init__(self, model: RecurrentActorCritic) -> None:
        super().__init__()
        self.model = model

    def forward(
        self,
        spatial: torch.Tensor,
        scalar: torch.Tensor,
        hidden: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        output = self.model(
            spatial.unsqueeze(1),
            scalar.unsqueeze(1),
            hidden=hidden,
        )
        return output.logits[:, 0], output.values[:, 0], output.hidden


def export_onnx(wrapper: EmbeddedPolicyStep, destination: str | Path) -> Path:
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
        output_names=("logits", "value", "next_hidden"),
        opset_version=18,
        do_constant_folding=True,
        dynamo=False,
    )
    return output


def validate_onnx(
    wrapper: EmbeddedPolicyStep,
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
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    generator = torch.Generator().manual_seed(seed)
    maximum = {"logits": 0.0, "value": 0.0, "hidden": 0.0}
    wrapper = wrapper.cpu().eval()
    for _ in range(trials):
        spatial = torch.randint(0, 2, (1, 13, 5, 5), generator=generator).float()
        scalar = torch.rand((1, 46), generator=generator)
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
            maximum["logits"], float(np.max(np.abs(expected[0].numpy() - actual[0])))
        )
        maximum["value"] = max(
            maximum["value"], float(np.max(np.abs(expected[1].numpy() - actual[1])))
        )
        maximum["hidden"] = max(
            maximum["hidden"], float(np.max(np.abs(expected[2].numpy() - actual[2])))
        )
    return {
        "operators": operators,
        "unsupported_operators": unsupported,
        "max_logit_error": maximum["logits"],
        "max_value_error": maximum["value"],
        "max_hidden_error": maximum["hidden"],
        "onnx_bytes": path.stat().st_size,
        "onnx_sha256": sha256(path.read_bytes()).hexdigest(),
    }


def load_production_model(checkpoint: str | Path) -> RecurrentActorCritic:
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model = RecurrentActorCritic()
    model.load_state_dict(payload["model"])
    return model.eval()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report")
    parser.add_argument("--trials", type=int, default=128)
    arguments = parser.parse_args()
    model = load_production_model(arguments.checkpoint)
    wrapper = EmbeddedPolicyStep(make_esp_compatible(model)).eval()
    output = export_onnx(wrapper, arguments.output)
    report = validate_onnx(wrapper, output, trials=arguments.trials, seed=20261114)
    report["checkpoint"] = str(arguments.checkpoint)
    report_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.report:
        Path(arguments.report).write_text(report_text, encoding="utf-8")
    print(report_text, end="")


if __name__ == "__main__":
    main()
