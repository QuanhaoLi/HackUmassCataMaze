# Created at: 2026-11-14 04:46 EST
# Created by: Codex
# Last Modified at: 2026-11-14 05:02 EST
# Last Modified by: Codex
# Runs resumable production recurrent-PPO training with fixed evaluation gates.

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import random
import re
import shutil
import subprocess
from time import perf_counter
from typing import Any

import numpy as np
import torch
from torch.utils.tensorboard import SummaryWriter
import yaml

from training.checkpoint import load_checkpoint, save_checkpoint
from training.collector import RolloutCollector
from training.config import load_config
from training.curriculum import CurriculumController
from training.env import CataMazeBatchEnv
from training.evaluator import evaluate_policy
from training.model import RecurrentActorCritic
from training.opponents import OpponentStrategy
from training.ppo import PPOConfig, PPOTrainer


RUN_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _git_revision() -> tuple[str, bool]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"], check=True, capture_output=True, text=True
        ).stdout
    )
    return revision, dirty


def _linear(start: float, end: float, progress: float) -> float:
    bounded = min(max(progress, 0.0), 1.0)
    return start + (end - start) * bounded


def _ppo_config(config: dict[str, Any], entropy_coef: float) -> PPOConfig:
    return PPOConfig(
        update_epochs=int(config["minibatch"]["update_epochs"]),
        sequence_length=int(config["rollout"]["sequence_length"]),
        sequences_per_batch=int(config["minibatch"]["sequences"]),
        clip_coef=float(config["ppo"]["clip_coef"]),
        value_clip_coef=float(config["ppo"]["value_clip_coef"]),
        value_loss_coef=float(config["ppo"]["value_loss_coef"]),
        entropy_coef=entropy_coef,
        max_grad_norm=float(config["ppo"]["max_grad_norm"]),
        hard_stop_kl=float(config["ppo"]["hard_stop_kl"]),
    )


def _stage_reports(
    model: RecurrentActorCritic,
    config: dict[str, Any],
    controller: CurriculumController,
    *,
    device: torch.device,
    evaluation_index: int,
) -> dict[str, dict[str, Any]]:
    opponents = config["curriculum"][controller.stage]["evaluation_opponents"]
    episodes = int(config["evaluation"]["episodes_per_persona_per_opponent"])
    reports: dict[str, dict[str, Any]] = {}
    for name in opponents:
        opponent = OpponentStrategy[name.upper()]
        reports[name] = evaluate_policy(
            model,
            episodes=episodes,
            opponent=opponent,
            mode="stochastic",
            seed=int(config["seed"]) + 1_000_000 + evaluation_index * 100 + int(opponent),
            num_envs=min(int(config["environment"]["num_envs"]), episodes),
            device=device,
        )
    return reports


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _save_training_checkpoint(
    run_dir: Path,
    *,
    model: RecurrentActorCritic,
    optimizer: torch.optim.Optimizer,
    environment: CataMazeBatchEnv,
    collector: RolloutCollector,
    generator: torch.Generator,
    state: dict[str, Any],
    config: dict[str, Any],
    keep_latest: int,
    failure: bool = False,
) -> Path:
    name = "failure.pt" if failure else "latest.pt"
    latest = run_dir / "checkpoints" / name
    save_checkpoint(
        latest,
        model=model,
        optimizer=optimizer,
        environment=environment,
        collector=collector,
        policy_generator=generator,
        training_state=state,
        resolved_config=config,
    )
    if not failure:
        numbered = run_dir / "checkpoints" / f"step-{int(state['agent_steps']):012d}.pt"
        shutil.copy2(latest, numbered)
        numbered_checkpoints = sorted((run_dir / "checkpoints").glob("step-*.pt"))
        for expired in numbered_checkpoints[:-keep_latest]:
            expired.unlink()
    return latest


