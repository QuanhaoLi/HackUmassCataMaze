# Created at: 2026-11-14 06:58 EST
# Created by: Codex
# Last Modified at: 2026-11-14 07:27 EST
# Last Modified by: Codex
# Runs resumable four-rank DDP training of one production recurrent policy.

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
from time import perf_counter
from typing import Any

import numpy as np
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel
from torch.utils.tensorboard import SummaryWriter
import yaml

from training.collector import RolloutCollector
from training.config import load_config
from training.curriculum import CurriculumController
from training.ddp_smoke import _atomic_torch_save, _barrier
from training.env import CataMazeBatchEnv
from training.evaluator import evaluate_policy, merge_evaluation_reports
from training.model import RecurrentActorCritic
from training.opponents import OpponentStrategy
from training.ppo import PPOConfig, PPOTrainer
from training.reward import COMPONENT_NAMES
from training.train_ppo import _linear


def _rank_state(
    *,
    rank: int,
    environment: CataMazeBatchEnv,
    collector: RolloutCollector,
    generator: torch.Generator,
) -> dict[str, Any]:
    return {
        "rank": rank,
        "environment": environment.state_dict(),
        "collector": collector.state_dict(),
        "policy_generator": generator.get_state(),
        "python_rng": random.getstate(),
        "numpy_rng": np.random.get_state(),
        "torch_cpu_rng": torch.get_rng_state(),
        "torch_cuda_rng": torch.cuda.get_rng_state(),
    }


def _restore_rank_state(
    state: dict[str, Any],
    *,
    environment: CataMazeBatchEnv,
    collector: RolloutCollector,
    generator: torch.Generator,
) -> None:
    environment.load_state_dict(state["environment"])
    collector.load_state_dict(state["collector"])
    generator.set_state(state["policy_generator"])
    random.setstate(state["python_rng"])
    np.random.set_state(state["numpy_rng"])
    torch.set_rng_state(state["torch_cpu_rng"])
    torch.cuda.set_rng_state(state["torch_cuda_rng"])


def _move_optimizer(optimizer: torch.optim.Optimizer, device: torch.device) -> None:
    for optimizer_state in optimizer.state.values():
        for name, value in optimizer_state.items():
            if isinstance(value, torch.Tensor):
                optimizer_state[name] = value.to(device)


def _save_checkpoint(
    run_dir: Path,
    *,
    rank: int,
    world_size: int,
    device: torch.device,
    base_model: RecurrentActorCritic,
    optimizer: torch.optim.Optimizer,
    environment: CataMazeBatchEnv,
    collector: RolloutCollector,
    generator: torch.Generator,
    state: dict[str, Any],
    config: dict[str, Any],
    failure: bool = False,
) -> None:
    suffix = "failure" if failure else "latest"
    _atomic_torch_save(
        _rank_state(
            rank=rank,
            environment=environment,
            collector=collector,
            generator=generator,
        ),
        run_dir / "checkpoints" / f"{suffix}-rank{rank}.pt",
    )
    _barrier(device)
    if rank == 0:
        _atomic_torch_save(
            {
                "format": "catamaze.ddp-training.v1",
                "world_size": world_size,
                "model": base_model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "training_state": state,
                "config": config,
            },
            run_dir / "checkpoints" / f"{suffix}.pt",
        )
    _barrier(device)


def _reduce_collection(collection: Any, device: torch.device) -> list[float]:
    values = torch.tensor(
        [
            float(collection.agent_steps),
            collection.reward_sum,
            float(collection.completed_episodes),
            *[collection.component_sums.get(name, 0.0) for name in COMPONENT_NAMES],
        ],
        dtype=torch.float64,
        device=device,
    )
    dist.all_reduce(values, op=dist.ReduceOp.SUM)
    return values.cpu().tolist()


