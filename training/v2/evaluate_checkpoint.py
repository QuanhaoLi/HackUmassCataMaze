# Created at: 2026-11-14 19:26 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:26 EST
# Last Modified by: Codex
# Runs fixed-seed V2 checkpoint evaluation without touching the V1 evaluator CLI.

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from training.evaluator import evaluate_policy
from training.opponents import OpponentStrategy
from training.v2.evaluator import assess_persona_gates
from training.v2.export_esp import load_v2_model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--episodes", type=int, default=300)
    parser.add_argument("--num-envs", type=int, default=64)
    parser.add_argument("--mode", choices=("stochastic", "deterministic"), default="stochastic")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--seed", type=int, default=20261114)
    parser.add_argument(
        "--opponents",
        nargs="+",
        choices=[opponent.name.lower() for opponent in OpponentStrategy],
        required=True,
    )
    arguments = parser.parse_args()
    if arguments.episodes <= 0:
        raise ValueError("episodes must be positive")
    device = torch.device(arguments.device)
    model = load_v2_model(arguments.checkpoint).to(device).eval()
    reports: dict[str, object] = {}
    for name in arguments.opponents:
        opponent = OpponentStrategy[name.upper()]
        report = evaluate_policy(
            model,
            episodes=arguments.episodes,
            opponent=opponent,
            mode=arguments.mode,
            seed=arguments.seed + int(opponent) * 10_000,
            num_envs=min(arguments.num_envs, arguments.episodes),
            device=device,
        )
        reports[name] = {
            "evaluation": report,
            "persona_assessment": assess_persona_gates(report),
        }
    result = {
        "schema": "catamaze.evaluation.persona.v2",
        "checkpoint": arguments.checkpoint,
        "episodes_per_opponent": arguments.episodes,
        "mode": arguments.mode,
        "reports": reports,
    }
    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
