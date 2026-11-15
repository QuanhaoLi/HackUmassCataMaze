# Created at: 2026-11-14 19:41 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:41 EST
# Last Modified by: Codex
# Verifies aggregate V2 evaluation is backed by complete per-episode evidence.

from __future__ import annotations

import torch

from training.opponents import OpponentStrategy
from training.v2.detailed_evaluator import evaluate_policy_detailed
from training.v2.model import PersonaRecurrentActorCritic


def test_detailed_evaluation_records_every_completed_episode() -> None:
    report, records = evaluate_policy_detailed(
        PersonaRecurrentActorCritic(),
        episodes=2,
        opponent=OpponentStrategy.SHORTEST_PATH_NOISY,
        mode="deterministic",
        seed=109,
        num_envs=2,
        device=torch.device("cpu"),
    )
    assert len(records) == report["episodes"]
    assert sum(report["outcomes"].values()) == len(records)
    assert {record["outcome"] for record in records} <= {
        "player_death",
        "player_escape",
        "timeout",
    }
    for record in records:
        assert record["ticks"] > 0
        assert len(record["personas"]) == 3
        assert all(len(persona["action_counts"]) == 9 for persona in record["personas"])
