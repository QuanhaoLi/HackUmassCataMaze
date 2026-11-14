# Created at: 2026-11-14 04:38 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:38 EST
# Last Modified by: Codex
# Benchmarks deterministic batched environment throughput without neural-network work.

from __future__ import annotations

import argparse
import json
from time import perf_counter

import numpy as np

from training.config import load_config
from training.env import CataMazeBatchEnv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl/ppo_16gb.yaml")
    parser.add_argument("--num-envs", type=int)
    parser.add_argument("--ticks", type=int, default=10_000)
    arguments = parser.parse_args()
    config = load_config(arguments.config)
    num_envs = arguments.num_envs or int(config["environment"]["num_envs"])
    environment = CataMazeBatchEnv(num_envs, int(config["seed"]))

    agent_steps = 0
    started = perf_counter()
    for _tick in range(arguments.ticks):
        observation = environment.observation
        actions = np.argmax(observation["action_mask"], axis=-1).astype(np.uint8)
        actions[~observation["alive"]] = 8
        environment.step(actions)
        agent_steps += int(observation["alive"].sum())
        environment.reset_finished()
    elapsed = perf_counter() - started
    print(
        json.dumps(
            {
                "num_envs": num_envs,
                "ticks": arguments.ticks,
                "agent_steps": agent_steps,
                "elapsed_seconds": elapsed,
                "agent_steps_per_second": agent_steps / elapsed,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
