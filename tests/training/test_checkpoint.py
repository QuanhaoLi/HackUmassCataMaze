# Created at: 2026-11-14 04:35 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:35 EST
# Last Modified by: Codex
# Verifies that a checkpoint resumes at the exact next recurrent transition.

from __future__ import annotations

from pathlib import Path

import torch

from training.checkpoint import load_checkpoint, save_checkpoint
from training.collector import RolloutCollector
from training.env import CataMazeBatchEnv
from training.model import RecurrentActorCritic


def make_stack(seed: int) -> tuple[object, ...]:
    environment = CataMazeBatchEnv(num_envs=2, seed=seed)
    model = RecurrentActorCritic()
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
    collector = RolloutCollector(environment, model, device=torch.device("cpu"))
    generator = torch.Generator().manual_seed(seed)
    return environment, model, optimizer, collector, generator


def test_checkpoint_reproduces_exact_next_rollout(tmp_path: Path) -> None:
    torch.manual_seed(43)
    environment, model, optimizer, collector, generator = make_stack(47)
    collector.collect(2, gamma=0.995, gae_lambda=0.95, generator=generator)
    checkpoint = tmp_path / "resume.pt"
    save_checkpoint(
        checkpoint,
        model=model,
        optimizer=optimizer,
        environment=environment,
        collector=collector,
        policy_generator=generator,
        training_state={"agent_steps": 12, "curriculum_stage": "A"},
        resolved_config={"versions": {"training_config": "test.v1"}},
    )
    expected, _ = collector.collect(2, gamma=0.995, gae_lambda=0.95, generator=generator)

    restored_environment, restored_model, restored_optimizer, restored_collector, restored_generator = (
        make_stack(999)
    )
    training_state = load_checkpoint(
        checkpoint,
        model=restored_model,
        optimizer=restored_optimizer,
        environment=restored_environment,
        collector=restored_collector,
        policy_generator=restored_generator,
    )
    actual, _ = restored_collector.collect(
        2, gamma=0.995, gae_lambda=0.95, generator=restored_generator
    )

    assert training_state["agent_steps"] == 12
    for name in (
        "spatial",
        "scalar",
        "actions",
        "old_log_prob",
        "values",
        "rewards",
        "next_values",
        "terminated",
        "truncated",
        "hidden",
    ):
        torch.testing.assert_close(getattr(actual, name), getattr(expected, name), rtol=0, atol=0)
