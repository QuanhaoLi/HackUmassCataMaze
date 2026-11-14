## header
Created at: 2026-11-14 03:34 EST
Created by: Codex
Last Modified at: 2026-11-14 03:34 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: define pinned recurrent-PPO configurations for smoke, qualification, and production runs.
- 架构思路：the 16GB baseline is authoritative; shorter runs override duration without silently changing model or PPO semantics.

## folder structure
|-README.md — Introduces RL configuration files.

## To-Dos
- Add the validated `ppo_16gb.yaml` only after its parser and schema tests exist.
