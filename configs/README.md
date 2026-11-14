## header
Created at: 2026-11-14 03:34 EST
Created by: Codex
Last Modified at: 2026-11-14 03:34 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: hold immutable, versioned product and training configurations.
- 架构思路：committed configurations contain explicit values and versions; each run stores a resolved copy rather than reading mutable defaults during resume.

## folder structure
|-README.md — Introduces configuration ownership.
|-rl/ — Contains reinforcement-learning run configurations.

## To-Dos
- Keep configuration schemas synchronized with checkpoint metadata and release reports.
