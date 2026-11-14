# Created at: 2026-11-14 04:19 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:19 EST
# Last Modified by: Codex
# Stores recurrent on-policy transitions and produces fixed-length sequence batches.

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import torch


@dataclass(frozen=True)
class SequenceBatch:
    spatial: torch.Tensor
    scalar: torch.Tensor
    action_mask: torch.Tensor
    actions: torch.Tensor
    old_log_prob: torch.Tensor
    old_values: torch.Tensor
    advantages: torch.Tensor
    returns: torch.Tensor
    episode_starts: torch.Tensor
    initial_hidden: torch.Tensor
    loss_mask: torch.Tensor


def compute_gae(
    rewards: torch.Tensor,
    values: torch.Tensor,
    next_values: torch.Tensor,
    *,
    terminated: torch.Tensor,
    truncated: torch.Tensor,
    active: torch.Tensor,
    gamma: float,
    gae_lambda: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    expected_shape = rewards.shape
    tensors = (values, next_values, terminated, truncated, active)
    if rewards.ndim != 2 or any(tensor.shape != expected_shape for tensor in tensors):
        raise ValueError("GAE tensors must share shape [T, B]")
    advantages = torch.zeros_like(rewards)
    next_advantage = torch.zeros_like(rewards[0])
    for step in reversed(range(rewards.shape[0])):
        bootstrap = (~terminated[step]).to(dtype=rewards.dtype)
        continuation = (~(terminated[step] | truncated[step])).to(dtype=rewards.dtype)
        active_step = active[step].to(dtype=rewards.dtype)
        delta = (
            rewards[step] + gamma * next_values[step] * bootstrap - values[step]
        ) * active_step
        next_advantage = (
            delta + gamma * gae_lambda * continuation * next_advantage
        ) * active_step
        advantages[step] = next_advantage
    returns = advantages + values
    return advantages, returns


class RecurrentRollout:
    def __init__(self, environment_steps: int, num_envs: int, agents_per_env: int = 3) -> None:
        if environment_steps <= 0 or num_envs <= 0 or agents_per_env <= 0:
            raise ValueError("rollout dimensions must be positive")
        self.environment_steps = environment_steps
        self.num_envs = num_envs
        self.agents_per_env = agents_per_env
        self.batch_agents = num_envs * agents_per_env
        shape = (environment_steps, self.batch_agents)
        self.spatial = torch.empty((*shape, 13, 5, 5), dtype=torch.uint8)
        self.scalar = torch.empty((*shape, 46), dtype=torch.float32)
        self.action_mask = torch.empty((*shape, 9), dtype=torch.bool)
        self.actions = torch.empty(shape, dtype=torch.int64)
        self.old_log_prob = torch.empty(shape, dtype=torch.float32)
        self.values = torch.empty(shape, dtype=torch.float32)
        self.rewards = torch.empty(shape, dtype=torch.float32)
        self.next_values = torch.empty(shape, dtype=torch.float32)
        self.terminated = torch.empty(shape, dtype=torch.bool)
        self.truncated = torch.empty(shape, dtype=torch.bool)
        self.active = torch.empty(shape, dtype=torch.bool)
        self.episode_starts = torch.empty(shape, dtype=torch.bool)
        self.hidden = torch.empty((*shape, 256), dtype=torch.float32)
        self.advantages: torch.Tensor | None = None
        self.returns: torch.Tensor | None = None
        self._position = 0

    def add(
        self,
        *,
        spatial: torch.Tensor,
        scalar: torch.Tensor,
        action_mask: torch.Tensor,
        actions: torch.Tensor,
        old_log_prob: torch.Tensor,
        values: torch.Tensor,
        rewards: torch.Tensor,
        next_values: torch.Tensor,
        terminated: torch.Tensor,
        truncated: torch.Tensor,
        active: torch.Tensor,
        episode_starts: torch.Tensor,
        hidden: torch.Tensor,
    ) -> None:
        if self._position >= self.environment_steps:
            raise RuntimeError("rollout is already full")
        expected = self.batch_agents
        expected_shapes = {
            "spatial": (expected, 13, 5, 5),
            "scalar": (expected, 46),
            "action_mask": (expected, 9),
            "actions": (expected,),
            "old_log_prob": (expected,),
            "values": (expected,),
            "rewards": (expected,),
            "next_values": (expected,),
            "terminated": (expected,),
            "truncated": (expected,),
            "active": (expected,),
            "episode_starts": (expected,),
            "hidden": (expected, 256),
        }
        provided = locals()
        for name, expected_shape in expected_shapes.items():
            if tuple(provided[name].shape) != expected_shape:
                raise ValueError(f"{name} must have shape {expected_shape}")
        index = self._position
        for name in expected_shapes:
            target = getattr(self, name if name != "old_log_prob" else "old_log_prob")
            target[index].copy_(provided[name].detach().to(device="cpu", dtype=target.dtype))
        self._position += 1

    def finish(self, *, gamma: float, gae_lambda: float) -> None:
        if self._position != self.environment_steps:
            raise RuntimeError("cannot finish an incomplete rollout")
        self.advantages, self.returns = compute_gae(
            self.rewards,
            self.values,
            self.next_values,
            terminated=self.terminated,
            truncated=self.truncated,
            active=self.active,
            gamma=gamma,
            gae_lambda=gae_lambda,
        )

    def sequence_batches(
        self,
        *,
        sequence_length: int,
        sequences_per_batch: int,
        generator: torch.Generator,
        shuffle: bool = True,
    ) -> Iterator[SequenceBatch]:
        if self.advantages is None or self.returns is None:
            raise RuntimeError("finish must be called before batching")
        if sequence_length <= 0 or self.environment_steps % sequence_length != 0:
            raise ValueError("sequence_length must evenly divide environment_steps")
        if sequences_per_batch <= 0:
            raise ValueError("sequences_per_batch must be positive")
        candidates: list[tuple[int, int]] = []
        for batch_agent in range(self.batch_agents):
            for start in range(0, self.environment_steps, sequence_length):
                if self.active[start : start + sequence_length, batch_agent].any():
                    candidates.append((batch_agent, start))
        if shuffle:
            order = torch.randperm(len(candidates), generator=generator).tolist()
            candidates = [candidates[index] for index in order]

        for offset in range(0, len(candidates), sequences_per_batch):
            selected = candidates[offset : offset + sequences_per_batch]

            def stack(source: torch.Tensor) -> torch.Tensor:
                return torch.stack(
                    [source[start : start + sequence_length, agent] for agent, start in selected]
                )

            initial_hidden = torch.stack(
                [self.hidden[start, agent] for agent, start in selected], dim=0
            ).unsqueeze(0)
            yield SequenceBatch(
                spatial=stack(self.spatial),
                scalar=stack(self.scalar),
                action_mask=stack(self.action_mask),
                actions=stack(self.actions),
                old_log_prob=stack(self.old_log_prob),
                old_values=stack(self.values),
                advantages=stack(self.advantages),
                returns=stack(self.returns),
                episode_starts=stack(self.episode_starts),
                initial_hidden=initial_hidden,
                loss_mask=stack(self.active),
            )
