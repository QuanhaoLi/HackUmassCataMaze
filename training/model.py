# Created at: 2026-11-14 04:11 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:11 EST
# Last Modified by: Codex
# Implements the versioned recurrent actor-critic and exact legal-action masking.

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import torch
from torch import nn
from torch.distributions import Categorical


MODEL_ARCH_VERSION = "catamaze.model.rppo.v1"


@dataclass(frozen=True)
class ModelOutput:
    logits: torch.Tensor
    values: torch.Tensor
    hidden: torch.Tensor


class ResidualBlock(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.norm1 = nn.GroupNorm(8, channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.norm2 = nn.GroupNorm(8, channels)
        self.activation = nn.SiLU()

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        residual = inputs
        hidden = self.activation(self.norm1(self.conv1(inputs)))
        hidden = self.activation(self.norm2(self.conv2(hidden)))
        return residual + hidden


class RecurrentActorCritic(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.visual_stem = nn.Sequential(
            nn.Conv2d(13, 64, kernel_size=3, padding=1),
            nn.GroupNorm(8, 64),
            nn.SiLU(),
        )
        self.visual_residual = ResidualBlock(64)
        self.visual_projection = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 5 * 5, 256),
            nn.SiLU(),
        )
        self.scalar_encoder = nn.Sequential(
            nn.Linear(46, 128),
            nn.SiLU(),
            nn.Linear(128, 128),
            nn.SiLU(),
        )
        self.fusion = nn.Sequential(
            nn.LayerNorm(384),
            nn.Linear(384, 256),
            nn.SiLU(),
        )
        self.gru = nn.GRU(input_size=256, hidden_size=256, num_layers=1, batch_first=True)
        self.actor = nn.Linear(256, 9)
        self.critic = nn.Linear(256, 1)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for module in self.modules():
            if isinstance(module, (nn.Conv2d, nn.Linear)):
                nn.init.orthogonal_(module.weight, gain=sqrt(2.0))
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, (nn.GroupNorm, nn.LayerNorm)):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)
        for name, parameter in self.gru.named_parameters():
            if "weight_ih" in name:
                for gate in parameter.chunk(3, dim=0):
                    nn.init.orthogonal_(gate, gain=sqrt(2.0))
            elif "weight_hh" in name:
                for gate in parameter.chunk(3, dim=0):
                    nn.init.orthogonal_(gate, gain=1.0)
            else:
                nn.init.zeros_(parameter)
        nn.init.orthogonal_(self.actor.weight, gain=0.01)
        nn.init.zeros_(self.actor.bias)
        nn.init.orthogonal_(self.critic.weight, gain=1.0)
        nn.init.zeros_(self.critic.bias)

    def forward(
        self,
        spatial: torch.Tensor,
        scalar: torch.Tensor,
        *,
        hidden: torch.Tensor | None = None,
        episode_starts: torch.Tensor | None = None,
    ) -> ModelOutput:
        if spatial.ndim != 5 or spatial.shape[2:] != (13, 5, 5):
            raise ValueError("spatial must have shape [B, T, 13, 5, 5]")
        if scalar.shape != (*spatial.shape[:2], 46):
            raise ValueError("scalar must have shape [B, T, 46]")
        if not spatial.is_floating_point() or not scalar.is_floating_point():
            raise TypeError("model inputs must be floating point")
        batch, time = spatial.shape[:2]
        if hidden is None:
            hidden = torch.zeros((1, batch, 256), device=spatial.device, dtype=spatial.dtype)
        elif hidden.shape != (1, batch, 256):
            raise ValueError("hidden must have shape [1, B, 256]")
        if episode_starts is None:
            episode_starts = torch.zeros((batch, time), device=spatial.device, dtype=torch.bool)
        elif episode_starts.shape != (batch, time):
            raise ValueError("episode_starts must have shape [B, T]")

        flat_spatial = spatial.reshape(batch * time, 13, 5, 5)
        visual = self.visual_projection(self.visual_residual(self.visual_stem(flat_spatial)))
        scalar_embedding = self.scalar_encoder(scalar.reshape(batch * time, 46))
        fused = self.fusion(torch.cat((visual, scalar_embedding), dim=-1)).reshape(batch, time, 256)

        recurrent_outputs: list[torch.Tensor] = []
        recurrent_hidden = hidden
        for step in range(time):
            keep_hidden = (~episode_starts[:, step]).to(dtype=spatial.dtype).view(1, batch, 1)
            recurrent_hidden = recurrent_hidden * keep_hidden
            output, recurrent_hidden = self.gru(fused[:, step : step + 1], recurrent_hidden)
            recurrent_outputs.append(output)
        recurrent = torch.cat(recurrent_outputs, dim=1)
        return ModelOutput(
            logits=self.actor(recurrent),
            values=self.critic(recurrent).squeeze(-1),
            hidden=recurrent_hidden,
        )


def masked_categorical(
    logits: torch.Tensor,
    action_mask: torch.Tensor,
    *,
    temperature: float = 1.0,
) -> Categorical:
    if logits.shape != action_mask.shape or logits.shape[-1] != 9:
        raise ValueError("logits and action_mask must have matching [..., 9] shapes")
    if action_mask.dtype != torch.bool:
        raise TypeError("action_mask must be bool")
    if temperature <= 0.0:
        raise ValueError("temperature must be positive")
    if not torch.all(action_mask.any(dim=-1)):
        raise ValueError("every policy row must contain at least one legal action")
    masked_logits = (logits / temperature).masked_fill(~action_mask, -torch.inf)
    return Categorical(logits=masked_logits)
