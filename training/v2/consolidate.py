# Created at: 2026-11-14 19:41 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:41 EST
# Last Modified by: Codex
# Consolidates isolated V2 phases into one cumulative model checkpoint and lineage.

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import torch

from training.v2.checkpoint import CHECKPOINT_FORMAT_VERSION
from training.v2.migrate import file_sha256


def consolidate(
    phases: list[tuple[str, Path]], destination: Path
) -> dict[str, Any]:
    if [name for name, _path in phases] != ["heads-only", "recurrent", "full"]:
        raise ValueError("V2 consolidation requires heads-only, recurrent, and full phases")
    loaded: list[tuple[str, Path, dict[str, Any]]] = []
    for name, path in phases:
        payload = torch.load(path, map_location="cpu", weights_only=False)
        if payload.get("format") != CHECKPOINT_FORMAT_VERSION:
            raise ValueError(f"{name} is not a V2 checkpoint")
        if payload["training_state"].get("phase") != name:
            raise ValueError(f"{name} checkpoint phase metadata does not match")
        loaded.append((name, path, payload))
    final = deepcopy(loaded[-1][2])
    phase_history = [
        {
            "phase": name,
            "agent_steps": int(payload["training_state"]["agent_steps"]),
            "checkpoint_name": path.name,
            "checkpoint_sha256": file_sha256(path),
        }
        for name, path, payload in loaded
    ]
    cumulative = sum(int(item["agent_steps"]) for item in phase_history)
    final["format"] = "catamaze.checkpoint.persona.candidate.v2"
    final["training_state"] = {
        "agent_steps": cumulative,
        "final_phase": "full",
        "phase_history": phase_history,
    }
    final["resolved_config"] = {
        **final.get("resolved_config", {}),
        "cumulative_agent_steps": cumulative,
        "phase_history": phase_history,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        torch.save(final, temporary_path)
        with temporary_path.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return {
        "format": final["format"],
        "cumulative_agent_steps": cumulative,
        "phase_history": phase_history,
        "output": str(destination),
        "output_sha256": file_sha256(destination),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--heads", required=True)
    parser.add_argument("--recurrent", required=True)
    parser.add_argument("--full", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    arguments = parser.parse_args()
    report = consolidate(
        [
            ("heads-only", Path(arguments.heads)),
            ("recurrent", Path(arguments.recurrent)),
            ("full", Path(arguments.full)),
        ],
        Path(arguments.output),
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    Path(arguments.report).write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
