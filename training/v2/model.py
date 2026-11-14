# Created at: 2026-11-14 18:52 EST
# Created by: Codex
# Last Modified at: 2026-11-14 18:52 EST
# Last Modified by: Codex
# Implements the isolated V2 shared recurrent trunk with persona modulation and heads.

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

import torch
from torch import nn

from training.model import RecurrentActorCritic


PERSONA_COUNT = 3
PERSONA_OFFSET = 43
HIDDEN_SIZE = 256
ACTION_COUNT = 9


@dataclass(frozen=True)
class PersonaModelOutput:
    logits: torch.Tensor
    logits_all: torch.Tensor
    values: torch.Tensor
    values_all: torch.Tensor
    hidden: torch.Tensor


class PersonaRecurrentActorCritic(nn.Module):
    """V2 policy with a V1-equivalent initialization and isolated persona heads."""

    def __init__(self) -> None:
        super().__init__()
        baseline = RecurrentActorCritic()
        self.visual_stem = baseline.visual_stem
        self.visual_residual = baseline.visual_residual
        self.visual_projection = baseline.visual_projection
        self.scalar_encoder = baseline.scalar_encoder
        self.fusion = baseline.fusion
        self.gru = baseline.gru
        self.persona_gamma = nn.Parameter(torch.zeros(PERSONA_COUNT, HIDDEN_SIZE))
        self.persona_beta = nn.Parameter(torch.zeros(PERSONA_COUNT, HIDDEN_SIZE))
        self.actors = nn.ModuleList(
            [deepcopy(baseline.actor) for _ in range(PERSONA_COUNT)]
        )
        self.critics = nn.ModuleList(
            [deepcopy(baseline.critic) for _ in range(PERSONA_COUNT)]
        )

    @classmethod
    def from_v1(cls, baseline: RecurrentActorCritic) -> "PersonaRecurrentActorCritic":
        candidate = cls()
        parameter = next(baseline.parameters())
        candidate.to(device=parameter.device, dtype=parameter.dtype)
        for name in (
            "visual_stem",
            "visual_residual",
            "visual_projection",
            "scalar_encoder",
            "fusion",
            "gru",
        ):
            getattr(candidate, name).load_state_dict(getattr(baseline, name).state_dict())
        for actor in candidate.actors:
            actor.load_state_dict(baseline.actor.state_dict())
        for critic in candidate.critics:
            critic.load_state_dict(baseline.critic.state_dict())
        with torch.no_grad():
            candidate.persona_gamma.zero_()
            candidate.persona_beta.zero_()
        candidate.train(baseline.training)
        return candidate

    def forward(
        self,
        spatial: torch.Tensor,
        scalar: torch.Tensor,
        *,
        hidden: torch.Tensor | None = None,
        episode_starts: torch.Tensor | None = None,
    ) -> PersonaModelOutput:
        if spatial.ndim != 5 or spatial.shape[2:] != (13, 5, 5):
            raise ValueError("spatial must have shape [B, T, 13, 5, 5]")
        if scalar.shape != (*spatial.shape[:2], 46):
            raise ValueError("scalar must have shape [B, T, 46]")
        if not spatial.is_floating_point() or not scalar.is_floating_point():
            raise TypeError("model inputs must be floating point")
        batch, time = spatial.shape[:2]
        if hidden is None:
            hidden = torch.zeros(
                (1, batch, HIDDEN_SIZE), device=spatial.device, dtype=spatial.dtype
            )
        elif hidden.shape != (1, batch, HIDDEN_SIZE):
            raise ValueError("hidden must have shape [1, B, 256]")
        if episode_starts is None:
            episode_starts = torch.zeros(
                (batch, time), device=spatial.device, dtype=torch.bool
            )
        elif episode_starts.shape != (batch, time):
            raise ValueError("episode_starts must have shape [B, T]")

        persona = scalar[..., PERSONA_OFFSET : PERSONA_OFFSET + PERSONA_COUNT]
        flat_spatial = spatial.reshape(batch * time, 13, 5, 5)
        visual = self.visual_projection(
            self.visual_residual(self.visual_stem(flat_spatial))
        )
        scalar_embedding = self.scalar_encoder(scalar.reshape(batch * time, 46))
        fused = self.fusion(torch.cat((visual, scalar_embedding), dim=-1)).reshape(
            batch, time, HIDDEN_SIZE
        )
        gamma = torch.matmul(persona, self.persona_gamma)
        beta = torch.matmul(persona, self.persona_beta)
        fused = fused * (1.0 + gamma) + beta

        recurrent_outputs: list[torch.Tensor] = []
        recurrent_hidden = hidden
        for step in range(time):
            keep_hidden = (~episode_starts[:, step]).to(dtype=spatial.dtype).view(
                1, batch, 1
            )
            recurrent_hidden = recurrent_hidden * keep_hidden
            output, recurrent_hidden = self.gru(
                fused[:, step : step + 1], recurrent_hidden
            )
            recurrent_outputs.append(output)
        recurrent = torch.cat(recurrent_outputs, dim=1)

        logits_all = torch.stack(
            [actor(recurrent) for actor in self.actors], dim=-2
        )
        values_all = torch.stack(
            [critic(recurrent).squeeze(-1) for critic in self.critics], dim=-1
        )
        logits = (logits_all * persona.unsqueeze(-1)).sum(dim=-2)
        values = (values_all * persona).sum(dim=-1)
        return PersonaModelOutput(
            logits=logits,
            logits_all=logits_all,
            values=values,
            values_all=values_all,
            hidden=recurrent_hidden,
        )
