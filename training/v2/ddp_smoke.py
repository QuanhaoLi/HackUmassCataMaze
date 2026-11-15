# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 20:25 EST
# Last Modified by: Codex
# Qualifies one persona-balanced V2 model with synchronous multi-V100 DDP.

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
from time import perf_counter
from typing import Any

import numpy as np
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel

from training.collector import RolloutCollector
from training.env import CataMazeBatchEnv
from training.ppo import PPOConfig
from training.v2.checkpoint import CHECKPOINT_FORMAT_VERSION, save_checkpoint
from training.v2.env import PersonaV3BatchEnv
from training.v2.migrate import MIGRATION_FORMAT, file_sha256
from training.v2.model import PersonaRecurrentActorCritic
from training.v2.ppo import PersonaPPOTrainer
from training.v2.schedule import TrainingPhase, apply_training_phase
from training.v2.reward import REWARD_VERSION as V3_REWARD_VERSION
from training.reward import REWARD_VERSION as V2_REWARD_VERSION


def _rank() -> int:
    return int(os.environ["RANK"])


def _local_rank() -> int:
    return int(os.environ["LOCAL_RANK"])


def _world_size() -> int:
    return int(os.environ["WORLD_SIZE"])


def _global_sum(value: float, device: torch.device) -> float:
    tensor = torch.tensor(value, device=device, dtype=torch.float64)
    dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
    return float(tensor)


def _global_max(value: float, device: torch.device) -> float:
    tensor = torch.tensor(value, device=device, dtype=torch.float64)
    dist.all_reduce(tensor, op=dist.ReduceOp.MAX)
    return float(tensor)


