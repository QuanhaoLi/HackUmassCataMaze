# Created at: 2026-11-14 18:52 EST
# Created by: Codex
# Last Modified at: 2026-11-14 21:55 EST
# Last Modified by: Codex
# Implements equal-weight per-persona recurrent PPO for the isolated V2 policy.

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.distributed as dist
from torch import nn

from training.model import masked_categorical
from training.ppo import PPOConfig
from training.rollout import RecurrentRollout, SequenceBatch
from training.v2.model import PERSONA_COUNT, PERSONA_OFFSET
from training.v2.rollout import persona_sequence_batches
from training.v2.style_loss import (
    STYLE_COMPONENT_NAMES,
    STYLE_METRIC_NAMES,
    persona_style_loss,
)


def normalize_advantages_per_persona(
    advantages: torch.Tensor,
    personas: torch.Tensor,
    loss_mask: torch.Tensor,
) -> torch.Tensor:
    if advantages.shape != personas.shape or advantages.shape != loss_mask.shape:
        raise ValueError("advantages, personas, and loss_mask must share a shape")
    normalized = torch.zeros_like(advantages)
    for persona in range(PERSONA_COUNT):
        selected = loss_mask & (personas == persona)
        values = advantages[selected]
        if values.numel() == 0:
            raise RuntimeError(f"persona {persona} has no active advantages")
        mean = values.mean()
        variance = (values - mean).square().mean()
        normalized[selected] = (values - mean) / variance.sqrt().clamp_min(1e-8)
    return normalized


@dataclass(frozen=True)
class PersonaPPOMetrics:
    policy_loss: float
    value_loss: float
    entropy: float
    approx_kl: float
    max_approx_kl: float
    clip_fraction: float
    grad_norm: float
    explained_variance: float
    style_loss: float
    updates: int
    early_stopped: bool
    persona_policy_loss: tuple[float, float, float]
    persona_value_loss: tuple[float, float, float]
    persona_entropy: tuple[float, float, float]
    persona_approx_kl: tuple[float, float, float]
    persona_clip_fraction: tuple[float, float, float]
    persona_explained_variance: tuple[float, float, float]
    style_metrics: dict[str, float]

    def as_dict(self) -> dict[str, float]:
        metrics = {
            "policy_loss": self.policy_loss,
            "value_loss": self.value_loss,
            "entropy": self.entropy,
            "approx_kl": self.approx_kl,
            "max_approx_kl": self.max_approx_kl,
            "clip_fraction": self.clip_fraction,
            "grad_norm": self.grad_norm,
            "explained_variance": self.explained_variance,
            "style_loss": self.style_loss,
            "updates": float(self.updates),
            "early_stopped": float(self.early_stopped),
        }
        fields = {
            "policy_loss": self.persona_policy_loss,
            "value_loss": self.persona_value_loss,
            "entropy": self.persona_entropy,
            "approx_kl": self.persona_approx_kl,
            "clip_fraction": self.persona_clip_fraction,
            "explained_variance": self.persona_explained_variance,
        }
        for name, values in fields.items():
            for persona, value in enumerate(values):
                metrics[f"persona/{persona}/{name}"] = value
        for name, value in self.style_metrics.items():
            metrics[f"style/{name}"] = value
        return metrics