def _distributed_stage_reports(
    model: RecurrentActorCritic,
    config: dict[str, Any],
    controller: CurriculumController,
    *,
    device: torch.device,
    evaluation_index: int,
    rank: int,
    world_size: int,
    control_group: dist.ProcessGroup,
) -> dict[str, dict[str, Any]]:
    total_episodes = int(config["evaluation"]["episodes_per_persona_per_opponent"])
    local_episodes = math.ceil(total_episodes / world_size)
    merged: dict[str, dict[str, Any]] = {}
    for name in config["curriculum"][controller.stage]["evaluation_opponents"]:
        opponent = OpponentStrategy[name.upper()]
        local_report = evaluate_policy(
            model,
            episodes=local_episodes,
            opponent=opponent,
            mode="stochastic",
            seed=(
                int(config["seed"])
                + 1_000_000
                + evaluation_index * 10_000
                + int(opponent) * 100
                + rank
            ),
            num_envs=min(int(config["environment"]["num_envs"]), local_episodes),
            device=device,
        )
        gathered: list[dict[str, Any] | None] = [None] * world_size
        dist.all_gather_object(gathered, local_report, group=control_group)
        if rank == 0:
            merged[name] = merge_evaluation_reports(
                [report for report in gathered if report is not None]
            )
    return merged


