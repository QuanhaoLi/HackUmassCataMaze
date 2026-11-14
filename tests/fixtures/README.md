## header
Created at: 2026-11-14 03:34 EST
Created by: Codex
Last Modified at: 2026-11-14 03:34 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: store immutable, human-reviewed inputs and expected outputs for training contract tests.
- 架构思路：fixtures are versioned alongside environment and reward schemas; generated diagnostics remain outside the repository.

## folder structure
|-README.md — Introduces fixture ownership.
|-reward/ — Contains structured golden trajectories for reward calculation.

## To-Dos
- Review fixture changes as contract changes, not ordinary snapshot updates.
