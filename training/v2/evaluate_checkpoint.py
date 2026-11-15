# Created at: 2026-11-14 19:26 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:41 EST
# Last Modified by: Codex
# Runs fixed-seed V2 checkpoint evaluation without touching the V1 evaluator CLI.

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from training.evaluator import evaluate_policy
from training.env import CataMazeBatchEnv
from training.opponents import OpponentStrategy
from training.v2.detailed_evaluator import evaluate_policy_detailed
from training.v2.evaluator import (
    assess_persona_gates,
    combine_opponent_reports,
    counterfactual_persona_divergence,
)
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
    parser.add_argument("--v1-evaluation")
    parser.add_argument("--episodes-output")
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
    v1_evaluation = None
    if arguments.v1_evaluation:
        v1_evaluation = json.loads(
            Path(arguments.v1_evaluation).read_text(encoding="utf-8")
        )
    reports: dict[str, object] = {}
    episode_records: list[dict[str, object]] = []
    for name in arguments.opponents:
        opponent = OpponentStrategy[name.upper()]
        evaluation_arguments = {
            "episodes": arguments.episodes,
            "opponent": opponent,
            "mode": arguments.mode,
            "seed": arguments.seed + int(opponent) * 10_000,
            "num_envs": min(arguments.num_envs, arguments.episodes),
            "device": device,
        }
        if arguments.episodes_output:
            report, raw_records = evaluate_policy_detailed(
                model, **evaluation_arguments
            )
            for record in raw_records:
                episode_records.append({"opponent": name, **record})
        else:
            report = evaluate_policy(model, **evaluation_arguments)
        reports[name] = {
            "evaluation": report,
            "persona_assessment": assess_persona_gates(
                report,
                v1_player_escape_rate=(
                    float(v1_evaluation[name]["player_escape_rate"])
                    if v1_evaluation is not None
                    else None
                ),
            ),
        }
    counterfactual_environment = CataMazeBatchEnv(
        min(arguments.num_envs, 64), arguments.seed + 999_999, curriculum_stage="D"
    )
    observation = counterfactual_environment.observation
    counterfactual = counterfactual_persona_divergence(
        model,
        torch.from_numpy(observation["spatial"]).reshape(-1, 13, 5, 5).to(device),
        torch.from_numpy(observation["scalar"]).reshape(-1, 46).to(device),
        torch.zeros(
            1, counterfactual_environment.num_envs * 3, 256, device=device
        ),
        torch.from_numpy(observation["action_mask"]).reshape(-1, 9).to(device),
    )
    combined = combine_opponent_reports(
        [value["evaluation"] for value in reports.values()]
    )
    combined_v1_escape = None
    if v1_evaluation is not None:
        combined_v1_escape = float(
            combine_opponent_reports(
                [v1_evaluation[name] for name in arguments.opponents]
            )["player_escape_rate"]
        )
    release_assessment = assess_persona_gates(
        combined, v1_player_escape_rate=combined_v1_escape
    )
    individual_regressions_pass = all(
        value["persona_assessment"]["gates"].get("v1_escape_regression", True)
        for value in reports.values()
    )
    result = {
        "schema": "catamaze.evaluation.persona.v2",
        "checkpoint": arguments.checkpoint,
        "episodes_per_opponent": arguments.episodes,
        "mode": arguments.mode,
        "counterfactual_persona_js": counterfactual,
        "counterfactual_gate_passed": max(counterfactual.values()) >= 0.02,
        "combined_evaluation": combined,
        "release_assessment": release_assessment,
        "release_gate_passed": bool(
            release_assessment["passed"]
            and max(counterfactual.values()) >= 0.02
            and individual_regressions_pass
        ),
        "reports": reports,
    }
    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if arguments.episodes_output:
        episodes_output = Path(arguments.episodes_output)
        episodes_output.parent.mkdir(parents=True, exist_ok=True)
        episodes_output.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in episode_records),
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
