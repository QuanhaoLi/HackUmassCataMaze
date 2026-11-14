## header
Created at: 2026-11-14 18:52 EST
Created by: Codex
Last Modified at: 2026-11-14 18:52 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: own immutable V2 smoke, qualification, warm-start, and production-candidate configurations.
- 架构思路：V2 configurations extend frozen V1 environment/reward semantics but never overwrite `configs/rl/ppo_16gb.yaml`.

## folder structure
|-README.md — Defines the isolated V2 configuration boundary.

## To-Dos
- Add configs only after `V1_FREEZE_COMMIT` and checkpoint SHA-256 are recorded.
