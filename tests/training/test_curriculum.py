# Created at: 2026-11-14 04:44 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:44 EST
# Last Modified by: Codex
# Verifies that curriculum promotion requires both steps and fixed evaluation gates.

from __future__ import annotations

from training.curriculum import CurriculumController


def report(
    *,
    death: float,
    escape: float,
    shots: tuple[float, float, float] = (3.0, 2.0, 1.0),
    deaths: tuple[float, float, float] = (0.2, 0.1, 0.15),
    visits: tuple[float, float, float] = (2.0, 3.0, 4.0),
) -> dict:
    names = ("aggressive", "cautious", "explorer")
    return {
        "episodes": 300,
        "player_death_rate": death,
        "player_escape_rate": escape,
        "personality": {
            name: {
                "shots_per_100_ticks": shots[index],
                "death_rate": deaths[index],
                "first_visits_per_100_ticks": visits[index],
            }
            for index, name in enumerate(names)
        },
    }


def test_steps_alone_never_promote_and_all_stage_gates_are_required() -> None:
    controller = CurriculumController()
    assert not controller.try_promote(5_000_000, {})
    failing = {
        "stationary": report(death=0.24, escape=0.0),
        "random_valid": report(death=0.2, escape=0.05),
    }
    assert not controller.try_promote(5_000_000, failing)

    passing = {
        "stationary": report(death=0.25, escape=0.0),
        "random_valid": report(death=0.2, escape=0.10),
    }
    assert controller.try_promote(5_000_000, passing)
    assert controller.stage == "B"


def test_later_stages_enforce_combat_and_personality_gates() -> None:
    controller = CurriculumController(stage="B")
    assert controller.try_promote(
        20_000_000, {"wall_follower": report(death=0.10, escape=0.30)}
    )
    reports = {
        "shortest_path_noisy": report(death=0.1, escape=0.8),
        "combat_planner": report(death=0.1, escape=0.8),
    }
    assert controller.try_promote(50_000_000, reports)
    assert controller.stage == "D"
    assert not controller.try_promote(100_000_000, reports)
