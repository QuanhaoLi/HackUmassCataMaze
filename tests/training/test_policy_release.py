# Created at: 2026-11-14 18:51 EST
# Created by: Codex
# Last Modified at: 2026-11-14 18:51 EST
# Last Modified by: Codex
# Verifies the single released-model manifest, artifact, evidence, tensor contract, and C++ output.

from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_DIR / "src/esp32/model/policy_release.json"
ARTIFACT_PATH = PROJECT_DIR / "src/esp32/model/catamaze_policy.espdl"
HEADER_PATH = PROJECT_DIR / "src/esp32/policy_release.hpp"


def load_generator():
    path = PROJECT_DIR / "scripts/generate_policy_release.py"
    spec = importlib.util.spec_from_file_location("generate_policy_release", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_manifest_is_complete_and_matches_artifact() -> None:
    release = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    artifact = ARTIFACT_PATH.read_bytes()
    assert release["schema"] == "catamaze.policy.release.v1"
    assert release["target"] == "esp32s3"
    assert release["quantization"] == "w8a16"
    assert release["artifact_bytes"] == len(artifact) == 1_490_800
    assert release["artifact_sha256"] == sha256(artifact).hexdigest()
    assert release["inputs"] == {
        "spatial": [1, 13, 5, 5],
        "scalar": [1, 46],
        "hidden": [1, 1, 256],
    }
    assert release["outputs"] == {
        "logits": [1, 9],
        "value": [1],
        "next_hidden": [1, 1, 256],
    }


def test_release_evidence_passes_declared_gates_and_compatibility_is_explicit() -> None:
    release = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    evidence = release["evidence"]
    gates = release["gates"]
    assert evidence["calibration_samples"] == 512
    assert evidence["evaluation_samples"] == 10_000
    assert evidence["masked_action_agreement"] >= gates["minimum_masked_action_agreement"]
    assert release["exporter_version"] == "3.3.15"
    assert release["runtime_version"] == "3.3.11"
    assert release["runtime_compatibility"] == "decoded-envelope-v1"
    assert gates == {
        "minimum_masked_action_agreement": 0.985,
        "maximum_logit_error": 0.1,
        "maximum_value_error": 0.5,
        "maximum_hidden_error": 0.18,
        "maximum_three_agent_us": 900_000,
    }


def test_generated_cpp_release_authority_is_current() -> None:
    generator = load_generator()
    release = generator.load_release(MANIFEST_PATH)
    assert HEADER_PATH.read_text(encoding="utf-8") == generator.render_header(release)
