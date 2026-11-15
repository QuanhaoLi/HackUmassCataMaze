# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:04 EST
# Last Modified by: Codex
# Creates a hash-verified, numerically equivalent V2 warm-start from a frozen V1 checkpoint.

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import torch

from training.model import RecurrentActorCritic
from training.v2 import MODEL_ARCH_VERSION
from training.v2.model import PersonaRecurrentActorCritic


MIGRATION_FORMAT = "catamaze.persona-warmstart.v2"
EXPECTED_V1_FORMAT = "catamaze.ddp-training.v1"


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def equivalence_report(
    baseline: RecurrentActorCritic,
    candidate: PersonaRecurrentActorCritic,
) -> dict[str, float]:
    generator = torch.Generator().manual_seed(20261114)
    spatial = torch.rand((3, 8, 13, 5, 5), generator=generator)
    scalar = torch.rand((3, 8, 46), generator=generator)
    scalar[..., 43:46] = 0.0
    for persona in range(3):
        scalar[persona, :, 43 + persona] = 1.0
    hidden = torch.randn((1, 3, 256), generator=generator) * 0.1
    starts = torch.zeros((3, 8), dtype=torch.bool)
    starts[:, 0] = True
    baseline.eval()
    candidate.eval()
    with torch.no_grad():
        expected = baseline(spatial, scalar, hidden=hidden, episode_starts=starts)
        actual = candidate(spatial, scalar, hidden=hidden, episode_starts=starts)
    return {
        "max_logit_error": float((actual.logits - expected.logits).abs().max()),
        "max_value_error": float((actual.values - expected.values).abs().max()),
        "max_hidden_error": float((actual.hidden - expected.hidden).abs().max()),
        "max_all_head_logit_error": max(
            float((actual.logits_all[:, :, persona] - expected.logits).abs().max())
            for persona in range(3)
        ),
        "max_all_head_value_error": max(
            float((actual.values_all[:, :, persona] - expected.values).abs().max())
            for persona in range(3)
        ),
    }


def migrate_checkpoint(
    source: str | Path,
    destination: str | Path,
    *,
    expected_sha256: str,
    source_product_commit: str,
    provisional: bool = False,
) -> dict[str, Any]:
    source_path = Path(source)
    actual_sha256 = file_sha256(source_path)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"V1 checkpoint SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    payload = torch.load(source_path, map_location="cpu", weights_only=False)
    if payload.get("format") != EXPECTED_V1_FORMAT:
        raise ValueError("source is not a production V1 DDP checkpoint")
    baseline = RecurrentActorCritic().eval()
    baseline.load_state_dict(payload["model"])
    candidate = PersonaRecurrentActorCritic.from_v1(baseline).eval()
    equivalence = equivalence_report(baseline, candidate)
    if max(equivalence.values()) > 1e-6:
        raise RuntimeError(f"V1 to V2 migration is not equivalent: {equivalence}")
    result = {
        "format": MIGRATION_FORMAT,
        "model_arch": MODEL_ARCH_VERSION,
        "model": candidate.state_dict(),
        "lineage": {
            "source_checkpoint_name": source_path.name,
            "source_checkpoint_sha256": actual_sha256,
            "source_checkpoint_format": payload["format"],
            "source_product_commit": source_product_commit,
            "source_world_size": int(payload.get("world_size", 0)),
            "source_agent_steps": int(payload["training_state"]["agent_steps"]),
            "source_versions": payload["config"]["versions"],
            "provisional": provisional,
        },
        "migration": {
            **equivalence,
            "persona_gamma_nonzero": int(torch.count_nonzero(candidate.persona_gamma)),
            "persona_beta_nonzero": int(torch.count_nonzero(candidate.persona_beta)),
        },
    }
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination_path.name}.",
            suffix=".tmp",
            dir=destination_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        torch.save(result, temporary_path)
        with temporary_path.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary_path, destination_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    report = {
        "output": str(destination_path),
        "output_sha256": file_sha256(destination_path),
        "parameter_count": sum(parameter.numel() for parameter in candidate.parameters()),
        "lineage": result["lineage"],
        "migration": result["migration"],
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--source-product-commit", required=True)
    parser.add_argument("--provisional", action="store_true")
    parser.add_argument("--report")
    arguments = parser.parse_args()
    report = migrate_checkpoint(
        arguments.source,
        arguments.output,
        expected_sha256=arguments.expected_sha256,
        source_product_commit=arguments.source_product_commit,
        provisional=arguments.provisional,
    )
    report_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.report:
        Path(arguments.report).write_text(report_text, encoding="utf-8")
    print(report_text, end="")


if __name__ == "__main__":
    main()