def train(
    config: dict[str, Any],
    *,
    run_dir: Path,
    device: torch.device,
    resume: Path | None,
) -> None:
    seed = int(config["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device.type == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA training requested but CUDA is unavailable")
        torch.cuda.manual_seed_all(seed)
        torch.backends.cuda.matmul.allow_tf32 = bool(config["precision"]["allow_tf32"])
    for directory in ("checkpoints", "evaluations", "artifacts", "tensorboard"):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)

    resume_state: dict[str, Any] | None = None
    if resume is not None:
        peek = torch.load(resume, map_location="cpu", weights_only=False)
        resume_state = peek["training_state"]
    controller = CurriculumController(
        stage=str(resume_state["curriculum"]["stage"]) if resume_state else "A"
    )
    environment = CataMazeBatchEnv(
        int(config["environment"]["num_envs"]),
        seed,
        curriculum_stage=controller.stage,
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
    generator = torch.Generator(device=device.type).manual_seed(seed)
    state: dict[str, Any] = {
        "agent_steps": 0,
        "update": 0,
        "evaluation_index": 0,
        "next_evaluation": int(config["evaluation"]["every_agent_steps"]),
        "next_checkpoint": int(config["checkpoint"]["every_agent_steps"]),
        "high_kl_updates": 0,
        "learning_rate_scale": 1.0,
        "curriculum": controller.state_dict(),
    }
    if resume is not None:
        state = load_checkpoint(
            resume,
            model=model,
            optimizer=optimizer,
            environment=environment,
            collector=collector,
            policy_generator=generator,
        )
        controller.load_state_dict(state["curriculum"])

    base_ppo = _ppo_config(config, float(config["ppo"]["entropy_coef"]))
    trainer = PPOTrainer(model, optimizer, base_ppo, device=device)
    writer = SummaryWriter(log_dir=run_dir / "tensorboard")
    metrics_path = run_dir / "metrics.jsonl"
    total_agent_steps = int(config["total_agent_steps"])
    started = perf_counter()
    try:
        while int(state["agent_steps"]) < total_agent_steps:
            progress = int(state["agent_steps"]) / total_agent_steps
            learning_rate = _linear(
                float(config["ppo"]["learning_rate"]),
                float(config["ppo"]["final_learning_rate"]),
                progress,
            ) * float(state["learning_rate_scale"])
            entropy_coef = _linear(
                float(config["ppo"]["entropy_coef"]),
                float(config["ppo"]["final_entropy_coef"]),
                progress,
            )
            for group in optimizer.param_groups:
                group["lr"] = learning_rate
            trainer.config = replace(base_ppo, entropy_coef=entropy_coef)

            rollout, collection = collector.collect(
                int(config["rollout"]["environment_steps"]),
                gamma=float(config["ppo"]["gamma"]),
                gae_lambda=float(config["ppo"]["gae_lambda"]),
                generator=generator,
            )
            update = trainer.update(rollout, generator=generator)
            state["agent_steps"] = int(state["agent_steps"]) + collection.agent_steps
            state["update"] = int(state["update"]) + 1
            if update.max_approx_kl > float(config["ppo"]["hard_stop_kl"]):
                state["high_kl_updates"] = int(state["high_kl_updates"]) + 1
            else:
                state["high_kl_updates"] = 0
            if int(state["high_kl_updates"]) >= 10:
                state["learning_rate_scale"] = float(state["learning_rate_scale"]) * 0.5
                state["high_kl_updates"] = 0

            record = {
                "agent_steps": state["agent_steps"],
                "update": state["update"],
                "curriculum_stage": controller.stage,
                "learning_rate": learning_rate,
                "entropy_coef": entropy_coef,
                "agent_steps_per_second": int(state["agent_steps"]) / (perf_counter() - started),
                "completed_episodes": collection.completed_episodes,
                "reward_sum": collection.reward_sum,
                "reward_components": collection.component_sums,
                **update.as_dict(),
            }
            if device.type == "cuda":
                record["cuda_max_memory_allocated"] = torch.cuda.max_memory_allocated(device)
                record["cuda_max_memory_reserved"] = torch.cuda.max_memory_reserved(device)
                if int(record["cuda_max_memory_allocated"]) >= 14 * 1024**3:
                    raise RuntimeError("allocated CUDA memory reached the 14GB safety ceiling")
            with metrics_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            for name, value in update.as_dict().items():
                writer.add_scalar(f"optimization/{name}", value, int(state["agent_steps"]))
            writer.add_scalar("optimization/learning_rate", learning_rate, int(state["agent_steps"]))
            for name, value in collection.component_sums.items():
                writer.add_scalar(f"reward/{name}", value, int(state["agent_steps"]))

            if int(state["agent_steps"]) >= int(state["next_evaluation"]):
                reports = _stage_reports(
                    model,
                    config,
                    controller,
                    device=device,
                    evaluation_index=int(state["evaluation_index"]),
                )
                evaluation_path = (
                    run_dir
                    / "evaluations"
                    / f"step-{int(state['agent_steps']):012d}-{controller.stage}.json"
                )
                _write_json(evaluation_path, reports)
                promoted = controller.try_promote(int(state["agent_steps"]), reports)
                if promoted:
                    environment.set_curriculum_stage(controller.stage)
                state["curriculum"] = controller.state_dict()
                state["evaluation_index"] = int(state["evaluation_index"]) + 1
                interval = int(config["evaluation"]["every_agent_steps"])
                while int(state["next_evaluation"]) <= int(state["agent_steps"]):
                    state["next_evaluation"] = int(state["next_evaluation"]) + interval

            if int(state["agent_steps"]) >= int(state["next_checkpoint"]):
                _save_training_checkpoint(
                    run_dir,
                    model=model,
                    optimizer=optimizer,
                    environment=environment,
                    collector=collector,
                    generator=generator,
                    state=state,
                    config=config,
                    keep_latest=int(config["checkpoint"]["keep_latest"]),
                )
                interval = int(config["checkpoint"]["every_agent_steps"])
                while int(state["next_checkpoint"]) <= int(state["agent_steps"]):
                    state["next_checkpoint"] = int(state["next_checkpoint"]) + interval
        _save_training_checkpoint(
            run_dir,
            model=model,
            optimizer=optimizer,
            environment=environment,
            collector=collector,
            generator=generator,
            state=state,
            config=config,
            keep_latest=int(config["checkpoint"]["keep_latest"]),
        )
    except BaseException:
        _save_training_checkpoint(
            run_dir,
            model=model,
            optimizer=optimizer,
            environment=environment,
            collector=collector,
            generator=generator,
            state=state,
            config=config,
            keep_latest=int(config["checkpoint"]["keep_latest"]),
            failure=True,
        )
        raise
    finally:
        writer.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl/ppo_16gb.yaml")
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--resume")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--device", choices=("cpu", "cuda"))
    parser.add_argument("--runs-root", default="runs")
    arguments = parser.parse_args()
    if not RUN_NAME_PATTERN.fullmatch(arguments.run_name):
        raise ValueError("run-name may contain only letters, digits, dot, underscore, and hyphen")
    config = load_config(arguments.config)
    if arguments.seed is not None:
        config = deepcopy(config)
        config["seed"] = arguments.seed
    device = torch.device(arguments.device or config["device"])
    run_dir = Path(arguments.runs_root) / arguments.run_name
    resume = Path(arguments.resume) if arguments.resume else None
    if run_dir.exists() and resume is None and any(run_dir.iterdir()):
        raise FileExistsError(f"run directory already exists and is non-empty: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "resolved_config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=True), encoding="utf-8"
    )
    revision, dirty = _git_revision()
    _write_json(
        run_dir / "metadata.json",
        {
            "git_commit": revision,
            "git_dirty": dirty,
            "seed": config["seed"],
            "versions": config["versions"],
            "device": str(device),
            "python_version": platform.python_version(),
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "command": "python -m training.train_ppo",
        },
    )
    train(config, run_dir=run_dir, device=device, resume=resume)


if __name__ == "__main__":
    main()