class PersonaPPOTrainer:
    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        config: PPOConfig,
        *,
        device: torch.device,
        style_loss_coef: float = 0.0,
    ) -> None:
        self.model = model.to(device)
        self.optimizer = optimizer
        self.config = config
        self.device = device
        if style_loss_coef < 0:
            raise ValueError("style_loss_coef must be non-negative")
        self.style_loss_coef = style_loss_coef

    @property
    def distributed(self) -> bool:
        return dist.is_available() and dist.is_initialized()

    @property
    def world_size(self) -> int:
        return dist.get_world_size() if self.distributed else 1

    def update(
        self, rollout: RecurrentRollout, *, generator: torch.Generator
    ) -> PersonaPPOMetrics:
        aggregate_names = (
            "policy_loss",
            "value_loss",
            "entropy",
            "approx_kl",
            "clip_fraction",
            "grad_norm",
            "explained_variance",
            "style_loss",
        )
        persona_names = (
            "policy_loss",
            "value_loss",
            "entropy",
            "approx_kl",
            "clip_fraction",
            "explained_variance",
        )
        totals = {name: 0.0 for name in aggregate_names}
        persona_totals = {
            name: [0.0 for _ in range(PERSONA_COUNT)] for name in persona_names
        }
        style_totals = {name: 0.0 for name in STYLE_METRIC_NAMES}
        updates = 0
        early_stopped = False
        max_approx_kl = 0.0
        shuffle_generator = generator if generator.device.type == "cpu" else None
        self.model.train()
        for _epoch in range(self.config.update_epochs):
            for batch in persona_sequence_batches(
                rollout,
                sequence_length=self.config.sequence_length,
                sequences_per_batch=self.config.sequences_per_batch,
                generator=shuffle_generator,
                include_inactive=self.distributed,
            ):
                aggregate, per_persona, style = self._update_batch(batch)
                for name in aggregate_names:
                    totals[name] += aggregate[name]
                for name in persona_names:
                    for persona in range(PERSONA_COUNT):
                        persona_totals[name][persona] += per_persona[name][persona]
                for name in STYLE_METRIC_NAMES:
                    style_totals[name] += style[name]
                batch_max_kl = max(per_persona["approx_kl"])
                max_approx_kl = max(max_approx_kl, batch_max_kl)
                updates += 1
                if batch_max_kl > self.config.hard_stop_kl:
                    early_stopped = True
                    break
            if early_stopped:
                break
        if updates == 0:
            raise RuntimeError("V2 PPO rollout contained no active sequences")
        averaged = {name: value / updates for name, value in totals.items()}
        persona_averaged = {
            name: tuple(value / updates for value in values)
            for name, values in persona_totals.items()
        }
        return PersonaPPOMetrics(
            **averaged,
            max_approx_kl=max_approx_kl,
            updates=updates,
            early_stopped=early_stopped,
            persona_policy_loss=persona_averaged["policy_loss"],
            persona_value_loss=persona_averaged["value_loss"],
            persona_entropy=persona_averaged["entropy"],
            persona_approx_kl=persona_averaged["approx_kl"],
            persona_clip_fraction=persona_averaged["clip_fraction"],
            persona_explained_variance=persona_averaged["explained_variance"],
            style_metrics={name: value / updates for name, value in style_totals.items()},
        )

    def _update_batch(
        self, batch: SequenceBatch
    ) -> tuple[dict[str, float], dict[str, list[float]], dict[str, float]]:
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
        persona = scalar[..., PERSONA_OFFSET : PERSONA_OFFSET + PERSONA_COUNT]
        persona_ids = persona.argmax(dim=-1)
        if not torch.allclose(persona[loss_mask].sum(dim=-1), torch.ones_like(persona_ids[loss_mask], dtype=scalar.dtype)):
            raise ValueError("active V2 samples must have exactly one persona")

        output = self.model(
            spatial,
            scalar,
            hidden=hidden,
            episode_starts=episode_starts,
        )
        style_loss, style_components = persona_style_loss(
            output.logits_all,
            safe_mask,
            spatial,
            scalar,
            loss_mask,
            actions,
        )
        distribution = masked_categorical(output.logits, safe_mask)
        new_log_prob = distribution.log_prob(actions)
        entropy = distribution.entropy()
        normalized_advantages = self._normalize_global_per_persona(
            advantages, persona_ids, loss_mask
        )

        differentiable_policy: list[torch.Tensor] = []
        differentiable_value: list[torch.Tensor] = []
        differentiable_entropy: list[torch.Tensor] = []
        per_persona = {
            "policy_loss": [],
            "value_loss": [],
            "entropy": [],
            "approx_kl": [],
            "clip_fraction": [],
            "explained_variance": [],
        }
        for index in range(PERSONA_COUNT):
            selected = loss_mask & (persona_ids == index)
            global_count = self._global_count(selected)
            loss_scale = float(self.world_size) / global_count
            log_ratio = new_log_prob[selected] - old_log_prob[selected]
            ratio = log_ratio.exp()
            advantage = normalized_advantages[selected]
            policy_unclipped = -advantage * ratio
            policy_clipped = -advantage * ratio.clamp(
                1.0 - self.config.clip_coef, 1.0 + self.config.clip_coef
            )
            policy_terms = torch.maximum(policy_unclipped, policy_clipped)
            policy_loss = policy_terms.sum() * loss_scale

            values = output.values[selected]
            selected_old_values = old_values[selected]
            selected_returns = returns[selected]
            value_unclipped = (values - selected_returns).square()
            clipped_prediction = selected_old_values + (
                values - selected_old_values
            ).clamp(-self.config.value_clip_coef, self.config.value_clip_coef)
            value_clipped = (clipped_prediction - selected_returns).square()
            value_terms = torch.maximum(value_unclipped, value_clipped)
            value_loss = 0.5 * value_terms.sum() * loss_scale
            entropy_loss = entropy[selected].sum() * loss_scale
            differentiable_policy.append(policy_loss)
            differentiable_value.append(value_loss)
            differentiable_entropy.append(entropy_loss)

            with torch.no_grad():
                per_persona["policy_loss"].append(float(self._global_mean(policy_terms)))
                per_persona["value_loss"].append(
                    float(0.5 * self._global_mean(value_terms))
                )
                per_persona["entropy"].append(float(self._global_mean(entropy[selected])))
                per_persona["approx_kl"].append(
                    float(self._global_mean((ratio - 1.0) - log_ratio))
                )
                per_persona["clip_fraction"].append(
                    float(
                        self._global_mean(
                            ((ratio - 1.0).abs() > self.config.clip_coef).float()
                        )
                    )
                )
                _return_mean, return_variance, _ = self._global_moments(
                    selected_returns
                )
                _residual_mean, residual_variance, _ = self._global_moments(
                    selected_returns - values
                )
                explained = torch.where(
                    return_variance > 1e-8,
                    1.0 - residual_variance / return_variance,
                    torch.zeros_like(return_variance),
                )
                per_persona["explained_variance"].append(float(explained))

        policy_loss = torch.stack(differentiable_policy).mean()
        value_loss = torch.stack(differentiable_value).mean()
        entropy_mean = torch.stack(differentiable_entropy).mean()
        total_loss = (
            policy_loss
            + self.config.value_loss_coef * value_loss
            - self.config.entropy_coef * entropy_mean
            + self.style_loss_coef * style_loss
        )
        if not torch.isfinite(total_loss):
            raise FloatingPointError("V2 PPO loss became NaN or Inf")
        self.optimizer.zero_grad(set_to_none=True)
        total_loss.backward()
        grad_norm = nn.utils.clip_grad_norm_(
            self.model.parameters(), self.config.max_grad_norm
        )
        if not torch.isfinite(grad_norm):
            raise FloatingPointError("V2 PPO gradient norm became NaN or Inf")
        self.optimizer.step()

        aggregate = {
            name: sum(per_persona[name]) / PERSONA_COUNT
            for name in per_persona
        }
        aggregate["grad_norm"] = float(grad_norm.detach())
        aggregate["style_loss"] = float(
            self._global_mean(style_loss.detach().reshape(1))
        )
        style_metrics = {
            name: float(self._global_mean(value.detach().reshape(1)))
            for name, value in style_components.items()
        }
        return aggregate, per_persona, style_metrics

    def _normalize_global_per_persona(
        self,
        advantages: torch.Tensor,
        persona_ids: torch.Tensor,
        loss_mask: torch.Tensor,
    ) -> torch.Tensor:
        normalized = torch.zeros_like(advantages)
        for persona in range(PERSONA_COUNT):
            selected = loss_mask & (persona_ids == persona)
            mean, variance, _count = self._global_moments(advantages[selected])
            normalized[selected] = (advantages[selected] - mean) / variance.sqrt().clamp_min(
                1e-8
            )
        return normalized

    def _global_count(self, mask: torch.Tensor) -> float:
        count = torch.tensor(float(mask.sum()), device=mask.device)
        if self.distributed:
            dist.all_reduce(count, op=dist.ReduceOp.SUM)
        if count <= 0:
            raise RuntimeError("V2 minibatch is missing an active persona")
        return float(count)

    def _global_mean(self, values: torch.Tensor) -> torch.Tensor:
        statistics = torch.stack(
            (
                values.detach().sum(),
                torch.tensor(float(values.numel()), device=values.device),
            )
        )
        if self.distributed:
            dist.all_reduce(statistics, op=dist.ReduceOp.SUM)
        if statistics[1] <= 0:
            raise RuntimeError("V2 minibatch is missing an active persona")
        return statistics[0] / statistics[1]

    def _global_moments(
        self, values: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, float]:
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
            raise RuntimeError("V2 minibatch is missing an active persona")
        mean = statistics[0] / statistics[2]
        variance = (statistics[1] / statistics[2] - mean.square()).clamp_min(0.0)
        return mean, variance, float(statistics[2])
