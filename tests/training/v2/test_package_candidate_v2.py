# Created at: 2026-11-14 19:41 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:41 EST
# Last Modified by: Codex
# Verifies V2 handoff creation is gated, immutable, and explicitly non-deploying.

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from training.v2.model import PersonaRecurrentActorCritic
from training.v2.package_candidate import package_candidate


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def inputs(tmp_path: Path) -> dict[str, Path]:
    checkpoint = tmp_path / "source.pt"
    torch.save(
        {
            "model": PersonaRecurrentActorCritic().state_dict(),
            "training_state": {"agent_steps": 25_000_000},
        },
        checkpoint,
    )
    files = {
        "checkpoint": checkpoint,
        "onnx": tmp_path / "source.onnx",
        "espdl": tmp_path / "source.espdl",
        "config": Path("configs/rl/v2/persona_v2.yaml"),
        "training_metrics": tmp_path / "metrics.jsonl",
        "evaluation_summary": tmp_path / "evaluation.json",
        "evaluation_episodes": tmp_path / "episodes.jsonl",
        "v1_evaluation": tmp_path / "v1.json",
        "ablations": tmp_path / "ablations.json",
        "quantization_report": tmp_path / "quantization.json",
        "operator_report": tmp_path / "operators.json",
    }
    for name in ("onnx", "espdl", "training_metrics", "evaluation_episodes"):
        files[name].write_bytes(b"test-artifact")
    write_json(files["evaluation_summary"], {"release_gate_passed": True})
    write_json(files["v1_evaluation"], {"schema": "v1"})
    write_json(files["ablations"], {"complete_model_selected": True})
    write_json(
        files["quantization_report"],
        {
            "passes_persona_gate": True,
            "minimum_persona_action_agreement": 0.995,
            "quant_type": "w8a16",
            "espdl_bytes": len(b"test-artifact"),
        },
    )
    write_json(
        files["operator_report"],
        {
            "unsupported_operators": [],
            "max_logit_error": 1e-6,
            "max_hidden_error": 1e-6,
        },
    )
    return files


def test_passing_candidate_is_checksummed_and_stops_before_deployment(
    tmp_path: Path,
) -> None:
    arguments = inputs(tmp_path)
    output = tmp_path / "candidate"
    manifest = package_candidate(
        candidate_id="persona-v2-test",
        output_dir=output,
        **arguments,
    )
    assert manifest["deployment_authorized"] is False
    assert (output / "manifest.json").is_file()
    assert (output / "checksums.sha256").is_file()
    assert "does not authorize" in (output / "HANDOFF.md").read_text(encoding="utf-8")


def test_failed_persona_quantization_cannot_produce_a_candidate(tmp_path: Path) -> None:
    arguments = inputs(tmp_path)
    write_json(
        arguments["quantization_report"],
        {
            "passes_persona_gate": False,
            "minimum_persona_action_agreement": 0.98,
        },
    )
    with pytest.raises(ValueError, match="quantization gate"):
        package_candidate(
            candidate_id="persona-v2-test",
            output_dir=tmp_path / "candidate",
            **arguments,
        )
