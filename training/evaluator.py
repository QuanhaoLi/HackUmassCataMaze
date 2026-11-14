# Created at: 2026-11-14 04:43 EST
# Created by: Codex
# Last Modified at: 2026-11-14 07:18 EST
# Last Modified by: Codex
# Runs fixed-seed policy evaluation and reports outcome and personality metrics.

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from training import _native
from training.config import load_config
from training.env import CataMazeBatchEnv
from training.model import RecurrentActorCritic, masked_categorical
from training.opponents import OpponentStrategy


PERSONAS = ("aggressive", "cautious", "explorer")


def merge_evaluation_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if not reports:
        raise ValueError("at least one evaluation report is required")
    opponent = reports[0]["opponent"]
    mode = reports[0]["mode"]
    if any(report["opponent"] != opponent or report["mode"] != mode for report in reports):
        raise ValueError("evaluation reports must share opponent and mode")
    episodes = sum(int(report["episodes"]) for report in reports)
    outcomes = {
        name: sum(int(report["outcomes"][name]) for report in reports)
        for name in ("player_death", "player_escape", "timeout")
    }
    personality: dict[str, Any] = {}
    for name in PERSONAS:
        action_counts = np.sum(
            np.asarray([report["personality"][name]["action_counts"] for report in reports]),
            axis=0,
            dtype=np.int64,
        )
        active_steps = max(int(action_counts.sum()), 1)
        moves = max(int(action_counts[:4].sum()), 1)
        weighted_return = sum(
            float(report["personality"][name]["mean_return"]) * int(report["episodes"])
            for report in reports
        )
        deaths = sum(
            float(report["personality"][name]["death_rate"]) * int(report["episodes"])
            for report in reports
        )

        def per_tick_total(metric: str) -> float:
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
            "mean_return": weighted_return / episodes,
            "death_rate": deaths / episodes,
            "shots_per_100_ticks": per_tick_total("shots_per_100_ticks")
            * 100.0
            / active_steps,
            "hits_per_100_ticks": per_tick_total("hits_per_100_ticks")
            * 100.0
            / active_steps,
            "first_visits_per_100_ticks": per_tick_total("first_visits_per_100_ticks")
            * 100.0
            / active_steps,
            "revisit_rate": revisit_total / moves,
            "action_counts": action_counts.tolist(),
        }
    return {
        "episodes": episodes,
        "opponent": opponent,
        "mode": mode,
        "seeds": [int(report["seed"]) for report in reports],
        "outcomes": outcomes,
        "player_escape_rate": outcomes["player_escape"] / episodes,
        "player_death_rate": outcomes["player_death"] / episodes,
        "timeout_rate": outcomes["timeout"] / episodes,
        "personality": personality,
    }


