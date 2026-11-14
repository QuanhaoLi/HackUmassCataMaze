## header
Created at: 2026-11-14 02:51 EST
Created by: Codex
Last Modified at: 2026-11-14 02:51 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: contain bounded Native verification executables separate from the playable product entry point.
- 架构思路：tools reuse public application contracts, emit machine-checkable evidence, and never become runtime dependencies.

## folder structure
|-README.md — Documents Native verification executable ownership.
|-randomized.cpp — Runs deterministic randomized games while checking domain invariants every tick.

## To-Dos
- Keep tools milestone-scoped and remove any duplicate domain logic.
