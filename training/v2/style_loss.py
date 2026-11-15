# Created at: 2026-11-14 20:40 EST
# Created by: Codex
# Last Modified at: 2026-11-14 21:03 EST
# Last Modified by: Codex
# Computes bounded V2 style constraints from legal local policy tensors only.

from __future__ import annotations

from itertools import combinations
from math import log

import torch
from torch.nn import functional as F


STYLE_COMPONENT_NAMES = (
    "aggressive_aligned_shot",
    "cautious_low_hp_retreat",
    "explorer_local_frontier",
    "aggressive_vs_cautious_shoot_margin",
    "aggressive_vs_explorer_shoot_margin",
    "explorer_vs_aggressive_move_margin",
    "explorer_vs_cautious_move_margin",
    "js_aggressive_cautious",
    "js_aggressive_explorer",
    "js_cautious_explorer",
)
STYLE_METRIC_NAMES = STYLE_COMPONENT_NAMES + (
    "aggressive_aligned_shot_count",
    "cautious_low_hp_retreat_count",
    "explorer_local_frontier_count",
)


def persona_style_loss(
    logits_all: torch.Tensor,
    action_mask: torch.Tensor,
    spatial: torch.Tensor,
    scalar: torch.Tensor,
    loss_mask: torch.Tensor,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    if logits_all.shape != (*loss_mask.shape, 3, 9):
        raise ValueError("logits_all must have shape [S,T,3,9]")
    if action_mask.shape != (*loss_mask.shape, 9):
        raise ValueError("action_mask must have shape [S,T,9]")
    if spatial.shape != (*loss_mask.shape, 13, 5, 5):
        raise ValueError("spatial must have shape [S,T,13,5,5]")
    if scalar.shape != (*loss_mask.shape, 46):
        raise ValueError("scalar must have shape [S,T,46]")
    if not loss_mask.any():
        zero = logits_all.sum() * 0.0
        return zero, {name: zero for name in STYLE_METRIC_NAMES}

    expanded_mask = action_mask.unsqueeze(-2).expand_as(logits_all)
    masked_logits = logits_all.masked_fill(~expanded_mask, -torch.inf)
    probabilities = torch.softmax(masked_logits, dim=-1)
    move_mass = probabilities[..., :4].sum(dim=-1)
    shoot_mass = probabilities[..., 4:8].sum(dim=-1)

    def active_mean(values: torch.Tensor) -> torch.Tensor:
        return values[loss_mask].mean()

    components: dict[str, torch.Tensor] = {}
    components["aggressive_vs_cautious_shoot_margin"] = F.relu(
        0.15 - (active_mean(shoot_mass[..., 0]) - active_mean(shoot_mass[..., 1]))
    ) / 0.15
    components["aggressive_vs_explorer_shoot_margin"] = F.relu(
        0.15 - (active_mean(shoot_mass[..., 0]) - active_mean(shoot_mass[..., 2]))
    ) / 0.15
    components["explorer_vs_aggressive_move_margin"] = F.relu(
        0.15 - (active_mean(move_mass[..., 2]) - active_mean(move_mass[..., 0]))
    ) / 0.15
    components["explorer_vs_cautious_move_margin"] = F.relu(
        0.10 - (active_mean(move_mass[..., 2]) - active_mean(move_mass[..., 1]))
    ) / 0.10

    player = spatial[..., 5, :, :] > 0.5
    player_up = player[..., :2, 2].any(dim=-1)
    player_down = player[..., 3:, 2].any(dim=-1)
    player_left = player[..., 2, :2].any(dim=-1)
    player_right = player[..., 2, 3:].any(dim=-1)
    shot_target = torch.full(loss_mask.shape, -1, dtype=torch.long, device=logits_all.device)
    shot_target[player_up] = 4
    shot_target[player_down] = 5
    shot_target[player_left] = 6
    shot_target[player_right] = 7
    shot_valid = loss_mask & (shot_target >= 0)
    if shot_valid.any():
        shot_legal = action_mask.gather(
            -1, shot_target.clamp_min(0).unsqueeze(-1)
        ).squeeze(-1)
        shot_valid &= shot_legal
    if shot_valid.any():
        components["aggressive_aligned_shot"] = F.cross_entropy(
            logits_all[..., 0, :][shot_valid], shot_target[shot_valid]
        ) / log(9.0)
    else:
        components["aggressive_aligned_shot"] = logits_all.sum() * 0.0
    components["aggressive_aligned_shot_count"] = shot_valid.sum().to(
        dtype=logits_all.dtype
    )

    retreat_target = torch.full_like(shot_target, -1)
    retreat_target[player_up] = 1
    retreat_target[player_down] = 0
    retreat_target[player_left] = 3
    retreat_target[player_right] = 2
    sound = scalar[..., 25:34]
    sound_present, sound_bucket = sound.max(dim=-1)
    sound_targets = torch.tensor(
        [1, 1, 2, 0, 0, 0, 3, 1, -1],
        dtype=torch.long,
        device=logits_all.device,
    )
    use_sound = (retreat_target < 0) & (sound_present > 0)
    retreat_target[use_sound] = sound_targets[sound_bucket[use_sound]]
    retreat_valid = loss_mask & (scalar[..., 0] <= 0.60) & (retreat_target >= 0)
    if retreat_valid.any():
        retreat_legal = action_mask.gather(
            -1, retreat_target.clamp_min(0).unsqueeze(-1)
        ).squeeze(-1)
        retreat_valid &= retreat_legal
    if retreat_valid.any():
        components["cautious_low_hp_retreat"] = F.cross_entropy(
            logits_all[..., 1, :][retreat_valid], retreat_target[retreat_valid]
        ) / log(9.0)
    else:
        components["cautious_low_hp_retreat"] = logits_all.sum() * 0.0
    components["cautious_low_hp_retreat_count"] = retreat_valid.sum().to(
        dtype=logits_all.dtype
    )

    fog = spatial[..., 3, :, :]
    frontier_scores = torch.stack(
        (
            fog[..., 0:3, 1:4].sum(dim=(-2, -1)),
            fog[..., 2:5, 1:4].sum(dim=(-2, -1)),
            fog[..., 1:4, 0:3].sum(dim=(-2, -1)),
            fog[..., 1:4, 2:5].sum(dim=(-2, -1)),
        ),
        dim=-1,
    )
    move_legal = action_mask[..., :4]
    frontier_target = frontier_scores.masked_fill(~move_legal, -torch.inf).argmax(dim=-1)
    frontier_valid = loss_mask & move_legal.any(dim=-1)
    if frontier_valid.any():
        components["explorer_local_frontier"] = F.cross_entropy(
            masked_logits[..., 2, :4][frontier_valid], frontier_target[frontier_valid]
        ) / log(4.0)
    else:
        components["explorer_local_frontier"] = logits_all.sum() * 0.0
    components["explorer_local_frontier_count"] = frontier_valid.sum().to(
        dtype=logits_all.dtype
    )

    persona_names = ("aggressive", "cautious", "explorer")
    for left, right in combinations(range(3), 2):
        p = probabilities[..., left, :].clamp_min(1e-8)
        q = probabilities[..., right, :].clamp_min(1e-8)
        midpoint = 0.5 * (p + q)
        divergence = 0.5 * (
            (p * (p.log() - midpoint.log())).sum(dim=-1)
            + (q * (q.log() - midpoint.log())).sum(dim=-1)
        )
        components[f"js_{persona_names[left]}_{persona_names[right]}"] = F.relu(
            0.02 - active_mean(divergence)
        ) / 0.02

    ordered = [components[name] for name in STYLE_COMPONENT_NAMES]
    return torch.stack(ordered).mean(), components
