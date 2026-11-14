# Created at: 2026-11-14 04:43 EST
# Created by: Codex
# Last Modified at: 2026-11-14 07:18 EST
# Last Modified by: Codex
# Verifies fixed-seed evaluation produces complete personality metrics.

import torch

from training.evaluator import evaluate_policy, merge_evaluation_reports
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


def test_stochastic_evaluation_replays_exactly_for_fixed_seed() -> None:
    torch.manual_seed(61)
    model = RecurrentActorCritic()
    arguments = {
        "episodes": 2,
        "opponent": OpponentStrategy.RANDOM_VALID,
        "mode": "stochastic",
        "seed": 67,
        "num_envs": 2,
        "device": torch.device("cpu"),
    }

    first = evaluate_policy(model, **arguments)
    second = evaluate_policy(model, **arguments)

    assert second == first


def test_evaluation_report_merge_preserves_counts_and_weighted_rates() -> None:
    torch.manual_seed(71)
    model = RecurrentActorCritic()
    reports = [
        evaluate_policy(
            model,
            episodes=2,
            opponent=OpponentStrategy.RANDOM_VALID,
            mode="deterministic",
            seed=seed,
            num_envs=2,
            device=torch.device("cpu"),
        )
        for seed in (73, 79)
    ]

    merged = merge_evaluation_reports(reports)

    assert merged["episodes"] == sum(report["episodes"] for report in reports)
    assert sum(merged["outcomes"].values()) == merged["episodes"]
    for name in ("aggressive", "cautious", "explorer"):
        expected_actions = sum(
            (torch.tensor(report["personality"][name]["action_counts"]) for report in reports),
            start=torch.zeros(9, dtype=torch.int64),
        )
        assert merged["personality"][name]["action_counts"] == expected_actions.tolist()
