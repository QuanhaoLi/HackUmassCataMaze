# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:04 EST
# Last Modified by: Codex
# Quantizes V2 with disjoint balanced recurrent samples and per-persona release gates.

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import torch

from training.collector import RolloutCollector
from training.env import CataMazeBatchEnv
from training.export_esp import make_esp_compatible
from training.v2.export_esp import EmbeddedPersonaPolicyStep, load_v2_model
from training.v2.model import PERSONA_COUNT


Sample = list[torch.Tensor]
PersonaSample = tuple[Sample, torch.Tensor]


def collect_persona_samples(
    model: torch.nn.Module,
    *,
    count_per_persona: int,
    environment_steps: int,
    num_envs: int,
    seed: int,
    device: torch.device,
) -> list[list[PersonaSample]]:
    if count_per_persona <= 0 or environment_steps <= 0 or num_envs <= 0:
        raise ValueError("V2 sample dimensions must be positive")
    environment = CataMazeBatchEnv(num_envs, seed, curriculum_stage="D")
    collector = RolloutCollector(environment, model, device=device)
    generator = torch.Generator(device=device.type).manual_seed(seed)
    samples: list[list[PersonaSample]] = [[] for _ in range(PERSONA_COUNT)]
    while min(len(items) for items in samples) < count_per_persona:
        rollout, _metrics = collector.collect(
            environment_steps,
            gamma=0.995,
            gae_lambda=0.95,
            generator=generator,
        )
        active_indices = torch.nonzero(rollout.active, as_tuple=False)
        for selected in active_indices:
            step, batch_agent = int(selected[0]), int(selected[1])
            persona = batch_agent % PERSONA_COUNT
            if len(samples[persona]) >= count_per_persona:
                continue
            inputs = [
                rollout.spatial[step, batch_agent].unsqueeze(0).float().contiguous(),
                rollout.scalar[step, batch_agent].unsqueeze(0).float().contiguous(),
                rollout.hidden[step, batch_agent]
                .reshape(1, 1, 256)
                .float()
                .contiguous(),
            ]
            mask = (
                rollout.action_mask[step, batch_agent]
                .unsqueeze(0)
                .bool()
                .contiguous()
            )
            samples[persona].append((inputs, mask))
        if not active_indices.numel():
            raise RuntimeError("V2 rollout produced no active quantization samples")
    return samples


def quantize(
    *,
    checkpoint: Path,
    onnx_path: Path,
    espdl_path: Path,
    calibration_path: Path,
    report_path: Path,
    calibration_per_persona: int,
    evaluation_per_persona: int,
    quant_type: str,
    device: torch.device,
) -> dict[str, Any]:
    from esp_ppq import TorchExecutor
    from esp_ppq.api import espdl_quantize_onnx

    model = load_v2_model(checkpoint).to(device).eval()
    collected = collect_persona_samples(
        model,
        count_per_persona=calibration_per_persona + evaluation_per_persona,
        environment_steps=128,
        num_envs=64,
        seed=20261114,
        device=device,
    )
    calibration: list[Sample] = []
    evaluation: list[list[PersonaSample]] = []
    for persona in range(PERSONA_COUNT):
        evaluation.append(collected[persona][calibration_per_persona:])
    for index in range(calibration_per_persona):
        for persona in range(PERSONA_COUNT):
            calibration.append(collected[persona][index][0])
    calibration_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(calibration, calibration_path)

    def collate(batch: Sample) -> Sample:
        return [tensor.to(device=device, dtype=torch.float32) for tensor in batch]

    graph = espdl_quantize_onnx(
        onnx_import_file=str(onnx_path),
        espdl_export_file=str(espdl_path),
        calib_dataloader=calibration,
        calib_steps=len(calibration),
        input_shape=[[1, 13, 5, 5], [1, 46], [1, 1, 256]],
        inputs=calibration[0],
        target="esp32s3",
        quant_type=quant_type,
        collate_fn=collate,
        device=str(device),
        error_report=True,
        export_config=True,
        export_test_values=True,
        verbose=1,
        metadata_props={
            "environment_version": "catamaze.environment.v1",
            "observation_version": "catamaze.observation.v1",
            "model_arch_version": "catamaze.model.persona-rppo.v2",
            "export_contract": "catamaze.esp-step.persona.v2",
            "target": "esp32s3",
        },
    )
    executor = TorchExecutor(graph=graph, device=str(device))
    wrapper = EmbeddedPersonaPolicyStep(
        make_esp_compatible(load_v2_model(checkpoint))
    ).to(device).eval()
    persona_reports: list[dict[str, Any]] = []
    for persona in range(PERSONA_COUNT):
        matches = 0
        maximum_logit_error = 0.0
        maximum_hidden_error = 0.0
        for sample, action_mask in evaluation[persona]:
            inputs = collate(sample)
            with torch.no_grad():
                expected_logits_all, expected_hidden = wrapper(*inputs)
                actual_logits_all, actual_hidden = executor.forward(inputs=inputs)
            expected_logits = expected_logits_all[:, persona]
            actual_logits = actual_logits_all[:, persona]
            maximum_logit_error = max(
                maximum_logit_error,
                float((expected_logits - actual_logits).abs().max().cpu()),
            )
            maximum_hidden_error = max(
                maximum_hidden_error,
                float((expected_hidden - actual_hidden).abs().max().cpu()),
            )
            mask = action_mask.to(device)
            expected_action = expected_logits.masked_fill(~mask, -torch.inf).argmax(dim=-1)
            actual_action = actual_logits.masked_fill(~mask, -torch.inf).argmax(dim=-1)
            matches += int(expected_action.item() == actual_action.item())
        count = len(evaluation[persona])
        persona_reports.append(
            {
                "persona": persona,
                "evaluation_samples": count,
                "masked_action_agreement": matches / count,
                "max_logit_error": maximum_logit_error,
                "max_hidden_error": maximum_hidden_error,
            }
        )
    minimum_agreement = min(
        float(report["masked_action_agreement"]) for report in persona_reports
    )
    report = {
        "quant_type": quant_type,
        "target": "esp32s3",
        "calibration_per_persona": calibration_per_persona,
        "calibration_samples": len(calibration),
        "evaluation_per_persona": evaluation_per_persona,
        "evaluation_samples": evaluation_per_persona * PERSONA_COUNT,
        "personas": persona_reports,
        "minimum_persona_action_agreement": minimum_agreement,
        "passes_persona_gate": minimum_agreement >= 0.99,
        "espdl_bytes": espdl_path.stat().st_size,
        "espdl_sha256": sha256(espdl_path.read_bytes()).hexdigest(),
        "checkpoint": str(checkpoint),
        "onnx": str(onnx_path),
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--calibration", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--calibration-per-persona", type=int, default=512)
    parser.add_argument("--evaluation-per-persona", type=int, default=10_000)
    parser.add_argument(
        "--quant-type", choices=("w8a8", "w8a16", "w16a16"), default="w8a16"
    )
    parser.add_argument("--device", default="cpu")
    arguments = parser.parse_args()
    report = quantize(
        checkpoint=Path(arguments.checkpoint),
        onnx_path=Path(arguments.onnx),
        espdl_path=Path(arguments.output),
        calibration_path=Path(arguments.calibration),
        report_path=Path(arguments.report),
        calibration_per_persona=arguments.calibration_per_persona,
        evaluation_per_persona=arguments.evaluation_per_persona,
        quant_type=arguments.quant_type,
        device=torch.device(arguments.device),
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
