# Created at: 2026-11-14 19:41 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:41 EST
# Last Modified by: Codex
# Verifies cumulative V2 phase lineage preserves the final model exactly.

from __future__ import annotations

from pathlib import Path

import torch

from training.v2.checkpoint import CHECKPOINT_FORMAT_VERSION
from training.v2.consolidate import consolidate
from training.v2.model import PersonaRecurrentActorCritic


def write_phase(path: Path, phase: str, steps: int, fill: float) -> None:
    model = PersonaRecurrentActorCritic()
    with torch.no_grad():
        model.persona_beta.fill_(fill)
    torch.save(
        {
            "format": CHECKPOINT_FORMAT_VERSION,
            "contracts": {
                "reward": (
                    "catamaze.reward.persona.v3"
                    if phase == "full"
                    else "catamaze.reward.v2"
                )
            },
            "model": model.state_dict(),
            "optimizer": {},
            "training_state": {"phase": phase, "agent_steps": steps},
            "resolved_config": {"source_lineage": {"provisional": False}},
        },
        path,
    )


def test_consolidation_sums_steps_and_preserves_final_model(tmp_path: Path) -> None:
    paths = []
    for name, steps, fill in (
        ("heads-only", 5, 0.1),
        ("recurrent", 5, 0.2),
        ("full", 15, 0.3),
    ):
        path = tmp_path / f"{name}.pt"
        write_phase(path, name, steps, fill)
        paths.append((name, path))
    output = tmp_path / "candidate.pt"
    report = consolidate(paths, output)
    candidate = torch.load(output, map_location="cpu", weights_only=False)
    final = torch.load(paths[-1][1], map_location="cpu", weights_only=False)
    assert report["cumulative_agent_steps"] == 25
    assert candidate["training_state"]["agent_steps"] == 25
    assert [
        item["reward_version"] for item in candidate["training_state"]["phase_history"]
    ] == ["catamaze.reward.v2", "catamaze.reward.v2", "catamaze.reward.persona.v3"]
    for name, tensor in final["model"].items():
        torch.testing.assert_close(candidate["model"][name], tensor, rtol=0.0, atol=0.0)
