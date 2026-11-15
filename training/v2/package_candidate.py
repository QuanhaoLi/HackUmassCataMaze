# Created at: 2026-11-14 19:41 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:41 EST
# Last Modified by: Codex
# Emits a checksummed V2 model handoff only after every model-side gate passes.

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
from typing import Any

import torch

from training.v2 import MODEL_ARCH_VERSION
from training.v2.config import load_config
from training.v2.migrate import file_sha256


CANDIDATE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]+$")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def package_candidate(
    *,
    candidate_id: str,
    output_dir: Path,
    checkpoint: Path,
    onnx: Path,
    espdl: Path,
    config: Path,
    training_metrics: Path,
    evaluation_summary: Path,
    evaluation_episodes: Path,
    v1_evaluation: Path,
    ablations: Path,
    quantization_report: Path,
    operator_report: Path,
) -> dict[str, Any]:
    if not CANDIDATE_PATTERN.fullmatch(candidate_id):
        raise ValueError("candidate_id must be a lowercase stable identifier")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"candidate output is non-empty: {output_dir}")
    resolved_config = load_config(config)
    evaluation = _load_json(evaluation_summary)
    quantization = _load_json(quantization_report)
    operators = _load_json(operator_report)
    ablation_report = _load_json(ablations)
    if evaluation.get("release_gate_passed") is not True:
        raise ValueError("V2 evaluation release gate did not pass")
    if quantization.get("passes_persona_gate") is not True:
        raise ValueError("V2 per-persona quantization gate did not pass")
    if float(quantization.get("minimum_persona_action_agreement", 0.0)) < 0.99:
        raise ValueError("V2 minimum persona action agreement is below 99%")
    if operators.get("unsupported_operators") != []:
        raise ValueError("V2 actor-only ONNX contains unsupported operators")
    if float(operators.get("max_logit_error", 1.0)) > 1e-5:
        raise ValueError("V2 ONNX logit parity failed")
    if float(operators.get("max_hidden_error", 1.0)) > 1e-5:
        raise ValueError("V2 ONNX hidden parity failed")
    if ablation_report.get("complete_model_selected") is not True:
        raise ValueError("V2 ablation report did not select the complete model")
    if espdl.stat().st_size > int(
        resolved_config["embedded_budgets"]["maximum_espdl_bytes"]
    ):
        raise ValueError("V2 ESP-DL artifact exceeds its size budget")
    checkpoint_payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    if "model" not in checkpoint_payload:
        raise ValueError("V2 checkpoint is missing model state")
    parameter_count = sum(tensor.numel() for tensor in checkpoint_payload["model"].values())
    if parameter_count > int(resolved_config["model"]["maximum_parameters"]):
        raise ValueError("V2 checkpoint exceeds its parameter budget")

    output_dir.mkdir(parents=True, exist_ok=True)
    sources = {
        "checkpoint.pt": checkpoint,
        "model_fp32.onnx": onnx,
        "model_w8a16.espdl": espdl,
        "training_config.yaml": config,
        "training_metrics.jsonl": training_metrics,
        "evaluation_summary.json": evaluation_summary,
        "evaluation_episodes.jsonl": evaluation_episodes,
        "v1_evaluation.json": v1_evaluation,
        "ablations.json": ablations,
        "quantization_report.json": quantization_report,
        "operator_report.json": operator_report,
    }
    for name, source in sources.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, output_dir / name)
    artifact_hashes = {
        name: file_sha256(output_dir / name) for name in sorted(sources)
    }
    manifest = {
        "schema": "catamaze.policy.persona.v2-candidate",
        "candidate_id": candidate_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_arch": MODEL_ARCH_VERSION,
        "parameter_count": parameter_count,
        "lineage": resolved_config["lineage"],
        "versions": resolved_config["versions"],
        "training_steps": checkpoint_payload.get("training_state", {}).get(
            "agent_steps"
        ),
        "quantization": {
            "type": quantization["quant_type"],
            "minimum_persona_action_agreement": quantization[
                "minimum_persona_action_agreement"
            ],
            "espdl_bytes": quantization["espdl_bytes"],
        },
        "evaluation_release_gate": evaluation["release_gate_passed"],
        "artifacts": artifact_hashes,
        "deployment_authorized": False,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "HANDOFF.md").write_text(
        "# V2 model candidate handoff\n\n"
        f"Candidate: `{candidate_id}`\n\n"
        "The model team stops here. This bundle does not authorize firmware changes, "
        "PlatformIO default changes, physical upload, or V1 replacement. The deployment "
        "owner must follow docs/v2/persona-policy-plan.md Deploy 1–9 and obtain explicit "
        "product-owner promotion approval.\n",
        encoding="utf-8",
    )
    checksum_files = [
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.name != "checksums.sha256"
    ]
    (output_dir / "checksums.sha256").write_text(
        "".join(
            f"{file_sha256(path)}  {path.name}\n"
            for path in sorted(checksum_files, key=lambda item: item.name)
        ),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", required=True)
    for name in (
        "checkpoint",
        "onnx",
        "espdl",
        "config",
        "training-metrics",
        "evaluation-summary",
        "evaluation-episodes",
        "v1-evaluation",
        "ablations",
        "quantization-report",
        "operator-report",
    ):
        parser.add_argument(f"--{name}", required=True)
    arguments = parser.parse_args()
    manifest = package_candidate(
        candidate_id=arguments.candidate_id,
        output_dir=Path(arguments.output),
        checkpoint=Path(arguments.checkpoint),
        onnx=Path(arguments.onnx),
        espdl=Path(arguments.espdl),
        config=Path(arguments.config),
        training_metrics=Path(arguments.training_metrics),
        evaluation_summary=Path(arguments.evaluation_summary),
        evaluation_episodes=Path(arguments.evaluation_episodes),
        v1_evaluation=Path(arguments.v1_evaluation),
        ablations=Path(arguments.ablations),
        quantization_report=Path(arguments.quantization_report),
        operator_report=Path(arguments.operator_report),
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
