## header
Created at: 2026-11-14 03:34 EST
Created by: Codex
Last Modified at: 2026-11-14 04:51 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: hold reward golden trajectories with explicit events, state deltas, components, and totals.
- 架构思路：each fixture isolates one reward rule and names its environment and reward contract versions.

## folder structure
|-README.md — Introduces reward fixtures.
|-v1.yaml — Defines reviewed terminal, combat-credit, timeout, and movement-cost trajectories.

## To-Dos
- Add one isolated fixture for every future reward defect before changing its implementation.
