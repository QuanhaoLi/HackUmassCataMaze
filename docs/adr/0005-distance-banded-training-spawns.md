<!--
Created at: 2026-11-14 07:49 EST
Created by: Codex
Last Modified at: 2026-11-14 07:49 EST
Last Modified by: Codex
-->

# ADR-0005: Distance-banded training spawns

## Status

Accepted after reward v2 improved movement but did not produce sufficient combat at 10M agent steps.

## Context

Reward v2 removed the backtracking penalty and increased first-visit rates by roughly two to five times, but the fixed full-map evaluation still produced only `2.54%` stationary-player deaths at 10M steps. Uniform random spawns in a 50×50 perfect maze make player encounters extremely rare before the policy has learned search, aim, and shooting. Sparse encounter data prevents the early stationary/random-valid curriculum from teaching its intended combat primitives.

## Decision

1. Curriculum A training spawns the player uniformly, then places each AI on a distinct reachable cell within shortest-path distance `12` of the player.
2. Curriculum B expands the maximum AI-player spawn distance to `30`.
3. Curriculum C and D use uniform full-map spawns.
4. Fixed evaluation always uses uniform full-map spawns, regardless of training stage.
5. No reward coefficient, model architecture, PPO parameter, opponent distribution, or DDP topology changes in this comparison.

## Consequences

- `training_config_version` advances to `catamaze.training.ppo16gb.v9`.
- Spawn-distance state is checkpointed and restored per rank.
- Curriculum A produces dense combat experience without leaking player position into deployed observations.