def evaluate_policy(
    model: RecurrentActorCritic,
    *,
    episodes: int,
    opponent: OpponentStrategy,
    mode: str,
    seed: int,
    num_envs: int,
    device: torch.device,
    temperature: float = 0.8,
) -> dict[str, Any]:
    if episodes <= 0 or num_envs <= 0:
        raise ValueError("episodes and num_envs must be positive")
    if mode not in ("stochastic", "deterministic"):
        raise ValueError("mode must be stochastic or deterministic")
    environment = CataMazeBatchEnv(num_envs, seed, curriculum_stage="D")
    environment.force_opponent_strategy(int(opponent))
    batch_agents = num_envs * 3
    hidden = torch.zeros((1, batch_agents, 256), device=device)
    episode_starts = torch.ones((batch_agents,), dtype=torch.bool, device=device)
    generator = torch.Generator(device=device.type).manual_seed(seed)
    model.eval()

    outcomes = {"player_death": 0, "player_escape": 0, "timeout": 0}
    action_counts = np.zeros((3, 9), dtype=np.int64)
    active_steps = np.zeros((3,), dtype=np.int64)
    shots = np.zeros((3,), dtype=np.int64)
    hits = np.zeros((3,), dtype=np.int64)
    deaths = np.zeros((3,), dtype=np.int64)
    returns_sum = np.zeros((3,), dtype=np.float64)
    first_visits = np.zeros((3,), dtype=np.int64)
    revisits = np.zeros((3,), dtype=np.int64)
    episode_returns = np.zeros((num_envs, 3), dtype=np.float64)
    visited = np.zeros((num_envs, 3, 2500), dtype=np.bool_)
    for env in range(num_envs):
        for agent in range(3):
            x, y = environment.observation["positions"][env, agent + 1]
            visited[env, agent, int(y) * 50 + int(x)] = True

    completed = 0
    while completed < episodes:
        observation = environment.observation
        active = np.asarray(observation["alive"], dtype=np.bool_)
        spatial = torch.from_numpy(observation["spatial"]).reshape(-1, 13, 5, 5)
        scalar = torch.from_numpy(observation["scalar"]).reshape(-1, 46)
        mask = torch.from_numpy(observation["action_mask"]).reshape(-1, 9).to(device)
        active_tensor = torch.from_numpy(active).reshape(-1).to(device)
        safe_mask = mask.clone()
        safe_mask[~active_tensor] = False
        safe_mask[:, 8] |= ~active_tensor
        with torch.no_grad():
            output = model(
                spatial[:, None].to(device, dtype=torch.float32),
                scalar[:, None].to(device, dtype=torch.float32),
                hidden=hidden,
                episode_starts=episode_starts[:, None],
            )
            if mode == "deterministic":
                masked_logits = output.logits[:, 0].masked_fill(~safe_mask, -torch.inf)
                actions = masked_logits.argmax(dim=-1)
            else:
                distribution = masked_categorical(
                    output.logits[:, 0], safe_mask, temperature=temperature
                )
                actions = torch.multinomial(
                    distribution.probs, num_samples=1, generator=generator
                ).squeeze(-1)
            actions[~active_tensor] = 8
        actions_numpy = actions.to("cpu", dtype=torch.uint8).numpy().reshape(num_envs, 3)
        for persona in range(3):
            persona_actions = actions_numpy[:, persona][active[:, persona]]
            active_steps[persona] += persona_actions.size
            action_counts[persona] += np.bincount(persona_actions, minlength=9)
            shots[persona] += int(np.count_nonzero((persona_actions >= 4) & (persona_actions <= 7)))

        step = environment.step(actions_numpy)
        episode_returns += step.reward.total
        terminal_observation = step.observation
        results = terminal_observation["last_result"][:, 1:]
        positions = terminal_observation["positions"][:, 1:]
        for env in range(num_envs):
            for persona in range(3):
                if results[env, persona] != _native.RESULT_MOVED:
                    continue
                x, y = positions[env, persona]
                cell = int(y) * 50 + int(x)
                if visited[env, persona, cell]:
                    revisits[persona] += 1
                else:
                    first_visits[persona] += 1
                    visited[env, persona, cell] = True
            count = int(terminal_observation["event_count"][env])
            for event in terminal_observation["events"][env, :count]:
                if int(event[0]) == _native.EVENT_DAMAGE_CREDIT and int(event[2]) == 0:
                    actor = int(event[1])
                    if 1 <= actor <= 3:
                        hits[actor - 1] += int(event[6])

        ended = step.reward.terminated | step.reward.truncated
        hidden = output.hidden.detach()
        ended_flat = torch.from_numpy(ended).reshape(-1).to(device)
        hidden[:, ended_flat] = 0.0
        episode_starts = ended_flat
        finished = np.asarray(terminal_observation["status"]) != _native.STATUS_RUNNING
        for env in np.flatnonzero(finished):
            status = int(terminal_observation["status"][env])
            if status == _native.STATUS_DEATH:
                outcomes["player_death"] += 1
            elif status == _native.STATUS_VICTORY:
                outcomes["player_escape"] += 1
            else:
                outcomes["timeout"] += 1
            deaths += ~terminal_observation["alive"][env]
            returns_sum += episode_returns[env]
            completed += 1
            episode_returns[env] = 0.0
        reset = environment.reset_finished()
        if np.any(reset):
            reset_agents = np.repeat(reset, 3)
            hidden[:, torch.from_numpy(reset_agents).to(device)] = 0.0
            episode_starts[torch.from_numpy(reset_agents).to(device)] = True
            for env in np.flatnonzero(reset):
                visited[env] = False
                for persona in range(3):
                    x, y = environment.observation["positions"][env, persona + 1]
                    visited[env, persona, int(y) * 50 + int(x)] = True

    personality: dict[str, Any] = {}
    for persona, name in enumerate(PERSONAS):
        steps = max(int(active_steps[persona]), 1)
        moves = int(action_counts[persona, :4].sum())
        personality[name] = {
            "mean_return": float(returns_sum[persona] / completed),
            "death_rate": float(deaths[persona] / completed),
            "shots_per_100_ticks": float(shots[persona] * 100.0 / steps),
            "hits_per_100_ticks": float(hits[persona] * 100.0 / steps),
            "first_visits_per_100_ticks": float(first_visits[persona] * 100.0 / steps),
            "revisit_rate": float(revisits[persona] / max(moves, 1)),
            "action_counts": action_counts[persona].tolist(),
        }
    return {
        "episodes": completed,
        "opponent": opponent.name.lower(),
        "mode": mode,
        "seed": seed,
        "outcomes": outcomes,
        "player_escape_rate": outcomes["player_escape"] / completed,
        "player_death_rate": outcomes["player_death"] / completed,
        "timeout_rate": outcomes["timeout"] / completed,
        "personality": personality,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl/ppo_16gb.yaml")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--episodes", type=int, default=300)
    parser.add_argument("--opponent", choices=[item.name.lower() for item in OpponentStrategy])
    parser.add_argument("--mode", choices=("stochastic", "deterministic"), default="stochastic")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--output")
    arguments = parser.parse_args()
    config = load_config(arguments.config)
    device = torch.device(arguments.device)
    model = RecurrentActorCritic().to(device)
    payload = torch.load(arguments.checkpoint, map_location="cpu", weights_only=False)
    model.load_state_dict(payload["model"])
    opponents = (
        [OpponentStrategy[arguments.opponent.upper()]]
        if arguments.opponent
        else list(OpponentStrategy)
    )
    reports = [
        evaluate_policy(
            model,
            episodes=arguments.episodes,
            opponent=opponent,
            mode=arguments.mode,
            seed=int(config["seed"]) + 10_000 + int(opponent),
            num_envs=min(int(config["environment"]["num_envs"]), arguments.episodes),
            device=device,
        )
        for opponent in opponents
    ]
    output = json.dumps(reports, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
