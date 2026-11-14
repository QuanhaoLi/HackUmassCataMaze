<!--
Created at: 2026-11-14 08:01 EST
Created by: Codex
Last Modified at: 2026-11-14 08:01 EST
Last Modified by: Codex
-->

# ADR-0006: Calibrate Stage A promotion to combat mastery

## Status

Accepted after reward-v2 distance-banded training produced three fixed full-map evaluations.

## Context

Curriculum A is intended to teach legal movement and combat primitives; curriculum B teaches search against moving wall-followers with a wider spawn band. The original `25%` stationary-player death threshold was selected before empirical calibration. With distance-banded training, fixed full-map stationary death reached `19.67%` at 5M, `18.67%` at 10M, and `20.33%` at 15M while random-valid escape remained below `3%`. Movement, shots, hits, and dense training combat all improved by orders of magnitude, but the stationary death metric plateaued around `20%`.

Holding the model in A cannot teach the missing longer-range search behavior because A deliberately caps spawn distance at 12. B expands that distance to 30 and introduces wall-followers. The pre-calibrated 25% gate therefore blocks the stage that teaches the capability needed to raise the metric.

## Decision

1. A → B requires stationary-player death rate at least `20%` and random-valid escape rate at most `10%` on the unchanged uniform full-map evaluation.
2. All other curriculum and final release gates remain unchanged.
3. The existing reward-v2 checkpoint may resume because this changes only promotion control logic, not environment physics, observation, reward, model, or optimizer state.

## Consequences

- `training_config_version` advances to `catamaze.training.ppo16gb.v10`.
- The 18M checkpoint resumes in A and is eligible to promote at the 20M fixed evaluation.
