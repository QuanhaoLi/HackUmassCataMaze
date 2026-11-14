<!--
Created at: 2026-11-14 07:35 EST
Created by: Codex
Last Modified at: 2026-11-14 07:35 EST
Last Modified by: Codex
-->

# ADR-0004: Remove negative revisit shaping

## Status

Accepted after the first four-V100 DDP curriculum-A run reached 10M agent steps.

## Context

The `dfs-grid-v1` perfect maze contains dead ends that require backtracking through visited cells. Reward v1 charged aggressive/cautious `-0.002` and explorer `-0.008` for every successful move to a visited cell, while WAIT incurred only the persona tick cost. At 5M and 10M fixed evaluations the shared policy converged toward waiting: stationary player death rate fell from approximately `1.17%` to `0.78%`, timeout exceeded `99%`, and effective hits remained near zero despite increasing aggressive shot frequency.

This is a reward/environment mismatch. Backtracking is required navigation, not inherently undesirable behavior. First-visit bonuses already distinguish exploration without making recovery from a dead end worse than waiting.

## Decision

1. Reward v2 keeps all first-visit bonuses and the `+5.0` exploration cap.
2. A successful move to a visited cell has zero exploration shaping for all personas.
3. Every non-terminal tick cost remains, so WAIT is not free.
4. No other reward coefficient, curriculum opponent mix, model architecture, PPO parameter, or DDP topology changes in the v2 comparison run.
5. The v1 11M checkpoint is retained as diagnostic evidence but is incompatible with reward v2 and is not resumed.

## Consequences

- `reward_version` advances to `catamaze.reward.v2`.
- `training_config_version` advances to `catamaze.training.ppo16gb.v8`.
- A new four-V100 run starts from random initialization and is evaluated at 5M before any additional intervention.