def run(arguments: argparse.Namespace) -> None:
    dist.init_process_group("nccl")
    control_group = dist.new_group(backend="gloo")
    rank = dist.get_rank()
    world_size = dist.get_world_size()
    local_rank = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local_rank)
    device = torch.device("cuda", local_rank)
    config = load_config(arguments.config)
    if world_size != int(config["distributed"]["world_size"]):
        raise RuntimeError("torchrun world size does not match distributed config")
    global_num_envs = int(config["distributed"]["global_num_envs"])
    global_minibatch = int(config["distributed"]["global_minibatch_sequences"])
    if global_num_envs % world_size or global_minibatch % world_size:
        raise RuntimeError("distributed batch configuration is not rank-divisible")

    run_dir = Path(arguments.runs_root) / arguments.run_name
    resume = arguments.resume
    if rank == 0:
        if not resume and run_dir.exists() and any(run_dir.iterdir()):
            raise FileExistsError(f"run directory is non-empty: {run_dir}")
        for directory in ("checkpoints", "evaluations", "tensorboard", "artifacts"):
            (run_dir / directory).mkdir(parents=True, exist_ok=True)
    _barrier(device)

    seed = int(config["seed"])
    rank_seed = seed + rank * 1_000_003
    random.seed(rank_seed)
    np.random.seed(rank_seed % (2**32))
    torch.manual_seed(seed)
    torch.cuda.manual_seed(rank_seed)
    torch.backends.cuda.matmul.allow_tf32 = bool(config["precision"]["allow_tf32"])

    checkpoint: dict[str, Any] | None = None
    if resume:
        checkpoint = torch.load(run_dir / "checkpoints" / "latest.pt", map_location="cpu", weights_only=False)
        if checkpoint["world_size"] != world_size:
            raise RuntimeError("checkpoint world size does not match torchrun")
    stage = checkpoint["training_state"]["curriculum"]["stage"] if checkpoint else "A"
    controller = CurriculumController(stage=stage)
    environment = CataMazeBatchEnv(
        global_num_envs // world_size,
        rank_seed,
        curriculum_stage=stage,
        randomize_spawns=bool(config["environment"]["randomize_spawns"]),
    )
    base_model = RecurrentActorCritic().to(device)
    ddp_model = DistributedDataParallel(base_model, device_ids=[local_rank])
    optimizer = torch.optim.AdamW(
        ddp_model.parameters(),
        lr=float(config["ppo"]["learning_rate"]),
        eps=float(config["ppo"]["adam_eps"]),
        weight_decay=float(config["ppo"]["weight_decay"]),
    )
    collector = RolloutCollector(environment, ddp_model, device=device)
    generator = torch.Generator(device="cuda").manual_seed(rank_seed)
    state: dict[str, Any] = {
        "agent_steps": 0,
        "update": 0,
        "next_evaluation": int(config["evaluation"]["every_agent_steps"]),
        "next_checkpoint": int(config["checkpoint"]["every_agent_steps"]),
        "evaluation_index": 0,
        "high_kl_updates": 0,
        "learning_rate_scale": 1.0,
        "curriculum": controller.state_dict(),
    }
    if checkpoint:
        base_model.load_state_dict(checkpoint["model"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        _move_optimizer(optimizer, device)
        state = checkpoint["training_state"]
        controller.load_state_dict(state["curriculum"])
        rank_checkpoint = torch.load(
            run_dir / "checkpoints" / f"latest-rank{rank}.pt",
            map_location="cpu",
            weights_only=False,
        )
        _restore_rank_state(
            rank_checkpoint,
            environment=environment,
            collector=collector,
            generator=generator,
        )

    base_ppo = PPOConfig(
        update_epochs=int(config["minibatch"]["update_epochs"]),
        sequence_length=int(config["rollout"]["sequence_length"]),
        sequences_per_batch=global_minibatch // world_size,
        clip_coef=float(config["ppo"]["clip_coef"]),
        value_clip_coef=float(config["ppo"]["value_clip_coef"]),
        value_loss_coef=float(config["ppo"]["value_loss_coef"]),
        entropy_coef=float(config["ppo"]["entropy_coef"]),
        max_grad_norm=float(config["ppo"]["max_grad_norm"]),
        hard_stop_kl=float(config["ppo"]["hard_stop_kl"]),
    )
    trainer = PPOTrainer(ddp_model, optimizer, base_ppo, device=device)
    policy_target = arguments.agent_steps or int(config["total_agent_steps"])
    writer = SummaryWriter(run_dir / "tensorboard") if rank == 0 else None
    metrics_path = run_dir / "metrics.jsonl"
    if rank == 0 and not resume:
        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
        (run_dir / "resolved_config.yaml").write_text(
            yaml.safe_dump(config, sort_keys=True), encoding="utf-8"
        )
        (run_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "platform": platform.platform(),
                    "git_commit": git_commit,
                    "world_size": world_size,
                    "global_num_envs": global_num_envs,
                    "global_minibatch_sequences": global_minibatch,
                    "training_config": config["versions"]["training_config"],
                    "torch": torch.__version__,
                    "cuda": torch.version.cuda,
                    "numpy": np.__version__,
                    "dependencies": {
                        name: version(name)
                        for name in ("pybind11", "PyYAML", "tensorboard", "torch")
                    },
                    "visible_devices": [
                        {
                            "logical_index": index,
                            "name": torch.cuda.get_device_properties(index).name,
                            "compute_capability": list(
                                torch.cuda.get_device_capability(index)
                            ),
                        }
                        for index in range(torch.cuda.device_count())
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    _barrier(device)

    started = perf_counter()
    session_start_steps = int(state["agent_steps"])
    try:
        while int(state["agent_steps"]) < policy_target:
            progress = int(state["agent_steps"]) / int(config["total_agent_steps"])
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
            reduced = _reduce_collection(collection, device)
            state["agent_steps"] = int(state["agent_steps"]) + int(reduced[0])
            state["update"] = int(state["update"]) + 1
            if update.max_approx_kl > float(config["ppo"]["hard_stop_kl"]):
                state["high_kl_updates"] = int(state["high_kl_updates"]) + 1
            else:
                state["high_kl_updates"] = 0
            if int(state["high_kl_updates"]) >= 10:
                state["learning_rate_scale"] = float(state["learning_rate_scale"]) * 0.5
                state["high_kl_updates"] = 0

            local_memory = torch.tensor(
                float(torch.cuda.max_memory_allocated(device)), dtype=torch.float64, device=device
            )
            dist.all_reduce(local_memory, op=dist.ReduceOp.MAX)
            if int(local_memory) >= 14 * 1024**3:
                raise RuntimeError("DDP allocated CUDA memory reached the 14GB safety ceiling")
            if rank == 0:
                record = {
                    "update": state["update"],
                    "agent_steps": state["agent_steps"],
                    "agent_steps_per_second": (
                        int(state["agent_steps"]) - session_start_steps
                    )
                    / (perf_counter() - started),
                    "curriculum_stage": controller.stage,
                    "learning_rate": learning_rate,
                    "entropy_coef": entropy_coef,
                    "completed_episodes": int(reduced[2]),
                    "reward_sum": reduced[1],
                    "reward_components": {
                        name: reduced[3 + index] for index, name in enumerate(COMPONENT_NAMES)
                    },
                    "max_cuda_memory_allocated": int(local_memory),
                    **update.as_dict(),
                }
                with metrics_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(record, sort_keys=True) + "\n")
                if writer:
                    for name, value in update.as_dict().items():
                        writer.add_scalar(f"optimization/{name}", value, int(state["agent_steps"]))

            if int(state["agent_steps"]) >= int(state["next_evaluation"]):
                dist.barrier(group=control_group)
                reports = _distributed_stage_reports(
                    base_model,
                    config,
                    controller,
                    device=device,
                    evaluation_index=int(state["evaluation_index"]),
                    rank=rank,
                    world_size=world_size,
                    control_group=control_group,
                )
                if rank == 0:
                    evaluation_path = (
                        run_dir
                        / "evaluations"
                        / f"step-{int(state['agent_steps']):012d}-{controller.stage}.json"
                    )
                    evaluation_path.write_text(
                        json.dumps(reports, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                    )
                    controller.try_promote(int(state["agent_steps"]), reports)
                stage_tensor = torch.tensor(
                    CurriculumController.STAGES.index(controller.stage) if rank == 0 else 0,
                    device="cpu",
                )
                dist.broadcast(stage_tensor, src=0, group=control_group)
                stage = CurriculumController.STAGES[int(stage_tensor)]
                if rank != 0:
                    controller.load_state_dict({"stage": stage, "last_failures": ()})
                if environment.curriculum_stage != stage:
                    environment.set_curriculum_stage(stage)
                state["curriculum"] = controller.state_dict()
                state["evaluation_index"] = int(state["evaluation_index"]) + 1
                interval = int(config["evaluation"]["every_agent_steps"])
                while int(state["next_evaluation"]) <= int(state["agent_steps"]):
                    state["next_evaluation"] = int(state["next_evaluation"]) + interval
                dist.barrier(group=control_group)

            if int(state["agent_steps"]) >= int(state["next_checkpoint"]):
                interval = int(config["checkpoint"]["every_agent_steps"])
                while int(state["next_checkpoint"]) <= int(state["agent_steps"]):
                    state["next_checkpoint"] = int(state["next_checkpoint"]) + interval
                _save_checkpoint(
                    run_dir,
                    rank=rank,
                    world_size=world_size,
                    device=device,
                    base_model=base_model,
                    optimizer=optimizer,
                    environment=environment,
                    collector=collector,
                    generator=generator,
                    state=state,
                    config=config,
                )

        _save_checkpoint(
            run_dir,
            rank=rank,
            world_size=world_size,
            device=device,
            base_model=base_model,
            optimizer=optimizer,
            environment=environment,
            collector=collector,
            generator=generator,
            state=state,
            config=config,
        )
    except BaseException:
        _atomic_torch_save(
            _rank_state(
                rank=rank,
                environment=environment,
                collector=collector,
                generator=generator,
            ),
            run_dir / "checkpoints" / f"failure-rank{rank}.pt",
        )
        if rank == 0:
            _atomic_torch_save(
                {
                    "format": "catamaze.ddp-training.failure.v1",
                    "world_size": world_size,
                    "model": base_model.state_dict(),
                    "optimizer": optimizer.state_dict(),
                    "training_state": state,
                    "config": config,
                },
                run_dir / "checkpoints" / "failure.pt",
            )
        raise
    finally:
        if writer:
            writer.close()
        dist.destroy_process_group(control_group)
        dist.destroy_process_group()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl/ppo_16gb.yaml")
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--runs-root", default="runs")
    parser.add_argument("--agent-steps", type=int)
    parser.add_argument("--resume", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
