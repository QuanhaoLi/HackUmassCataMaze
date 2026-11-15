# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:04 EST
# Last Modified by: Codex
# Verifies explicit V2 persona gates and same-state counterfactual divergence.

from __future__ import annotations

import torch

from training.v2.evaluator import assess_persona_gates, counterfactual_persona_divergence
from training.v2.model import PersonaRecurrentActorCritic


def passing_report() -> dict[str, object]:
    return {
        "player_escape_rate": 0.20,
        "personality": {
            "aggressive": {
                "shots_per_100_ticks": 6.0,
                "hits_per_100_ticks": 3.0,
                "first_visits_per_100_ticks": 1.0,
                "death_rate": 0.40,
                "revisit_rate": 0.50,
                "action_counts": [30, 5, 5, 5, 20, 20, 10, 5, 0],
            },
            "cautious": {
                "shots_per_100_ticks": 2.0,
                "hits_per_100_ticks": 1.0,
                "first_visits_per_100_ticks": 1.0,
                "death_rate": 0.20,
                "revisit_rate": 0.30,
                "action_counts": [5, 30, 5, 5, 5, 5, 5, 5, 35],
            },
            "explorer": {
                "shots_per_100_ticks": 1.0,
                "hits_per_100_ticks": 0.5,
                "first_visits_per_100_ticks": 5.0,
                "death_rate": 0.30,
                "revisit_rate": 0.10,
                "action_counts": [25, 25, 20, 20, 2, 2, 2, 2, 2],
            },
        },
    }


def test_persona_gate_assessment_requires_style_and_v1_effectiveness() -> None:
    assessment = assess_persona_gates(passing_report(), v1_player_escape_rate=0.18)
    assert assessment["passed"] is True
    assert all(assessment["gates"].values())
    failed = passing_report()
    failed["personality"]["aggressive"]["shots_per_100_ticks"] = 1.0
    assert assess_persona_gates(failed)["gates"]["aggressive_shots"] is False


def test_counterfactual_divergence_is_zero_when_persona_inputs_are_neutralized() -> None:
    model = PersonaRecurrentActorCritic()
    with torch.no_grad():
        model.scalar_encoder[0].weight[:, 43:46] = 0.0
    spatial = torch.rand(4, 13, 5, 5)
    scalar = torch.rand(4, 46)
    hidden = torch.zeros(1, 4, 256)
    mask = torch.ones(4, 9, dtype=torch.bool)
    divergence = counterfactual_persona_divergence(
        model, spatial, scalar, hidden, mask
    )
    assert max(divergence.values()) == 0.0


def test_counterfactual_divergence_detects_a_specialized_head() -> None:
    model = PersonaRecurrentActorCritic()
    with torch.no_grad():
        model.actors[0].bias[4] = 5.0
    divergence = counterfactual_persona_divergence(
        model,
        torch.rand(4, 13, 5, 5),
        torch.rand(4, 46),
        torch.zeros(1, 4, 256),
        torch.ones(4, 9, dtype=torch.bool),
    )
    assert max(divergence.values()) > 0.02
