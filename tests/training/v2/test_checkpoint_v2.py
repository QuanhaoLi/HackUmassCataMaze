# Created at: 2026-11-14 18:52 EST
# Created by: Codex
# Last Modified at: 2026-11-14 18:52 EST
# Last Modified by: Codex
# Verifies exact V2 checkpoint continuation with three independent recurrent states.

from __future__ import annotations

from pathlib import Path

import torch

from training.collector import RolloutCollector
from training.env import CataMazeBatchEnv
from training.v2.checkpoint import load_checkpoint, save_checkpoint
from training.v2.model import PersonaRecurrentActorCritic


def make_stack(seed: int) -> tuple[object, ...]:
    environment = CataMazeBatchEnv(num_envs=2, seed=seed)
    model = PersonaRecurrentActorCritic()
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
    collector = RolloutCollector(environment, model, device=torch.device("cpu"))
    generator = torch.Generator().manual_seed(seed)
    return environment, model, optimizer, collector, generator


def test_v2_checkpoint_reproduces_exact_next_rollout(tmp_path: Path) -> None:
    torch.manual_seed(53)
    environment, model, optimizer, collector, generator = make_stack(59)
    collector.collect(2, gamma=0.995, gae_lambda=0.95, generator=generator)
    checkpoint = tmp_path / "resume-v2.pt"
    save_checkpoint(
        checkpoint,
        model=model,
        optimizer=optimizer,
        environment=environment,
        collector=collector,
        policy_generator=generator,
        training_state={"agent_steps": 12, "phase": "heads-only"},
        resolved_config={"versions": {"training_config": "test.persona.v2"}},
    )
    expected, _ = collector.collect(
        2, gamma=0.995, gae_lambda=0.95, generator=generator
    )
    restored = make_stack(999)
    state = load_checkpoint(
        checkpoint,
        model=restored[1],
        optimizer=restored[2],
        environment=restored[0],
        collector=restored[3],
        policy_generator=restored[4],
    )
    actual, _ = restored[3].collect(
        2, gamma=0.995, gae_lambda=0.95, generator=restored[4]
    )
    assert state == {"agent_steps": 12, "phase": "heads-only"}
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
        torch.testing.assert_close(
            getattr(actual, name), getattr(expected, name), rtol=0.0, atol=0.0
        )
