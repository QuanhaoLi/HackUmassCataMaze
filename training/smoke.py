# Created at: 2026-11-14 04:38 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:38 EST
# Last Modified by: Codex
# Runs bounded end-to-end recurrent-PPO correctness qualification.

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import platform
from pathlib import Path
import random
import subprocess
from time import perf_counter
from typing import Any

import numpy as np
import torch
import yaml

from training.checkpoint import load_checkpoint, save_checkpoint
from training.collector import RolloutCollector
from training.config import load_config
from training.env import CataMazeBatchEnv
from training.model import RecurrentActorCritic
from training.ppo import PPOConfig, PPOTrainer


def _git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_smoke(
    config: dict[str, Any],
    *,
    target_agent_steps: int,
    device: torch.device,
    output_dir: Path,
) -> dict[str, Any]:
    seed = int(config["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device.type == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA smoke requested but CUDA is unavailable")
        torch.cuda.manual_seed_all(seed)
        torch.backends.cuda.matmul.allow_tf32 = bool(config["precision"]["allow_tf32"])
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "checkpoints").mkdir(exist_ok=True)
    resolved = deepcopy(config)
    resolved["device"] = str(device)
    (output_dir / "resolved_config.yaml").write_text(
        yaml.safe_dump(resolved, sort_keys=True), encoding="utf-8"
    )
    _write_json(
        output_dir / "metadata.json",
        {
            "git_commit": _git_revision(),
            "versions": config["versions"],
            "seed": seed,
            "device": str(device),
            "device_name": (
                torch.cuda.get_device_name(device) if device.type == "cuda" else platform.processor()
            ),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "parameter_count": None,
            "target_agent_steps": target_agent_steps,
        },
    )

    environment = CataMazeBatchEnv(
        int(config["environment"]["num_envs"]),
        seed,
        randomize_spawns=bool(config["environment"]["randomize_spawns"]),
    )
    model = RecurrentActorCritic().to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["ppo"]["learning_rate"]),
        eps=float(config["ppo"]["adam_eps"]),
        weight_decay=float(config["ppo"]["weight_decay"]),
    )
    collector = RolloutCollector(environment, model, device=device)
    trainer = PPOTrainer(
        model,
        optimizer,
        PPOConfig(
            update_epochs=int(config["minibatch"]["update_epochs"]),
            sequence_length=int(config["rollout"]["sequence_length"]),
            sequences_per_batch=int(config["minibatch"]["sequences"]),
            clip_coef=float(config["ppo"]["clip_coef"]),
            value_clip_coef=float(config["ppo"]["value_clip_coef"]),
            value_loss_coef=float(config["ppo"]["value_loss_coef"]),
            entropy_coef=float(config["ppo"]["entropy_coef"]),
            max_grad_norm=float(config["ppo"]["max_grad_norm"]),
            hard_stop_kl=float(config["ppo"]["hard_stop_kl"]),
        ),
        device=device,
    )
    generator = torch.Generator(device=device.type).manual_seed(seed)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    metadata["parameter_count"] = parameter_count
    _write_json(output_dir / "metadata.json", metadata)

    global_agent_steps = 0
    update_index = 0
    started = perf_counter()
    metrics_path = output_dir / "metrics.jsonl"
    while global_agent_steps < target_agent_steps:
        rollout, collection = collector.collect(
            int(config["rollout"]["environment_steps"]),
            gamma=float(config["ppo"]["gamma"]),
            gae_lambda=float(config["ppo"]["gae_lambda"]),
            generator=generator,
        )
        if collection.invalid_actions != 0:
            raise RuntimeError("smoke sampled an illegal action")
        component_total = sum(collection.component_sums.values())
        if not np.isclose(component_total, collection.reward_sum, atol=1e-4):
            raise RuntimeError("reward components do not sum to total reward")
        update_metrics = trainer.update(rollout, generator=generator)
        global_agent_steps += collection.agent_steps
        update_index += 1
        record = {
            "update": update_index,
            "agent_steps": global_agent_steps,
            "collection_agent_steps": collection.agent_steps,
            "completed_episodes": collection.completed_episodes,
            "reward_sum": collection.reward_sum,
            "reward_components": collection.component_sums,
            **update_metrics.as_dict(),
        }
        if device.type == "cuda":
            record["cuda_max_memory_allocated"] = torch.cuda.max_memory_allocated(device)
            record["cuda_max_memory_reserved"] = torch.cuda.max_memory_reserved(device)
            if record["cuda_max_memory_allocated"] >= 14 * 1024**3:
                raise RuntimeError("allocated CUDA memory reached the 14GB safety ceiling")
        with metrics_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
        checkpoint_path = output_dir / "checkpoints" / "latest.pt"
        save_checkpoint(
            checkpoint_path,
            model=model,
            optimizer=optimizer,
            environment=environment,
            collector=collector,
            policy_generator=generator,
            training_state={
                "agent_steps": global_agent_steps,
                "update": update_index,
                "curriculum_stage": environment.curriculum_stage,
            },
            resolved_config=resolved,
        )
        load_checkpoint(
            checkpoint_path,
            model=model,
            optimizer=optimizer,
            environment=environment,
            collector=collector,
            policy_generator=generator,
        )
    elapsed = perf_counter() - started
    return {
        "agent_steps": global_agent_steps,
        "updates": update_index,
        "elapsed_seconds": elapsed,
        "agent_steps_per_second": global_agent_steps / elapsed,
        "parameter_count": parameter_count,
        "checkpoint": str(output_dir / "checkpoints" / "latest.pt"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl/ppo_16gb.yaml")
    parser.add_argument("--agent-steps", type=int, default=100_000)
    parser.add_argument("--device", choices=("cpu", "cuda"))
    parser.add_argument("--output", default=".artifacts/rl-smoke")
    arguments = parser.parse_args()
    config = load_config(arguments.config)
    device = torch.device(arguments.device or config["device"])
    summary = run_smoke(
        config,
        target_agent_steps=arguments.agent_steps,
        device=device,
        output_dir=Path(arguments.output),
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
