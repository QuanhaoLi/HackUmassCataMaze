# Created at: 2026-11-14 04:43 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:43 EST
# Last Modified by: Codex
# Verifies fixed-seed evaluation produces complete personality metrics.

import torch

from training.evaluator import evaluate_policy
from training.model import RecurrentActorCritic
from training.opponents import OpponentStrategy


def test_fixed_seed_evaluator_reports_outcomes_and_every_persona() -> None:
    torch.manual_seed(53)
    model = RecurrentActorCritic()

    report = evaluate_policy(
        model,
        episodes=2,
        opponent=OpponentStrategy.SHORTEST_PATH_NOISY,
        mode="deterministic",
        seed=59,
        num_envs=2,
        device=torch.device("cpu"),
    )

    assert report["episodes"] >= 2
    assert sum(report["outcomes"].values()) == report["episodes"]
    assert 0.0 <= report["player_escape_rate"] <= 1.0
    assert set(report["personality"]) == {"aggressive", "cautious", "explorer"}
    for metrics in report["personality"].values():
        assert len(metrics["action_counts"]) == 9
