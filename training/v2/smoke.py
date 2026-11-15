# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 21:09 EST
# Last Modified by: Codex
# Runs bounded end-to-end V2 recurrent PPO without touching V1 configs or artifacts.

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
from time import perf_counter
from typing import Any

import numpy as np
import torch

from training.collector import RolloutCollector
from training.env import CataMazeBatchEnv
from training.ppo import PPOConfig
from training.reward import REWARD_VERSION as V2_REWARD_VERSION
from training.v2.checkpoint import (
    CHECKPOINT_FORMAT_VERSION,
    load_checkpoint,
    save_checkpoint,
)
from training.v2 import MODEL_ARCH_VERSION, PERSONA_HEADS_MODEL_ARCH_VERSION
from training.v2.env import PersonaV3BatchEnv
from training.v2.migrate import MIGRATION_FORMAT, file_sha256
from training.v2.model import PersonaRecurrentActorCritic, neutralize_persona_trunk
from training.v2.ppo import PersonaPPOTrainer
from training.v2.schedule import TrainingPhase, apply_training_phase
from training.v2.reward import REWARD_VERSION as V3_REWARD_VERSION


def run_smoke(
    warmstart: str | Path,
    *,
    target_agent_steps: int,
    output_dir: Path,
    device: torch.device,
    seed: int = 20261114,
    num_envs: int = 4,
    environment_steps: int = 8,
    sequence_length: int = 4,
    sequences_per_batch: int = 12,
    update_epochs: int = 2,
    allow_provisional: bool = False,
    reward_version: str = V2_REWARD_VERSION,
    phase: TrainingPhase = TrainingPhase.HEADS_ONLY,
    curriculum_stage: str = "A",
    learning_rate: float = 3e-4,
    style_loss_coef: float = 0.0,
) -> dict[str, Any]:
    if target_agent_steps <= 0:
        raise ValueError("target_agent_steps must be positive")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device.type == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA V2 smoke requested but CUDA is unavailable")
        torch.cuda.manual_seed_all(seed)
    warmstart_path = Path(warmstart)
    warmstart_payload = torch.load(warmstart_path, map_location="cpu", weights_only=False)
    if warmstart_payload.get("format") == MIGRATION_FORMAT:
        source_lineage = warmstart_payload["lineage"]
    elif warmstart_payload.get("format") == CHECKPOINT_FORMAT_VERSION:
        source_lineage = warmstart_payload["resolved_config"]["source_lineage"]
    else:
        raise ValueError("V2 smoke requires a warm-start or V2 checkpoint")
    if source_lineage["provisional"] and not allow_provisional:
        raise ValueError("provisional V2 warm-start requires explicit opt-in")
    if reward_version not in (V2_REWARD_VERSION, V3_REWARD_VERSION):
        raise ValueError("unsupported V2 smoke reward version")
    if not 0.0 <= style_loss_coef <= 0.1:
        raise ValueError("V2 style loss coefficient must be in [0,0.1]")
    if reward_version == V3_REWARD_VERSION:
        allowed_stages = {
            TrainingPhase.HEADS_ONLY: ("C",),
            TrainingPhase.HEADS_NEUTRAL: ("C",),
            TrainingPhase.RECURRENT: (),
            TrainingPhase.FULL: ("C",),
        }
    else:
        allowed_stages = {
            TrainingPhase.HEADS_ONLY: ("A",),
            TrainingPhase.HEADS_NEUTRAL: (),
            TrainingPhase.RECURRENT: ("B",),
            TrainingPhase.FULL: ("C", "D"),
        }
    if curriculum_stage not in allowed_stages[phase]:
        raise ValueError("V2 smoke phase/curriculum combination is invalid")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "checkpoints").mkdir(exist_ok=True)
    model = PersonaRecurrentActorCritic().to(device)
    model.load_state_dict(warmstart_payload["model"])
    if phase is TrainingPhase.HEADS_NEUTRAL:
        neutralize_persona_trunk(model)
        model_arch_version = PERSONA_HEADS_MODEL_ARCH_VERSION
    else:
        model_arch_version = MODEL_ARCH_VERSION
    trainable_names = apply_training_phase(model, phase)
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
        num_envs,
        seed,
        curriculum_stage=curriculum_stage,
        randomize_spawns=True,
    )
    collector = RolloutCollector(environment, model, device=device)
    generator = torch.Generator(device=device.type).manual_seed(seed)
    trainer = PersonaPPOTrainer(
        model,
        optimizer,
        PPOConfig(
            update_epochs=update_epochs,
            sequence_length=sequence_length,
            sequences_per_batch=sequences_per_batch,
        ),
        device=device,
        style_loss_coef=style_loss_coef,
    )
    resolved_config = {
        "schema": "catamaze.training.persona.v2-smoke",
        "seed": seed,
        "device": str(device),
        "num_envs": num_envs,
        "environment_steps": environment_steps,
        "sequence_length": sequence_length,
        "sequences_per_batch": sequences_per_batch,
        "update_epochs": update_epochs,
        "phase": phase.value,
        "reward_version": reward_version,
        "curriculum_stage": curriculum_stage,
        "learning_rate": learning_rate,
        "style_loss_coef": style_loss_coef,
        "warmstart_sha256": file_sha256(warmstart_path),
        "source_lineage": source_lineage,
        "model_arch_version": model_arch_version,
    }
    (output_dir / "resolved_config.json").write_text(
        json.dumps(resolved_config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    before = {
        name: parameter.detach().cpu().clone()
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    }
    agent_steps = 0
    updates = 0
    started = perf_counter()
    metrics_path = output_dir / "metrics.jsonl"
    while agent_steps < target_agent_steps:
        rollout, collection = collector.collect(
            environment_steps,
            gamma=0.995,
            gae_lambda=0.95,
            generator=generator,
        )
        if collection.invalid_actions != 0:
            raise RuntimeError("V2 smoke sampled an illegal action")
        metrics = trainer.update(rollout, generator=generator)
        agent_steps += collection.agent_steps
        updates += 1
        record = {
            "agent_steps": agent_steps,
            "update": updates,
            "completed_episodes": collection.completed_episodes,
            "reward_sum": collection.reward_sum,
            **metrics.as_dict(),
        }
        with metrics_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
        checkpoint = output_dir / "checkpoints" / "latest.pt"
        save_checkpoint(
            checkpoint,
            model=model,
            optimizer=optimizer,
            environment=environment,
            collector=collector,
            policy_generator=generator,
            training_state={
                "agent_steps": agent_steps,
                "update": updates,
                "phase": phase.value,
            },
            resolved_config=resolved_config,
            reward_version=reward_version,
            model_arch_version=model_arch_version,
        )
        load_checkpoint(
            checkpoint,
            model=model,
            optimizer=optimizer,
            environment=environment,
            collector=collector,
            policy_generator=generator,
            reward_version=reward_version,
            model_arch_version=model_arch_version,
        )
    elapsed = perf_counter() - started
    changed = {
        name: not torch.equal(before[name], parameter.detach().cpu())
        for name, parameter in model.named_parameters()
        if name in before
    }
    for persona in range(3):
        if not any(
            value
            for name, value in changed.items()
            if name.startswith(f"actors.{persona}.")
            or name.startswith(f"critics.{persona}.")
        ):
            raise RuntimeError(f"V2 smoke did not update persona head {persona}")
    summary = {
        "schema": "catamaze.training.persona.v2-smoke-result",
        "agent_steps": agent_steps,
        "updates": updates,
        "elapsed_seconds": elapsed,
        "agent_steps_per_second": agent_steps / elapsed,
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "trainable_parameter_count": sum(
            parameter.numel() for parameter in model.parameters() if parameter.requires_grad
        ),
        "trainable_names": trainable_names,
        "checkpoint": str(output_dir / "checkpoints" / "latest.pt"),
        "checkpoint_sha256": file_sha256(output_dir / "checkpoints" / "latest.pt"),
        "source_lineage": source_lineage,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warmstart", required=True)
    parser.add_argument("--agent-steps", type=int, default=100_000)
    parser.add_argument("--output", default=".artifacts/v2/smoke")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--num-envs", type=int, default=4)
    parser.add_argument("--environment-steps", type=int, default=8)
    parser.add_argument("--sequence-length", type=int, default=4)
    parser.add_argument("--sequences-per-batch", type=int, default=12)
    parser.add_argument("--update-epochs", type=int, default=2)
    parser.add_argument("--allow-provisional", action="store_true")
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
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--style-loss-coef", type=float, default=0.0)
    arguments = parser.parse_args()
    summary = run_smoke(
        arguments.warmstart,
        target_agent_steps=arguments.agent_steps,
        output_dir=Path(arguments.output),
        device=torch.device(arguments.device),
        num_envs=arguments.num_envs,
        environment_steps=arguments.environment_steps,
        sequence_length=arguments.sequence_length,
        sequences_per_batch=arguments.sequences_per_batch,
        update_epochs=arguments.update_epochs,
        allow_provisional=arguments.allow_provisional,
        reward_version=arguments.reward_version,
        phase=TrainingPhase(arguments.phase),
        curriculum_stage=arguments.curriculum_stage,
        learning_rate=arguments.learning_rate,
        style_loss_coef=arguments.style_loss_coef,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
