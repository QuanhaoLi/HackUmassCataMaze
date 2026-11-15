# Created at: 2026-11-14 19:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 19:04 EST
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
from training.v2.checkpoint import load_checkpoint, save_checkpoint
from training.v2.migrate import MIGRATION_FORMAT, file_sha256
from training.v2.model import PersonaRecurrentActorCritic
from training.v2.ppo import PersonaPPOTrainer
from training.v2.schedule import TrainingPhase, apply_training_phase


def run_smoke(
    warmstart: str | Path,
    *,
    target_agent_steps: int,
    output_dir: Path,
    device: torch.device,
    seed: int = 20261114,
    num_envs: int = 4,
    environment_steps: int = 8,
    allow_provisional: bool = False,
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
    if warmstart_payload.get("format") != MIGRATION_FORMAT:
        raise ValueError("V2 smoke requires a migrated warm-start checkpoint")
    if warmstart_payload["lineage"]["provisional"] and not allow_provisional:
        raise ValueError("provisional V2 warm-start requires explicit opt-in")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "checkpoints").mkdir(exist_ok=True)
    model = PersonaRecurrentActorCritic().to(device)
    model.load_state_dict(warmstart_payload["model"])
    phase = TrainingPhase.HEADS_ONLY
    trainable_names = apply_training_phase(model, phase)
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=3e-4,
        eps=1e-5,
        weight_decay=1e-4,
    )
    environment = CataMazeBatchEnv(
        num_envs,
        seed,
        curriculum_stage="A",
        randomize_spawns=True,
    )
    collector = RolloutCollector(environment, model, device=device)
    generator = torch.Generator(device=device.type).manual_seed(seed)
    trainer = PersonaPPOTrainer(
        model,
        optimizer,
        PPOConfig(
            update_epochs=2,
            sequence_length=4,
            sequences_per_batch=12,
        ),
        device=device,
    )
    resolved_config = {
        "schema": "catamaze.training.persona.v2-smoke",
        "seed": seed,
        "device": str(device),
        "num_envs": num_envs,
        "environment_steps": environment_steps,
        "phase": phase.value,
        "warmstart_sha256": file_sha256(warmstart_path),
        "source_lineage": warmstart_payload["lineage"],
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
        )
        load_checkpoint(
            checkpoint,
            model=model,
            optimizer=optimizer,
            environment=environment,
            collector=collector,
            policy_generator=generator,
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
        "source_lineage": warmstart_payload["lineage"],
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
    parser.add_argument("--allow-provisional", action="store_true")
    arguments = parser.parse_args()
    summary = run_smoke(
        arguments.warmstart,
        target_agent_steps=arguments.agent_steps,
        output_dir=Path(arguments.output),
        device=torch.device(arguments.device),
        allow_provisional=arguments.allow_provisional,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
