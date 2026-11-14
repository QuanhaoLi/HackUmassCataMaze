## header
Created at: 2026-11-14 03:34 EST
Created by: Codex
Last Modified at: 2026-11-14 04:38 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: define pinned recurrent-PPO configurations for smoke, qualification, and production runs.
- 架构思路：the 16GB baseline is authoritative; shorter runs override duration without silently changing model or PPO semantics.

## folder structure
|-README.md — Introduces RL configuration files.
|-ppo_16gb.yaml — Defines the authoritative 16GB recurrent-PPO baseline and contract versions.

## To-Dos
- Add a release override only when it changes explicit, versioned values from the baseline.
