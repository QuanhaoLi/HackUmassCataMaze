# Created at: 2026-11-14 04:26 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:38 EST
# Last Modified by: Codex
# Collects legal recurrent rollouts and preserves terminal bootstrap observations.

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from training.env import CataMazeBatchEnv
from training.model import RecurrentActorCritic, masked_categorical
from training.rollout import RecurrentRollout


@dataclass
class CollectorState:
    hidden: torch.Tensor
    episode_starts: torch.Tensor


@dataclass(frozen=True)
class CollectorMetrics:
    agent_steps: int
    invalid_actions: int
    reward_sum: float
    component_sums: dict[str, float]
    completed_episodes: int


class RolloutCollector:
    def __init__(
        self,
        environment: CataMazeBatchEnv,
        model: RecurrentActorCritic,
        *,
        device: torch.device,
    ) -> None:
        self.environment = environment
        self.model = model
        self.device = device
        batch_agents = environment.num_envs * 3
        self.state = CollectorState(
            hidden=torch.zeros((1, batch_agents, 256), device=device),
            episode_starts=torch.ones((batch_agents,), dtype=torch.bool, device=device),
        )

    def state_dict(self) -> dict[str, torch.Tensor]:
        return {
            "hidden": self.state.hidden.detach().to("cpu").clone(),
            "episode_starts": self.state.episode_starts.detach().to("cpu").clone(),
        }

    def load_state_dict(self, state: dict[str, torch.Tensor]) -> None:
        hidden = state["hidden"]
        starts = state["episode_starts"]
        expected_agents = self.environment.num_envs * 3
        if hidden.shape != (1, expected_agents, 256) or starts.shape != (expected_agents,):
            raise ValueError("collector state does not match environment batch")
        self.state = CollectorState(
            hidden=hidden.to(self.device).clone(),
            episode_starts=starts.to(self.device).clone(),
        )

    def collect(
        self,
        environment_steps: int,
        *,
        gamma: float,
        gae_lambda: float,
        generator: torch.Generator | None = None,
    ) -> tuple[RecurrentRollout, CollectorMetrics]:
        rollout = RecurrentRollout(
            environment_steps=environment_steps,
            num_envs=self.environment.num_envs,
            agents_per_env=3,
        )
        component_sums: dict[str, float] = {}
        agent_steps = 0
        completed_episodes = 0
        self.model.eval()
        for _step in range(environment_steps):
            observation = self.environment.observation
            spatial_cpu = torch.from_numpy(observation["spatial"]).reshape(-1, 13, 5, 5)
            scalar_cpu = torch.from_numpy(observation["scalar"]).reshape(-1, 46)
            mask_cpu = torch.from_numpy(observation["action_mask"]).reshape(-1, 9)
            active_cpu = torch.from_numpy(observation["alive"]).reshape(-1)
            safe_mask = mask_cpu.to(self.device).clone()
            safe_mask[~active_cpu.to(self.device)] = False
            safe_mask[:, 8] |= ~active_cpu.to(self.device)
            hidden_before = self.state.hidden.detach().clone()
            starts_before = self.state.episode_starts.detach().clone()
            with torch.no_grad():
                output = self.model(
                    spatial_cpu[:, None].to(self.device, dtype=torch.float32),
                    scalar_cpu[:, None].to(self.device, dtype=torch.float32),
                    hidden=hidden_before,
                    episode_starts=starts_before[:, None],
                )
                distribution = masked_categorical(output.logits[:, 0], safe_mask)
                actions = torch.multinomial(
                    distribution.probs,
                    num_samples=1,
                    generator=generator,
                ).squeeze(-1)
                actions[~active_cpu.to(self.device)] = 8
                old_log_prob = distribution.log_prob(actions)
                values = output.values[:, 0]

            step_result = self.environment.step(
                actions.to("cpu", dtype=torch.uint8).numpy().reshape(self.environment.num_envs, 3)
            )
            terminal_observation = step_result.observation
            next_spatial = torch.from_numpy(terminal_observation["spatial"]).reshape(-1, 13, 5, 5)
            next_scalar = torch.from_numpy(terminal_observation["scalar"]).reshape(-1, 46)
            with torch.no_grad():
                next_output = self.model(
                    next_spatial[:, None].to(self.device, dtype=torch.float32),
                    next_scalar[:, None].to(self.device, dtype=torch.float32),
                    hidden=output.hidden,
                    episode_starts=torch.zeros_like(starts_before)[:, None],
                )
                next_values = next_output.values[:, 0]

            rewards_cpu = torch.from_numpy(step_result.reward.total).reshape(-1)
            terminated_cpu = torch.from_numpy(step_result.reward.terminated).reshape(-1)
            truncated_cpu = torch.from_numpy(step_result.reward.truncated).reshape(-1)
            rollout.add(
                spatial=spatial_cpu,
                scalar=scalar_cpu,
                action_mask=mask_cpu,
                actions=actions.to("cpu"),
                old_log_prob=old_log_prob.to("cpu"),
                values=values.to("cpu"),
                rewards=rewards_cpu,
                next_values=next_values.to("cpu"),
                terminated=terminated_cpu,
                truncated=truncated_cpu,
                active=active_cpu,
                episode_starts=starts_before.to("cpu"),
                hidden=hidden_before[0].to("cpu"),
            )
            agent_steps += int(active_cpu.sum())
            for name, values_array in step_result.reward.components.items():
                component_sums[name] = component_sums.get(name, 0.0) + float(values_array.sum())

            ended_cpu = terminated_cpu | truncated_cpu
            current_alive_cpu = torch.from_numpy(terminal_observation["alive"]).reshape(-1)
            starts_next_cpu = ended_cpu | (~current_alive_cpu)
            finished_envs = self.environment.reset_finished()
            completed_episodes += int(finished_envs.sum())
            if np.any(finished_envs):
                starts_next_cpu.reshape(self.environment.num_envs, 3)[finished_envs] = True
            self.state.hidden = output.hidden.detach()
            starts_next = starts_next_cpu.to(self.device)
            self.state.hidden[:, starts_next] = 0.0
            self.state.episode_starts = starts_next

        rollout.finish(gamma=gamma, gae_lambda=gae_lambda)
        return rollout, CollectorMetrics(
            agent_steps=agent_steps,
            invalid_actions=0,
            reward_sum=float(rollout.rewards.sum()),
            component_sums=component_sums,
            completed_episodes=completed_episodes,
        )
