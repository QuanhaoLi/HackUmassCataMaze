# Created at: 2026-11-14 04:19 EST
# Created by: Codex
# Last Modified at: 2026-11-14 06:48 EST
# Last Modified by: Codex
# Implements clipped recurrent PPO with masked actions and KL safety stops.

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.distributed as dist
from torch import nn

from training.model import masked_categorical
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
    max_approx_kl: float
    clip_fraction: float
    grad_norm: float
    explained_variance: float
    updates: int
    early_stopped: bool

    def as_dict(self) -> dict[str, float]:
        return {
            "policy_loss": self.policy_loss,
            "value_loss": self.value_loss,
            "entropy": self.entropy,
            "approx_kl": self.approx_kl,
            "max_approx_kl": self.max_approx_kl,
            "clip_fraction": self.clip_fraction,
            "grad_norm": self.grad_norm,
            "explained_variance": self.explained_variance,
            "updates": float(self.updates),
            "early_stopped": float(self.early_stopped),
        }


class PPOTrainer:
    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        config: PPOConfig,
        *,
        device: torch.device,
    ) -> None:
        self.model = model.to(device)
        self.optimizer = optimizer
        self.config = config
        self.device = device

    @property
    def distributed(self) -> bool:
        return dist.is_available() and dist.is_initialized()

    @property
    def world_size(self) -> int:
        return dist.get_world_size() if self.distributed else 1

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
        max_approx_kl = 0.0
        shuffle_generator = generator if generator.device.type == "cpu" else None
        self.model.train()
        for _epoch in range(self.config.update_epochs):
            for batch in rollout.sequence_batches(
                sequence_length=self.config.sequence_length,
                sequences_per_batch=self.config.sequences_per_batch,
                generator=shuffle_generator,
                include_inactive=self.distributed,
            ):
                metrics = self._update_batch(batch)
                for name in totals:
                    totals[name] += metrics[name]
                max_approx_kl = max(max_approx_kl, metrics["approx_kl"])
                updates += 1
                if metrics["approx_kl"] > self.config.hard_stop_kl:
                    stop = True
                    break
            if stop:
                break
        if updates == 0:
            raise RuntimeError("PPO rollout contained no active sequences")
        averaged = {name: value / updates for name, value in totals.items()}
        return PPOMetrics(
            **averaged,
            max_approx_kl=max_approx_kl,
            updates=updates,
            early_stopped=stop,
        )

    def _update_batch(self, batch: SequenceBatch) -> dict[str, float]:
        spatial = batch.spatial.to(self.device, dtype=torch.float32, non_blocking=True)
        scalar = batch.scalar.to(self.device, dtype=torch.float32, non_blocking=True)
        action_mask = batch.action_mask.to(self.device, non_blocking=True)
        actions = batch.actions.to(self.device, non_blocking=True)
        old_log_prob = batch.old_log_prob.to(self.device, non_blocking=True)
        old_values = batch.old_values.to(self.device, non_blocking=True)
        advantages = batch.advantages.to(self.device, non_blocking=True)
        returns = batch.returns.to(self.device, non_blocking=True)
        episode_starts = batch.episode_starts.to(self.device, non_blocking=True)
        hidden = batch.initial_hidden.to(self.device, non_blocking=True)
        loss_mask = batch.loss_mask.to(self.device, non_blocking=True)
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
        advantage_mean, advantage_variance, global_count = self._global_moments(
            selected_advantages
        )
        normalized_advantages = (selected_advantages - advantage_mean) / advantage_variance.sqrt().clamp_min(1e-8)
        log_ratio = new_log_prob[loss_mask] - old_log_prob[loss_mask]
        ratio = log_ratio.exp()
        policy_loss_unclipped = -normalized_advantages * ratio
        policy_loss_clipped = -normalized_advantages * ratio.clamp(
            1.0 - self.config.clip_coef, 1.0 + self.config.clip_coef
        )
        policy_terms = torch.maximum(policy_loss_unclipped, policy_loss_clipped)
        loss_scale = float(self.world_size) / global_count
        policy_loss = policy_terms.sum() * loss_scale

        values = output.values[loss_mask]
        selected_old_values = old_values[loss_mask]
        selected_returns = returns[loss_mask]
        value_unclipped = (values - selected_returns).square()
        value_clipped_prediction = selected_old_values + (values - selected_old_values).clamp(
            -self.config.value_clip_coef, self.config.value_clip_coef
        )
        value_clipped = (value_clipped_prediction - selected_returns).square()
        value_terms = torch.maximum(value_unclipped, value_clipped)
        value_loss = 0.5 * value_terms.sum() * loss_scale
        selected_entropy = entropy[loss_mask]
        entropy_mean = selected_entropy.sum() * loss_scale
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
            policy_metric = self._global_mean(policy_terms)
            value_metric = 0.5 * self._global_mean(value_terms)
            entropy_metric = self._global_mean(selected_entropy)
            approx_kl = self._global_mean((ratio - 1.0) - log_ratio)
            clip_fraction = self._global_mean(
                ((ratio - 1.0).abs() > self.config.clip_coef).float()
            )
            _return_mean, return_variance, _ = self._global_moments(selected_returns)
            _residual_mean, residual_variance, _ = self._global_moments(
                selected_returns - values
            )
            explained_variance = torch.where(
                return_variance > 1e-8,
                1.0 - residual_variance / return_variance,
                torch.zeros_like(return_variance),
            )
        return {
            "policy_loss": float(policy_metric),
            "value_loss": float(value_metric),
            "entropy": float(entropy_metric),
            "approx_kl": float(approx_kl.detach()),
            "clip_fraction": float(clip_fraction.detach()),
            "grad_norm": float(grad_norm.detach()),
            "explained_variance": float(explained_variance.detach()),
        }

    def _global_mean(self, values: torch.Tensor) -> torch.Tensor:
        total = values.detach().sum()
        count = torch.tensor(float(values.numel()), device=values.device)
        statistics = torch.stack((total, count))
        if self.distributed:
            dist.all_reduce(statistics, op=dist.ReduceOp.SUM)
        if statistics[1] <= 0:
            raise RuntimeError("distributed PPO minibatch contains no active transitions")
        return statistics[0] / statistics[1]

    def _global_moments(self, values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, float]:
        detached = values.detach()
        statistics = torch.stack(
            (
                detached.sum(),
                detached.square().sum(),
                torch.tensor(float(detached.numel()), device=detached.device),
            )
        )
        if self.distributed:
            dist.all_reduce(statistics, op=dist.ReduceOp.SUM)
        if statistics[2] <= 0:
            raise RuntimeError("distributed PPO minibatch contains no active transitions")
        mean = statistics[0] / statistics[2]
        variance = (statistics[1] / statistics[2] - mean.square()).clamp_min(0.0)
        return mean, variance, float(statistics[2])
