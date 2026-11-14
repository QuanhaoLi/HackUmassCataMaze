# Created at: 2026-11-14 10:48 EST
# Created by: Codex
# Last Modified at: 2026-11-14 10:48 EST
# Last Modified by: Codex
# Quantizes the one-step ONNX policy for ESP32-S3 from real recurrent rollouts.

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from training.collector import RolloutCollector
from training.env import CataMazeBatchEnv
from training.export_esp import EmbeddedPolicyStep, load_production_model, make_esp_compatible


def collect_calibration_samples(
    model: torch.nn.Module,
    *,
    count: int,
    environment_steps: int,
    num_envs: int,
    seed: int,
    device: torch.device,
) -> list[list[torch.Tensor]]:
    if count <= 0 or environment_steps <= 0 or num_envs <= 0:
        raise ValueError("calibration dimensions must be positive")
    environment = CataMazeBatchEnv(num_envs, seed, curriculum_stage="D")
    collector = RolloutCollector(environment, model, device=device)
    generator = torch.Generator(device=device.type).manual_seed(seed)
    rollout, _metrics = collector.collect(
        environment_steps,
        gamma=0.995,
        gae_lambda=0.95,
        generator=generator,
    )
    active_indices = torch.nonzero(rollout.active, as_tuple=False)
    if active_indices.shape[0] < count:
        raise RuntimeError("rollout did not produce enough active calibration samples")
    choices = torch.linspace(0, active_indices.shape[0] - 1, steps=count).round().long()
    samples: list[list[torch.Tensor]] = []
    for selected in active_indices[choices]:
        step, agent = int(selected[0]), int(selected[1])
        samples.append(
            [
                rollout.spatial[step, agent].unsqueeze(0).float().contiguous(),
                rollout.scalar[step, agent].unsqueeze(0).float().contiguous(),
                rollout.hidden[step, agent].reshape(1, 1, 256).float().contiguous(),
            ]
        )
    return samples


def quantize(
    *,
    checkpoint: Path,
    onnx_path: Path,
    espdl_path: Path,
    calibration_path: Path,
    report_path: Path,
    calibration_count: int,
    device: torch.device,
) -> dict[str, Any]:
    from esp_ppq import TorchExecutor
    from esp_ppq.api import espdl_quantize_onnx

    model = load_production_model(checkpoint).to(device).eval()
    samples = collect_calibration_samples(
        model,
        count=calibration_count,
        environment_steps=64,
        num_envs=64,
        seed=20261114,
        device=device,
    )
    calibration_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(samples, calibration_path)

    def collate(batch: list[torch.Tensor]) -> list[torch.Tensor]:
        return [tensor.to(device=device, dtype=torch.float32) for tensor in batch]

    graph = espdl_quantize_onnx(
        onnx_import_file=str(onnx_path),
        espdl_export_file=str(espdl_path),
        calib_dataloader=samples,
        calib_steps=len(samples),
        input_shape=[[1, 13, 5, 5], [1, 46], [1, 1, 256]],
        inputs=samples[0],
        target="esp32s3",
        quant_type="w8a8",
        collate_fn=collate,
        device=str(device),
        error_report=True,
        export_config=True,
        export_test_values=True,
        verbose=1,
        metadata_props={
            "environment_version": "catamaze.environment.v1",
            "observation_version": "catamaze.observation.v1",
            "model_arch_version": "catamaze.model.rppo.v1",
            "target": "esp32s3",
        },
    )

    executor = TorchExecutor(graph=graph, device=str(device))
    wrapper = EmbeddedPolicyStep(make_esp_compatible(load_production_model(checkpoint))).to(
        device
    ).eval()
    maximum = {"logits": 0.0, "value": 0.0, "hidden": 0.0}
    action_matches = 0
    evaluated = min(256, len(samples))
    for sample in samples[:evaluated]:
        inputs = collate(sample)
        with torch.no_grad():
            expected = wrapper(*inputs)
            actual = executor.forward(inputs=inputs)
        maximum["logits"] = max(
            maximum["logits"], float((expected[0] - actual[0]).abs().max().cpu())
        )
        maximum["value"] = max(
            maximum["value"], float((expected[1] - actual[1]).abs().max().cpu())
        )
        maximum["hidden"] = max(
            maximum["hidden"], float((expected[2] - actual[2]).abs().max().cpu())
        )
        action_matches += int(expected[0].argmax(dim=-1).item() == actual[0].argmax(dim=-1).item())
    report = {
        "quant_type": "w8a8",
        "target": "esp32s3",
        "calibration_samples": len(samples),
        "evaluation_samples": evaluated,
        "max_logit_error": maximum["logits"],
        "max_value_error": maximum["value"],
        "max_hidden_error": maximum["hidden"],
        "unmasked_action_agreement": action_matches / evaluated,
        "espdl_bytes": espdl_path.stat().st_size,
        "checkpoint": str(checkpoint),
        "onnx": str(onnx_path),
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--calibration", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--calibration-count", type=int, default=512)
    parser.add_argument("--device", default="cpu")
    arguments = parser.parse_args()
    report = quantize(
        checkpoint=Path(arguments.checkpoint),
        onnx_path=Path(arguments.onnx),
        espdl_path=Path(arguments.output),
        calibration_path=Path(arguments.calibration),
        report_path=Path(arguments.report),
        calibration_count=arguments.calibration_count,
        device=torch.device(arguments.device),
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
