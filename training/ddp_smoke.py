# Created at: 2026-11-14 06:50 EST
# Created by: Codex
# Last Modified at: 2026-11-14 06:55 EST
# Last Modified by: Codex
# Qualifies synchronized PPO training of one model across multiple ranks.

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import random
from time import perf_counter
from typing import Any

import numpy as np
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel

from training.collector import RolloutCollector
from training.config import load_config
from training.env import CataMazeBatchEnv
from training.model import RecurrentActorCritic
from training.ppo import PPOConfig, PPOTrainer
from training.reward import COMPONENT_NAMES


def _atomic_torch_save(value: Any, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    torch.save(value, temporary)
    os.replace(temporary, destination)


def _barrier(device: torch.device) -> None:
    if device.type == "cuda":
        dist.barrier(device_ids=[device.index])
    else:
        dist.barrier()


def _reduce_sum(values: list[float], device: torch.device) -> list[float]:
    tensor = torch.tensor(values, dtype=torch.float64, device=device)
    dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
    return tensor.cpu().tolist()


def _write_rank_checkpoint(
    output_dir: Path,
    *,
    rank: int,
    environment: CataMazeBatchEnv,
    collector: RolloutCollector,
    generator: torch.Generator,
    global_agent_steps: int,
) -> None:
    _atomic_torch_save(
        {
            "rank": rank,
            "global_agent_steps": global_agent_steps,
            "environment": environment.state_dict(),
            "collector": collector.state_dict(),
            "policy_generator": generator.get_state(),
            "python_rng": random.getstate(),
            "numpy_rng": np.random.get_state(),
            "torch_cpu_rng": torch.get_rng_state(),
            "torch_cuda_rng": torch.cuda.get_rng_state() if torch.cuda.is_available() else None,
        },
        output_dir / "checkpoints" / f"latest-rank{rank}.pt",
    )


def run(arguments: argparse.Namespace) -> None:
    dist.init_process_group(backend=arguments.backend)
    rank = dist.get_rank()
    world_size = dist.get_world_size()
    local_rank = int(os.environ.get("LOCAL_RANK", rank))
    if arguments.backend == "nccl":
        torch.cuda.set_device(local_rank)
        device = torch.device("cuda", local_rank)
    else:
        device = torch.device("cpu")

    config = load_config(arguments.config)
    expected_world_size = int(config["distributed"]["world_size"])
    if arguments.backend == "nccl" and world_size != expected_world_size:
        raise RuntimeError(f"expected {expected_world_size} DDP ranks, got {world_size}")
    global_num_envs = arguments.num_envs or int(config["distributed"]["global_num_envs"])
    global_minibatch = arguments.minibatch_sequences or int(
        config["distributed"]["global_minibatch_sequences"]
    )
    if global_num_envs % world_size != 0 or global_minibatch % world_size != 0:
        raise ValueError("global environments and minibatch sequences must divide world_size")

    seed = int(config["seed"])
    rank_seed = seed + rank * 1_000_003
    random.seed(rank_seed)
    np.random.seed(rank_seed % (2**32))
    torch.manual_seed(seed)
    if device.type == "cuda":
        torch.cuda.manual_seed(rank_seed)
        torch.backends.cuda.matmul.allow_tf32 = bool(config["precision"]["allow_tf32"])

    output_dir = Path(arguments.output)
    if rank == 0:
        if output_dir.exists() and any(output_dir.iterdir()):
            raise FileExistsError(f"DDP output directory is non-empty: {output_dir}")
        (output_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
        metadata = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "world_size": world_size,
            "global_num_envs": global_num_envs,
            "global_minibatch_sequences": global_minibatch,
            "target_agent_steps": arguments.agent_steps,
            "backend": arguments.backend,
            "training_config": config["versions"]["training_config"],
        }
        (output_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    _barrier(device)

    base_model = RecurrentActorCritic().to(device)
    ddp_model = DistributedDataParallel(
        base_model,
        device_ids=[local_rank] if device.type == "cuda" else None,
        output_device=local_rank if device.type == "cuda" else None,
    )
    optimizer = torch.optim.AdamW(
        ddp_model.parameters(),
        lr=float(config["ppo"]["learning_rate"]),
        eps=float(config["ppo"]["adam_eps"]),
        weight_decay=float(config["ppo"]["weight_decay"]),
    )
    environment = CataMazeBatchEnv(
        global_num_envs // world_size,
        rank_seed,
        randomize_spawns=bool(config["environment"]["randomize_spawns"]),
    )
    collector = RolloutCollector(environment, ddp_model, device=device)
    trainer = PPOTrainer(
        ddp_model,
        optimizer,
        PPOConfig(
            update_epochs=int(config["minibatch"]["update_epochs"]),
            sequence_length=int(config["rollout"]["sequence_length"]),
            sequences_per_batch=global_minibatch // world_size,
            clip_coef=float(config["ppo"]["clip_coef"]),
            value_clip_coef=float(config["ppo"]["value_clip_coef"]),
            value_loss_coef=float(config["ppo"]["value_loss_coef"]),
            entropy_coef=float(config["ppo"]["entropy_coef"]),
            max_grad_norm=float(config["ppo"]["max_grad_norm"]),
            hard_stop_kl=float(config["ppo"]["hard_stop_kl"]),
        ),
        device=device,
    )
    policy_generator = torch.Generator(device=device.type).manual_seed(rank_seed)

    global_agent_steps = 0
    update_index = 0
    started = perf_counter()
    while global_agent_steps < arguments.agent_steps:
        rollout, collection = collector.collect(
            int(config["rollout"]["environment_steps"]),
            gamma=float(config["ppo"]["gamma"]),
            gae_lambda=float(config["ppo"]["gae_lambda"]),
            generator=policy_generator,
        )
        update = trainer.update(rollout, generator=policy_generator)
        reduced = _reduce_sum(
            [
                float(collection.agent_steps),
                collection.reward_sum,
                float(collection.completed_episodes),
                *[collection.component_sums.get(name, 0.0) for name in COMPONENT_NAMES],
            ],
            device,
        )
        global_agent_steps += int(reduced[0])
        update_index += 1
        local_memory = float(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else 0.0
        memory = torch.tensor(local_memory, dtype=torch.float64, device=device)
        dist.all_reduce(memory, op=dist.ReduceOp.MAX)

        _write_rank_checkpoint(
            output_dir,
            rank=rank,
            environment=environment,
            collector=collector,
            generator=policy_generator,
            global_agent_steps=global_agent_steps,
        )
        if rank == 0:
            _atomic_torch_save(
                {
                    "format": "catamaze.ddp-smoke.v1",
                    "world_size": world_size,
                    "global_agent_steps": global_agent_steps,
                    "update": update_index,
                    "model": base_model.state_dict(),
                    "optimizer": optimizer.state_dict(),
                    "config": config,
                },
                output_dir / "checkpoints" / "latest.pt",
            )
            record = {
                "update": update_index,
                "agent_steps": global_agent_steps,
                "agent_steps_per_second": global_agent_steps / (perf_counter() - started),
                "completed_episodes": int(reduced[2]),
                "reward_sum": reduced[1],
                "reward_components": {
                    name: reduced[3 + index] for index, name in enumerate(COMPONENT_NAMES)
                },
                "max_cuda_memory_allocated": int(memory.item()),
                **update.as_dict(),
            }
            with (output_dir / "metrics.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            print(json.dumps(record, sort_keys=True), flush=True)
        _barrier(device)

    parameter_checksum = torch.stack(
        [parameter.detach().double().sum() for parameter in base_model.parameters()]
    ).sum()
    minimum = parameter_checksum.clone()
    maximum = parameter_checksum.clone()
    dist.all_reduce(minimum, op=dist.ReduceOp.MIN)
    dist.all_reduce(maximum, op=dist.ReduceOp.MAX)
    if not torch.equal(minimum, maximum):
        raise RuntimeError("DDP ranks ended with different model parameters")
    _barrier(device)
    dist.destroy_process_group()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl/ppo_16gb.yaml")
    parser.add_argument("--agent-steps", type=int, default=100_000)
    parser.add_argument("--num-envs", type=int)
    parser.add_argument("--minibatch-sequences", type=int)
    parser.add_argument("--backend", choices=("nccl", "gloo"), default="nccl")
    parser.add_argument("--output", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
