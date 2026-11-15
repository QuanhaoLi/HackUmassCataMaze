#!/usr/bin/env python3
# Created at: 2026-11-14 18:51 EST
# Created by: Codex
# Last Modified at: 2026-11-14 18:51 EST
# Last Modified by: Codex
# Validates one released ESP-DL artifact and deterministically renders its C++ authority.

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_DIR / "src/esp32/model/policy_release.json"
DEFAULT_OUTPUT = PROJECT_DIR / "src/esp32/policy_release.hpp"


def load_release(path: Path) -> dict[str, Any]:
    release = json.loads(path.read_text(encoding="utf-8"))
    if release.get("schema") != "catamaze.policy.release.v1":
        raise ValueError("unsupported policy release schema")
    artifact = path.parent / str(release["artifact"])
    payload = artifact.read_bytes()
    if len(payload) != int(release["artifact_bytes"]):
        raise ValueError("policy artifact byte count does not match manifest")
    if sha256(payload).hexdigest() != release["artifact_sha256"]:
        raise ValueError("policy artifact SHA-256 does not match manifest")
    if release["target"] != "esp32s3" or release["quantization"] != "w8a16":
        raise ValueError("unsupported target or quantization")
    if release["runtime_compatibility"] != "decoded-envelope-v1":
        raise ValueError("unreviewed exporter/runtime compatibility mode")
    if float(release["evidence"]["masked_action_agreement"]) < float(
        release["gates"]["minimum_masked_action_agreement"]
    ):
        raise ValueError("masked action agreement is below its release gate")
    return release


def cpp_shape(name: str, values: list[int]) -> str:
    joined = ", ".join(f"{int(value)}U" for value in values)
    return (
        f"inline constexpr std::array<std::size_t, {len(values)}U> "
        f"{name}{{{joined}}};"
    )


def render_header(release: dict[str, Any]) -> str:
    evidence = release["evidence"]
    gates = release["gates"]
    metadata = release["generated_header"]
    lines = [
        f"// Created at: {metadata['created_at']}",
        "// Created by: Codex",
        f"// Last Modified at: {metadata['modified_at']}",
        "// Last Modified by: Codex",
        "// Generated from model/policy_release.json; do not hand-edit release values.",
        "",
        "#pragma once",
        "",
        "#include <array>",
        "#include <cstddef>",
        "#include <cstdint>",
        "#include <string_view>",
        "",
        "namespace catamaze::esp32::policy_release {",
        "",
        f'inline constexpr std::string_view kSchema{{"{release["schema"]}"}};',
        f'inline constexpr std::string_view kRelease{{"{release["release"]}"}};',
        f'inline constexpr std::string_view kArtifact{{"{release["artifact"]}"}};',
        f'inline constexpr std::string_view kArtifactSha256{{"{release["artifact_sha256"]}"}};',
        f"inline constexpr std::size_t kArtifactBytes = {int(release['artifact_bytes'])}U;",
        f"inline constexpr std::size_t kParameters = {int(release['parameters'])}U;",
        f'inline constexpr std::string_view kTarget{{"{release["target"]}"}};',
        f'inline constexpr std::string_view kQuantization{{"{release["quantization"]}"}};',
        f'inline constexpr std::string_view kExporterVersion{{"{release["exporter_version"]}"}};',
        f'inline constexpr std::string_view kRuntimeVersion{{"{release["runtime_version"]}"}};',
        f'inline constexpr std::string_view kRuntimeCompatibility{{"{release["runtime_compatibility"]}"}};',
        cpp_shape("kSpatialShape", release["inputs"]["spatial"]),
        cpp_shape("kScalarShape", release["inputs"]["scalar"]),
        cpp_shape("kHiddenShape", release["inputs"]["hidden"]),
        cpp_shape("kLogitsShape", release["outputs"]["logits"]),
        cpp_shape("kValueShape", release["outputs"]["value"]),
        cpp_shape("kNextHiddenShape", release["outputs"]["next_hidden"]),
        f"inline constexpr std::size_t kCalibrationSamples = {int(evidence['calibration_samples'])}U;",
        f"inline constexpr std::size_t kEvaluationSamples = {int(evidence['evaluation_samples'])}U;",
        f"inline constexpr float kMaskedActionAgreement = {float(evidence['masked_action_agreement']):.6f}F;",
        f"inline constexpr float kMinimumMaskedActionAgreement = {float(gates['minimum_masked_action_agreement']):.6f}F;",
        f"inline constexpr float kMaximumLogitError = {float(gates['maximum_logit_error']):.6f}F;",
        f"inline constexpr float kMaximumValueError = {float(gates['maximum_value_error']):.6f}F;",
        f"inline constexpr float kMaximumHiddenError = {float(gates['maximum_hidden_error']):.6f}F;",
        f"inline constexpr std::uint32_t kMaximumThreeAgentUs = {int(gates['maximum_three_agent_us'])}U;",
        f"inline constexpr std::uint32_t kPhysicalThreeInferenceUs = {int(evidence['physical_three_inference_us'])}U;",
        f"inline constexpr std::uint32_t kPhysicalInternalBytes = {int(evidence['physical_internal_bytes'])}U;",
        f"inline constexpr std::uint32_t kPhysicalPsramBytes = {int(evidence['physical_psram_bytes'])}U;",
        "",
        '}  // namespace catamaze::esp32::policy_release',
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    release = load_release(arguments.manifest.resolve())
    expected = render_header(release)
    output = arguments.output.resolve()
    if arguments.check:
        if not output.exists() or output.read_text(encoding="utf-8") != expected:
            print("generated policy release header is stale", file=sys.stderr)
            return 1
        print(f"POLICY_RELEASE_OK release={release['release']} sha256={release['artifact_sha256']}")
        return 0
    output.write_text(expected, encoding="utf-8")
    print(f"POLICY_RELEASE_WRITTEN path={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