def run(
    warmstart: Path,
    *,
    output_dir: Path,
    target_agent_steps: int,
    num_envs_per_rank: int,
    environment_steps: int,
    sequence_length: int,
    sequences_per_batch_per_rank: int,
    update_epochs: int,
    seed: int,
    phase: TrainingPhase,
    curriculum_stage: str,
    learning_rate: float,
    reward_version: str,
) -> dict[str, Any] | None:
    rank = _rank()
    local_rank = _local_rank()
    world_size = _world_size()
    if world_size != 4:
        raise ValueError("V2 DDP qualification requires exactly four ranks")
    if learning_rate <= 0:
        raise ValueError("V2 learning rate must be positive")
    if reward_version not in (V2_REWARD_VERSION, V3_REWARD_VERSION):
        raise ValueError("unsupported V2 reward version")
    if reward_version == V3_REWARD_VERSION:
        allowed_stages = {
            TrainingPhase.HEADS_ONLY: ("C",),
            TrainingPhase.RECURRENT: (),
            TrainingPhase.FULL: ("C",),
        }
    else:
        allowed_stages = {
            TrainingPhase.HEADS_ONLY: ("A",),
            TrainingPhase.RECURRENT: ("B",),
            TrainingPhase.FULL: ("C", "D"),
        }
    if curriculum_stage not in allowed_stages[phase]:
        raise ValueError(
            f"V2 phase {phase.value} cannot use curriculum stage {curriculum_stage}"
        )
    torch.cuda.set_device(local_rank)
    device = torch.device("cuda", local_rank)
    dist.init_process_group(backend="nccl")
    try:
        rank_seed = seed + rank * 100_003
        random.seed(rank_seed)
        np.random.seed(rank_seed)
        torch.manual_seed(rank_seed)
        torch.cuda.manual_seed_all(rank_seed)
        torch.backends.cuda.matmul.allow_tf32 = True
        if rank == 0:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "checkpoints").mkdir(exist_ok=True)
        dist.barrier(device_ids=[local_rank])

        payload = torch.load(warmstart, map_location="cpu", weights_only=False)
        if payload.get("format") == MIGRATION_FORMAT:
            source_lineage = payload["lineage"]
        elif payload.get("format") == CHECKPOINT_FORMAT_VERSION:
            source_lineage = payload["resolved_config"]["source_lineage"]
        else:
            raise ValueError("DDP qualification requires a V2 warm-start or checkpoint")
        if source_lineage["provisional"]:
            raise ValueError("DDP qualification rejects provisional lineage")
        model = PersonaRecurrentActorCritic().to(device)
        model.load_state_dict(payload["model"])
        trainable_names = apply_training_phase(model, phase)
        ddp_model = DistributedDataParallel(
            model,
            device_ids=[local_rank],
            output_device=local_rank,
            broadcast_buffers=False,
        )
        optimizer = torch.optim.AdamW(
            [parameter for parameter in model.parameters() if parameter.requires_grad],
            lr=learning_rate,
            eps=1e-5,
            weight_decay=1e-4,
        )
        environment_type = (
            PersonaV3BatchEnv if reward_version == V3_REWARD_VERSION else CataMazeBatchEnv
        )
        environment = environment_type(
            num_envs_per_rank,
            rank_seed,
            curriculum_stage=curriculum_stage,
            randomize_spawns=True,
        )
        collector = RolloutCollector(environment, ddp_model, device=device)
        generator = torch.Generator(device="cuda").manual_seed(rank_seed)
        trainer = PersonaPPOTrainer(
            ddp_model,
            optimizer,
            PPOConfig(
                update_epochs=update_epochs,
                sequence_length=sequence_length,
                sequences_per_batch=sequences_per_batch_per_rank,
            ),
            device=device,
        )
        resolved_config = {
            "schema": "catamaze.training.persona.v2-ddp-qualification",
            "world_size": world_size,
            "num_envs_per_rank": num_envs_per_rank,
            "global_num_envs": num_envs_per_rank * world_size,
            "environment_steps": environment_steps,
            "sequence_length": sequence_length,
            "sequences_per_batch_per_rank": sequences_per_batch_per_rank,
            "global_minibatch_sequences": sequences_per_batch_per_rank * world_size,
            "update_epochs": update_epochs,
            "seed": seed,
            "phase": phase.value,
            "curriculum_stage": curriculum_stage,
            "learning_rate": learning_rate,
            "reward_version": reward_version,
            "warmstart_sha256": file_sha256(warmstart),
            "source_lineage": source_lineage,
        }
        if rank == 0:
            (output_dir / "resolved_config.json").write_text(
                json.dumps(resolved_config, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        global_agent_steps = 0
        updates = 0
        maximum_kl = 0.0
        started = perf_counter()
        while global_agent_steps < target_agent_steps:
            rollout, collection = collector.collect(
                environment_steps,
                gamma=0.995,
                gae_lambda=0.95,
                generator=generator,
            )
            if collection.invalid_actions != 0:
                raise RuntimeError("V2 DDP qualification sampled an illegal action")
            metrics = trainer.update(rollout, generator=generator)
            global_agent_steps += int(_global_sum(collection.agent_steps, device))
            global_reward = _global_sum(collection.reward_sum, device)
            global_episodes = int(_global_sum(collection.completed_episodes, device))
            updates += 1
            maximum_kl = max(maximum_kl, metrics.max_approx_kl)
            if rank == 0:
                record = {
                    "agent_steps": global_agent_steps,
                    "update": updates,
                    "reward_sum": global_reward,
                    "completed_episodes": global_episodes,
                    **metrics.as_dict(),
                }
                with (output_dir / "metrics.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(record, sort_keys=True) + "\n")

        elapsed = perf_counter() - started
        max_memory = _global_max(torch.cuda.max_memory_allocated(device), device)
        max_reserved = _global_max(torch.cuda.max_memory_reserved(device), device)
        if rank != 0:
            return None
        save_checkpoint(
            output_dir / "checkpoints" / "latest.pt",
            model=model,
            optimizer=optimizer,
            environment=environment,
            collector=collector,
            policy_generator=generator,
            training_state={
                "agent_steps": global_agent_steps,
                "update": updates,
                "phase": phase.value,
                "world_size": world_size,
            },
            resolved_config=resolved_config,
            reward_version=reward_version,
        )
        summary = {
            "schema": "catamaze.training.persona.v2-ddp-qualification-result",
            "agent_steps": global_agent_steps,
            "updates": updates,
            "elapsed_seconds": elapsed,
            "agent_steps_per_second": global_agent_steps / elapsed,
            "max_approx_kl": maximum_kl,
            "cuda_max_memory_allocated": int(max_memory),
            "cuda_max_memory_reserved": int(max_reserved),
            "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
            "trainable_names": trainable_names,
            "checkpoint": str(output_dir / "checkpoints" / "latest.pt"),
            "checkpoint_sha256": file_sha256(output_dir / "checkpoints" / "latest.pt"),
            "phase": phase.value,
            "source_lineage": source_lineage,
        }
        (output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return summary
    finally:
        if dist.is_initialized():
            dist.destroy_process_group()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warmstart", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--agent-steps", type=int, default=1_000_000)
    parser.add_argument("--num-envs-per-rank", type=int, default=64)
    parser.add_argument("--environment-steps", type=int, default=128)
    parser.add_argument("--sequence-length", type=int, default=64)
    parser.add_argument("--sequences-per-batch-per-rank", type=int, default=30)
    parser.add_argument("--update-epochs", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261114)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument(
        "--reward-version",
        choices=(V2_REWARD_VERSION, V3_REWARD_VERSION),
        default=V2_REWARD_VERSION,
    )
    parser.add_argument(
        "--phase",
        choices=[phase.value for phase in TrainingPhase],
        default=TrainingPhase.HEADS_ONLY.value,
    )
    parser.add_argument(
        "--curriculum-stage", choices=("A", "B", "C", "D"), default="A"
    )
    arguments = parser.parse_args()
    summary = run(
        Path(arguments.warmstart),
        output_dir=Path(arguments.output),
        target_agent_steps=arguments.agent_steps,
        num_envs_per_rank=arguments.num_envs_per_rank,
        environment_steps=arguments.environment_steps,
        sequence_length=arguments.sequence_length,
        sequences_per_batch_per_rank=arguments.sequences_per_batch_per_rank,
        update_epochs=arguments.update_epochs,
        seed=arguments.seed,
        phase=TrainingPhase(arguments.phase),
        curriculum_stage=arguments.curriculum_stage,
        learning_rate=arguments.learning_rate,
        reward_version=arguments.reward_version,
    )
    if summary is not None:
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
