# Created at: 2026-11-14 19:41 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:41 EST
# Last Modified by: Codex
# Evaluates V2 with aggregate persona metrics and immutable per-episode evidence.

from __future__ import annotations

from typing import Any

import numpy as np
import torch
from torch import nn

from training import _native
from training.env import CataMazeBatchEnv
from training.evaluator import PERSONAS
from training.model import masked_categorical
from training.opponents import OpponentStrategy


def evaluate_policy_detailed(
    model: nn.Module,
    *,
    episodes: int,
    opponent: OpponentStrategy,
    mode: str,
    seed: int,
    num_envs: int,
    device: torch.device,
    temperature: float = 0.8,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
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
    total_action_counts = np.zeros((3, 9), dtype=np.int64)
    total_active_steps = np.zeros(3, dtype=np.int64)
    total_shots = np.zeros(3, dtype=np.int64)
    total_hits = np.zeros(3, dtype=np.int64)
    total_deaths = np.zeros(3, dtype=np.int64)
    total_returns = np.zeros(3, dtype=np.float64)
    total_first_visits = np.zeros(3, dtype=np.int64)
    total_revisits = np.zeros(3, dtype=np.int64)

    episode_actions = np.zeros((num_envs, 3, 9), dtype=np.int64)
    episode_steps = np.zeros((num_envs, 3), dtype=np.int64)
    episode_shots = np.zeros((num_envs, 3), dtype=np.int64)
    episode_hits = np.zeros((num_envs, 3), dtype=np.int64)
    episode_returns = np.zeros((num_envs, 3), dtype=np.float64)
    episode_first = np.zeros((num_envs, 3), dtype=np.int64)
    episode_revisits = np.zeros((num_envs, 3), dtype=np.int64)
    visited = np.zeros((num_envs, 3, 2500), dtype=np.bool_)
    for env in range(num_envs):
        for persona in range(3):
            x, y = environment.observation["positions"][env, persona + 1]
            visited[env, persona, int(y) * 50 + int(x)] = True

    records: list[dict[str, Any]] = []
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
                actions = output.logits[:, 0].masked_fill(~safe_mask, -torch.inf).argmax(
                    dim=-1
                )
            else:
                distribution = masked_categorical(
                    output.logits[:, 0], safe_mask, temperature=temperature
                )
                actions = torch.multinomial(
                    distribution.probs, num_samples=1, generator=generator
                ).squeeze(-1)
            actions[~active_tensor] = 8
        actions_numpy = actions.to("cpu", dtype=torch.uint8).numpy().reshape(num_envs, 3)
        for env in range(num_envs):
            for persona in range(3):
                if not active[env, persona]:
                    continue
                action = int(actions_numpy[env, persona])
                total_action_counts[persona, action] += 1
                total_active_steps[persona] += 1
                episode_actions[env, persona, action] += 1
                episode_steps[env, persona] += 1
                if 4 <= action <= 7:
                    total_shots[persona] += 1
                    episode_shots[env, persona] += 1

        step = environment.step(actions_numpy)
        episode_returns += step.reward.total
        terminal = step.observation
        results = terminal["last_result"][:, 1:]
        positions = terminal["positions"][:, 1:]
        for env in range(num_envs):
            for persona in range(3):
                if results[env, persona] != _native.RESULT_MOVED:
                    continue
                x, y = positions[env, persona]
                cell = int(y) * 50 + int(x)
                if visited[env, persona, cell]:
                    total_revisits[persona] += 1
                    episode_revisits[env, persona] += 1
                else:
                    total_first_visits[persona] += 1
                    episode_first[env, persona] += 1
                    visited[env, persona, cell] = True
            count = int(terminal["event_count"][env])
            for event in terminal["events"][env, :count]:
                if int(event[0]) == _native.EVENT_DAMAGE_CREDIT and int(event[2]) == 0:
                    actor = int(event[1])
                    if 1 <= actor <= 3:
                        hits = int(event[6])
                        total_hits[actor - 1] += hits
                        episode_hits[env, actor - 1] += hits

        ended = step.reward.terminated | step.reward.truncated
        hidden = output.hidden.detach()
        ended_flat = torch.from_numpy(ended).reshape(-1).to(device)
        hidden[:, ended_flat] = 0.0
        episode_starts = ended_flat
        finished = np.asarray(terminal["status"]) != _native.STATUS_RUNNING
        for env in np.flatnonzero(finished):
            status = int(terminal["status"][env])
            if status == _native.STATUS_DEATH:
                outcome = "player_death"
            elif status == _native.STATUS_VICTORY:
                outcome = "player_escape"
            else:
                outcome = "timeout"
            outcomes[outcome] += 1
            total_deaths += ~terminal["alive"][env]
            total_returns += episode_returns[env]
            persona_records = []
            for persona, name in enumerate(PERSONAS):
                steps = max(int(episode_steps[env, persona]), 1)
                moves = max(int(episode_actions[env, persona, :4].sum()), 1)
                persona_records.append(
                    {
                        "persona": name,
                        "alive": bool(terminal["alive"][env, persona]),
                        "return": float(episode_returns[env, persona]),
                        "action_counts": episode_actions[env, persona].tolist(),
                        "shots_per_100_ticks": float(
                            episode_shots[env, persona] * 100.0 / steps
                        ),
                        "hits_per_100_ticks": float(
                            episode_hits[env, persona] * 100.0 / steps
                        ),
                        "first_visits_per_100_ticks": float(
                            episode_first[env, persona] * 100.0 / steps
                        ),
                        "revisit_rate": float(episode_revisits[env, persona] / moves),
                    }
                )
            records.append(
                {
                    "evaluation_seed": seed,
                    "episode_index": completed,
                    "environment_slot": int(env),
                    "game_seed": int(terminal["seed"][env]),
                    "terminal_state_hash": int(terminal["state_hash"][env]),
                    "ticks": int(terminal["tick"][env]),
                    "outcome": outcome,
                    "personas": persona_records,
                }
            )
            completed += 1
            episode_actions[env] = 0
            episode_steps[env] = 0
            episode_shots[env] = 0
            episode_hits[env] = 0
            episode_returns[env] = 0.0
            episode_first[env] = 0
            episode_revisits[env] = 0
        reset = environment.reset_finished()
        if np.any(reset):
            reset_agents = np.repeat(reset, 3)
            reset_tensor = torch.from_numpy(reset_agents).to(device)
            hidden[:, reset_tensor] = 0.0
            episode_starts[reset_tensor] = True
            for env in np.flatnonzero(reset):
                visited[env] = False
                for persona in range(3):
                    x, y = environment.observation["positions"][env, persona + 1]
                    visited[env, persona, int(y) * 50 + int(x)] = True

    personality: dict[str, Any] = {}
    for persona, name in enumerate(PERSONAS):
        steps = max(int(total_active_steps[persona]), 1)
        moves = max(int(total_action_counts[persona, :4].sum()), 1)
        personality[name] = {
            "mean_return": float(total_returns[persona] / completed),
            "death_rate": float(total_deaths[persona] / completed),
            "shots_per_100_ticks": float(total_shots[persona] * 100.0 / steps),
            "hits_per_100_ticks": float(total_hits[persona] * 100.0 / steps),
            "first_visits_per_100_ticks": float(
                total_first_visits[persona] * 100.0 / steps
            ),
            "revisit_rate": float(total_revisits[persona] / moves),
            "action_counts": total_action_counts[persona].tolist(),
        }
    report = {
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
    return report, records
