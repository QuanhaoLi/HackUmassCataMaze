# Created at: 2026-11-14 04:44 EST
# Created by: Codex
# Last Modified at: 2026-11-14 08:01 EST
# Last Modified by: Codex
# Enforces immutable step and fixed-evaluation gates for curriculum promotion.

from __future__ import annotations

from typing import Any, Mapping


class CurriculumController:
    STAGES = ("A", "B", "C", "D")
    MINIMUM_STEPS = {"A": 5_000_000, "B": 20_000_000, "C": 50_000_000}

    def __init__(self, stage: str = "A") -> None:
        if stage not in self.STAGES:
            raise ValueError(f"invalid curriculum stage: {stage}")
        self.stage = stage
        self.last_failures: tuple[str, ...] = ()

    def try_promote(
        self,
        agent_steps: int,
        reports: Mapping[str, Mapping[str, Any]],
    ) -> bool:
        if self.stage == "D":
            self.last_failures = ("D is the final curriculum stage",)
            return False
        failures: list[str] = []
        if agent_steps < self.MINIMUM_STEPS[self.stage]:
            failures.append(f"minimum agent steps not reached for stage {self.stage}")
        required = {
            "A": ("stationary", "random_valid"),
            "B": ("wall_follower",),
            "C": ("shortest_path_noisy", "combat_planner"),
        }[self.stage]
        for opponent in required:
            if opponent not in reports:
                failures.append(f"missing {opponent} evaluation")
            elif int(reports[opponent].get("episodes", 0)) < 300:
                failures.append(f"{opponent} evaluation has fewer than 300 episodes")
        if not failures:
            if self.stage == "A":
                if float(reports["stationary"]["player_death_rate"]) < 0.20:
                    failures.append("stationary player death rate is below 20%")
                if float(reports["random_valid"]["player_escape_rate"]) > 0.10:
                    failures.append("random-valid player escape rate exceeds 10%")
            elif self.stage == "B":
                wall = reports["wall_follower"]
                if float(wall["player_escape_rate"]) > 0.30:
                    failures.append("wall-follower player escape rate exceeds 30%")
                if float(wall["player_death_rate"]) < 0.10:
                    failures.append("wall-follower player death rate is below 10%")
            else:
                self._check_stage_c(reports, failures)
        self.last_failures = tuple(failures)
        if failures:
            return False
        self.stage = self.STAGES[self.STAGES.index(self.stage) + 1]
        return True

    @staticmethod
    def _check_stage_c(
        reports: Mapping[str, Mapping[str, Any]], failures: list[str]
    ) -> None:
        selected = [reports["shortest_path_noisy"], reports["combat_planner"]]
        if any(float(report["player_escape_rate"]) > 0.80 for report in selected):
            failures.append("hard-opponent player escape rate exceeds 80%")

        def mean_metric(persona: str, metric: str) -> float:
            return sum(float(report["personality"][persona][metric]) for report in selected) / 2.0

        if mean_metric("aggressive", "shots_per_100_ticks") < mean_metric(
            "cautious", "shots_per_100_ticks"
        ):
            failures.append("aggressive shooting rate is below cautious")
        if mean_metric("cautious", "death_rate") > mean_metric("aggressive", "death_rate"):
            failures.append("cautious death rate exceeds aggressive")
        if mean_metric("explorer", "first_visits_per_100_ticks") < mean_metric(
            "aggressive", "first_visits_per_100_ticks"
        ):
            failures.append("explorer first-visit rate is below aggressive")

    def state_dict(self) -> dict[str, Any]:
        return {"stage": self.stage, "last_failures": self.last_failures}

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        stage = str(state["stage"])
        if stage not in self.STAGES:
            raise ValueError("checkpoint contains invalid curriculum stage")
        self.stage = stage
        self.last_failures = tuple(str(item) for item in state.get("last_failures", ()))
