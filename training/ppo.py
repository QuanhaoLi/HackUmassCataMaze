# Created at: 2026-11-14 04:19 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:19 EST
# Last Modified by: Codex
# Implements clipped recurrent PPO with masked actions and KL safety stops.

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from training.model import RecurrentActorCritic, masked_categorical
from training.rollout import RecurrentRollout, SequenceBatch


@dataclass(frozen=True)
class PPOConfig:
    update_epochs: int = 4
    sequence_length: int = 64
    sequences_per_batch: int = 32
    clip_coef: float = 0.20
    value_clip_coef: float = 0.20
    value_loss_coef: float = 0.5
    entropy_coef: float = 0.020
    max_grad_norm: float = 0.5
    hard_stop_kl: float = 0.03


@dataclass(frozen=True)
class PPOMetrics:
    policy_loss: float
    value_loss: float
    entropy: float
    approx_kl: float
    clip_fraction: float
    grad_norm: float
    explained_variance: float
    updates: int

    def as_dict(self) -> dict[str, float]:
        return {
            "policy_loss": self.policy_loss,
            "value_loss": self.value_loss,
            "entropy": self.entropy,
            "approx_kl": self.approx_kl,
            "clip_fraction": self.clip_fraction,
            "grad_norm": self.grad_norm,
            "explained_variance": self.explained_variance,
            "updates": float(self.updates),
        }


class PPOTrainer:
    def __init__(
        self,
        model: RecurrentActorCritic,
        optimizer: torch.optim.Optimizer,
        config: PPOConfig,
        *,
        device: torch.device,
    ) -> None:
        self.model = model.to(device)
        self.optimizer = optimizer
        self.config = config
        self.device = device

    def update(self, rollout: RecurrentRollout, *, generator: torch.Generator) -> PPOMetrics:
        totals = {
            "policy_loss": 0.0,
            "value_loss": 0.0,
            "entropy": 0.0,
            "approx_kl": 0.0,
            "clip_fraction": 0.0,
            "grad_norm": 0.0,
            "explained_variance": 0.0,
        }
        updates = 0
        stop = False
        self.model.train()
        for _epoch in range(self.config.update_epochs):
            for batch in rollout.sequence_batches(
                sequence_length=self.config.sequence_length,
                sequences_per_batch=self.config.sequences_per_batch,
                generator=generator,
            ):
                metrics = self._update_batch(batch)
                for name in totals:
                    totals[name] += metrics[name]
                updates += 1
                if metrics["approx_kl"] > self.config.hard_stop_kl:
                    stop = True
                    break
            if stop:
                break
        if updates == 0:
            raise RuntimeError("PPO rollout contained no active sequences")
        averaged = {name: value / updates for name, value in totals.items()}
        return PPOMetrics(**averaged, updates=updates)

    def _update_batch(self, batch: SequenceBatch) -> dict[str, float]:
        spatial = batch.spatial.to(self.device, dtype=torch.float32)
        scalar = batch.scalar.to(self.device, dtype=torch.float32)
        action_mask = batch.action_mask.to(self.device)
        actions = batch.actions.to(self.device)
        old_log_prob = batch.old_log_prob.to(self.device)
        old_values = batch.old_values.to(self.device)
        advantages = batch.advantages.to(self.device)
        returns = batch.returns.to(self.device)
        episode_starts = batch.episode_starts.to(self.device)
        hidden = batch.initial_hidden.to(self.device)
        loss_mask = batch.loss_mask.to(self.device)
        safe_mask = action_mask.clone()
        safe_mask[~loss_mask] = False
        safe_mask[..., 8] |= ~loss_mask

        output = self.model(
            spatial,
            scalar,
            hidden=hidden,
            episode_starts=episode_starts,
        )
        distribution = masked_categorical(output.logits, safe_mask)
        new_log_prob = distribution.log_prob(actions)
        entropy = distribution.entropy()

        selected_advantages = advantages[loss_mask]
        normalized_advantages = (
            selected_advantages - selected_advantages.mean()
        ) / selected_advantages.std(unbiased=False).clamp_min(1e-8)
        log_ratio = new_log_prob[loss_mask] - old_log_prob[loss_mask]
        ratio = log_ratio.exp()
        policy_loss_unclipped = -normalized_advantages * ratio
        policy_loss_clipped = -normalized_advantages * ratio.clamp(
            1.0 - self.config.clip_coef, 1.0 + self.config.clip_coef
        )
        policy_loss = torch.maximum(policy_loss_unclipped, policy_loss_clipped).mean()

        values = output.values[loss_mask]
        selected_old_values = old_values[loss_mask]
        selected_returns = returns[loss_mask]
        value_unclipped = (values - selected_returns).square()
        value_clipped_prediction = selected_old_values + (values - selected_old_values).clamp(
            -self.config.value_clip_coef, self.config.value_clip_coef
        )
        value_clipped = (value_clipped_prediction - selected_returns).square()
        value_loss = 0.5 * torch.maximum(value_unclipped, value_clipped).mean()
        entropy_mean = entropy[loss_mask].mean()
        total_loss = (
            policy_loss
            + self.config.value_loss_coef * value_loss
            - self.config.entropy_coef * entropy_mean
        )
        if not torch.isfinite(total_loss):
            raise FloatingPointError("PPO loss became NaN or Inf")

        self.optimizer.zero_grad(set_to_none=True)
        total_loss.backward()
        grad_norm = nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
        if not torch.isfinite(grad_norm):
            raise FloatingPointError("PPO gradient norm became NaN or Inf")
        self.optimizer.step()

        with torch.no_grad():
            approx_kl = ((ratio - 1.0) - log_ratio).mean()
            clip_fraction = ((ratio - 1.0).abs() > self.config.clip_coef).float().mean()
            return_variance = torch.var(selected_returns, unbiased=False)
            explained_variance = torch.where(
                return_variance > 1e-8,
                1.0 - torch.var(selected_returns - values, unbiased=False) / return_variance,
                torch.zeros_like(return_variance),
            )
        return {
            "policy_loss": float(policy_loss.detach()),
            "value_loss": float(value_loss.detach()),
            "entropy": float(entropy_mean.detach()),
            "approx_kl": float(approx_kl.detach()),
            "clip_fraction": float(clip_fraction.detach()),
            "grad_norm": float(grad_norm.detach()),
            "explained_variance": float(explained_variance.detach()),
        }
