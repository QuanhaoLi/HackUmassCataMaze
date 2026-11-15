# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:41 EST
# Last Modified by: Codex
# Computes V2 persona gates and counterfactual action-distribution divergence.

from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np
import torch
from torch import nn

from training.v2.model import PERSONA_COUNT, PERSONA_OFFSET


PERSONAS = ("aggressive", "cautious", "explorer")


def combine_opponent_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if not reports:
        raise ValueError("at least one opponent report is required")
    episodes = sum(int(report["episodes"]) for report in reports)
    outcomes = {
        name: sum(int(report["outcomes"][name]) for report in reports)
        for name in ("player_death", "player_escape", "timeout")
    }
    personality: dict[str, Any] = {}
    for name in PERSONAS:
        action_counts = np.sum(
            np.asarray(
                [report["personality"][name]["action_counts"] for report in reports]
            ),
            axis=0,
            dtype=np.int64,
        )
        active_steps = max(int(action_counts.sum()), 1)
        moves = max(int(action_counts[:4].sum()), 1)

        def total_per_tick(metric: str) -> float:
            return sum(
                float(report["personality"][name][metric])
                * sum(report["personality"][name]["action_counts"])
                / 100.0
                for report in reports
            )

        revisit_total = sum(
            float(report["personality"][name]["revisit_rate"])
            * sum(report["personality"][name]["action_counts"][:4])
            for report in reports
        )
        personality[name] = {
            "mean_return": sum(
                float(report["personality"][name]["mean_return"])
                * int(report["episodes"])
                for report in reports
            )
            / episodes,
            "death_rate": sum(
                float(report["personality"][name]["death_rate"])
                * int(report["episodes"])
                for report in reports
            )
            / episodes,
            "shots_per_100_ticks": total_per_tick("shots_per_100_ticks")
            * 100.0
            / active_steps,
            "hits_per_100_ticks": total_per_tick("hits_per_100_ticks")
            * 100.0
            / active_steps,
            "first_visits_per_100_ticks": total_per_tick(
                "first_visits_per_100_ticks"
            )
            * 100.0
            / active_steps,
            "revisit_rate": revisit_total / moves,
            "action_counts": action_counts.tolist(),
        }
    return {
        "episodes": episodes,
        "opponent": "combined",
        "mode": reports[0]["mode"],
        "outcomes": outcomes,
        "player_escape_rate": outcomes["player_escape"] / episodes,
        "player_death_rate": outcomes["player_death"] / episodes,
        "timeout_rate": outcomes["timeout"] / episodes,
        "personality": personality,
    }


def jensen_shannon(left: np.ndarray, right: np.ndarray) -> float:
    left = np.asarray(left, dtype=np.float64)
    right = np.asarray(right, dtype=np.float64)
    left = left / max(float(left.sum()), 1.0)
    right = right / max(float(right.sum()), 1.0)
    midpoint = 0.5 * (left + right)

    def kl(source: np.ndarray) -> float:
        selected = source > 0
        return float(np.sum(source[selected] * np.log(source[selected] / midpoint[selected])))

    return 0.5 * (kl(left) + kl(right))


def assess_persona_gates(
    report: dict[str, Any],
    *,
    v1_player_escape_rate: float | None = None,
) -> dict[str, Any]:
    personality = report["personality"]
    shots = np.asarray(
        [personality[name]["shots_per_100_ticks"] for name in PERSONAS], dtype=np.float64
    )
    hits = np.asarray(
        [personality[name]["hits_per_100_ticks"] for name in PERSONAS], dtype=np.float64
    )
    first_visits = np.asarray(
        [personality[name]["first_visits_per_100_ticks"] for name in PERSONAS],
        dtype=np.float64,
    )
    deaths = np.asarray(
        [personality[name]["death_rate"] for name in PERSONAS], dtype=np.float64
    )
    revisits = np.asarray(
        [personality[name]["revisit_rate"] for name in PERSONAS], dtype=np.float64
    )
    pairwise_js = {
        f"{PERSONAS[left]}:{PERSONAS[right]}": jensen_shannon(
            np.asarray(personality[PERSONAS[left]]["action_counts"]),
            np.asarray(personality[PERSONAS[right]]["action_counts"]),
        )
        for left, right in combinations(range(PERSONA_COUNT), 2)
    }
    gates = {
        "aggressive_shots": bool(shots[0] >= shots.mean() * 1.20),
        "aggressive_hits": bool(hits[0] >= hits.mean() * 1.20),
        "cautious_survival": bool(
            deaths[1] <= deaths[0] * 0.85 if deaths[0] > 0 else deaths[1] == 0
        ),
        "explorer_first_visits": bool(first_visits[2] >= first_visits.mean() * 1.20),
        "explorer_revisits": bool(revisits[2] < revisits[0]),
        "action_divergence": bool(max(pairwise_js.values()) >= 0.02),
    }
    if v1_player_escape_rate is not None:
        gates["v1_escape_regression"] = bool(
            float(report["player_escape_rate"]) <= v1_player_escape_rate + 0.05
        )
    return {
        "passed": all(gates.values()),
        "gates": gates,
        "pairwise_action_js": pairwise_js,
        "metrics": {
            "shots_per_100_ticks": shots.tolist(),
            "hits_per_100_ticks": hits.tolist(),
            "first_visits_per_100_ticks": first_visits.tolist(),
            "death_rate": deaths.tolist(),
            "revisit_rate": revisits.tolist(),
        },
    }


@torch.no_grad()
def counterfactual_persona_divergence(
    model: nn.Module,
    spatial: torch.Tensor,
    scalar: torch.Tensor,
    hidden: torch.Tensor,
    action_mask: torch.Tensor,
) -> dict[str, float]:
    if spatial.ndim != 4 or spatial.shape[1:] != (13, 5, 5):
        raise ValueError("spatial must have shape [N,13,5,5]")
    if scalar.shape != (spatial.shape[0], 46):
        raise ValueError("scalar must have shape [N,46]")
    if hidden.shape != (1, spatial.shape[0], 256):
        raise ValueError("hidden must have shape [1,N,256]")
    if action_mask.shape != (spatial.shape[0], 9):
        raise ValueError("action_mask must have shape [N,9]")
    model.eval()
    probabilities: list[torch.Tensor] = []
    for persona in range(PERSONA_COUNT):
        conditioned = scalar.clone()
        conditioned[:, PERSONA_OFFSET : PERSONA_OFFSET + PERSONA_COUNT] = 0.0
        conditioned[:, PERSONA_OFFSET + persona] = 1.0
        output = model(
            spatial[:, None].float(),
            conditioned[:, None].float(),
            hidden=hidden,
            episode_starts=torch.zeros(
                (spatial.shape[0], 1), dtype=torch.bool, device=spatial.device
            ),
        )
        logits = output.logits[:, 0].masked_fill(~action_mask, -torch.inf)
        probabilities.append(torch.softmax(logits, dim=-1))
    result: dict[str, float] = {}
    for left, right in combinations(range(PERSONA_COUNT), 2):
        p = probabilities[left]
        q = probabilities[right]
        midpoint = 0.5 * (p + q)
        p_terms = torch.where(p > 0, p * (p.log() - midpoint.log()), torch.zeros_like(p))
        q_terms = torch.where(q > 0, q * (q.log() - midpoint.log()), torch.zeros_like(q))
        divergence = 0.5 * (p_terms.sum(dim=-1) + q_terms.sum(dim=-1))
        result[f"{PERSONAS[left]}:{PERSONAS[right]}"] = float(divergence.mean())
    return result
