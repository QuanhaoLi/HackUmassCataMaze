# Created at: 2026-11-14 04:51 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:51 EST
# Last Modified by: Codex
# Runs explicit-seed environment invariants without model or network dependencies.

from __future__ import annotations

import argparse
import json
from typing import Iterable

import numpy as np

from training import _native
from training.reward import RewardCalculator


def _sample_legal(
    masks: np.ndarray, alive: np.ndarray, random: np.random.Generator
) -> np.ndarray:
    actions = np.full(alive.shape, 8, dtype=np.uint8)
    for index in np.ndindex(alive.shape):
        if alive[index]:
            actions[index] = random.choice(np.flatnonzero(masks[index]))
    return actions


def validate_environment(
    *, episodes: int, seeds: Iterable[int], num_envs: int = 64
) -> dict[str, object]:
    seed_values = [int(seed) for seed in seeds][:episodes]
    if len(seed_values) != episodes or episodes <= 0:
        raise ValueError("seed collection must contain at least the requested positive episode count")
    batch_size = min(num_envs, episodes)
    next_seed = batch_size
    native = _native.NativeBatch(
        np.asarray(seed_values[:batch_size], dtype=np.uint64), randomize_spawns=True
    )
    previous = native.snapshot()
    reward = RewardCalculator(previous)
    random = np.random.Generator(np.random.PCG64(0x434154414D415A45))
    active_env = np.ones((batch_size,), dtype=np.bool_)
    outcomes = {"death": 0, "victory": 0, "timeout": 0}
    completed = 0
    agent_steps = 0
    environment_steps = 0
    while completed < episodes:
        ai_actions = _sample_legal(previous["action_mask"], previous["alive"], random)
        player_actions = _sample_legal(
            previous["player_action_mask"], active_env, random
        )
        ai_actions[~active_env] = 8
        player_actions[~active_env] = 8
        current = native.step(player_actions, ai_actions)
        result = reward.calculate(previous, current)
        selected_agents = np.repeat(active_env[:, None], 3, axis=1)
        if not np.all(np.isfinite(result.total[selected_agents])):
            raise RuntimeError("environment validator observed non-finite reward")
        component_total = np.zeros_like(result.total)
        for component in result.components.values():
            component_total += component
        if not np.allclose(result.total[selected_agents], component_total[selected_agents], atol=1e-6):
            raise RuntimeError("reward component sum mismatch")
        if np.any(current["hp"] > 5) or np.any(current["ammo"] > 3):
            raise RuntimeError("entity resource range invariant failed")
        if np.any(current["event_count"] > 192):
            raise RuntimeError("event capacity invariant failed")
        if np.any(current["last_result"][:, 1:][selected_agents] == _native.RESULT_INVALID_FALLBACK):
            raise RuntimeError("masked AI action produced INVALID_FALLBACK")
        for env in np.flatnonzero(active_env):
            alive_positions = current["positions"][env][
                np.concatenate(([True], current["alive"][env]))
            ]
            if len({tuple(position) for position in alive_positions}) != len(alive_positions):
                raise RuntimeError("living entities share a position")
        agent_steps += int(previous["alive"][active_env].sum())
        environment_steps += int(active_env.sum())

        finished = active_env & (current["status"] != _native.STATUS_RUNNING)
        reset_indices: list[int] = []
        reset_seeds: list[int] = []
        for env in np.flatnonzero(finished):
            status = int(current["status"][env])
            if status == _native.STATUS_DEATH:
                outcomes["death"] += 1
            elif status == _native.STATUS_VICTORY:
                outcomes["victory"] += 1
            else:
                outcomes["timeout"] += 1
            completed += 1
            if next_seed < episodes:
                reset_indices.append(int(env))
                reset_seeds.append(seed_values[next_seed])
                next_seed += 1
            else:
                active_env[env] = False
        if reset_indices:
            current = native.reset_at(
                np.asarray(reset_indices, dtype=np.int64),
                np.asarray(reset_seeds, dtype=np.uint64),
            )
            reset_mask = np.zeros((batch_size,), dtype=np.bool_)
            reset_mask[reset_indices] = True
            reward.reset(current, reset_mask)
        previous = current
    return {
        "episodes": completed,
        "agent_steps": agent_steps,
        "environment_steps": environment_steps,
        "outcomes": outcomes,
    }


def _parse_seeds(value: str) -> range:
    start_text, separator, stop_text = value.partition(":")
    if not separator:
        seed = int(start_text)
        return range(seed, seed + 1)
    start = int(start_text)
    stop = int(stop_text)
    if stop < start:
        raise ValueError("seed range stop must be at least start")
    return range(start, stop + 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--seeds", default="1:1000")
    parser.add_argument("--num-envs", type=int, default=64)
    arguments = parser.parse_args()
    summary = validate_environment(
        episodes=arguments.episodes,
        seeds=_parse_seeds(arguments.seeds),
        num_envs=arguments.num_envs,
    )
    print("ENVIRONMENT_VALIDATION_OK " + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
