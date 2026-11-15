## header
Created at: 2026-11-14 18:51 EST
Created by: Codex
Last Modified at: 2026-11-14 18:51 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: own the exact released ESP-DL artifact and its machine-readable release authority.
- 架构思路：`policy_release.json` is the single source for artifact identity, tensor shapes, quantization, runtime compatibility, evaluation evidence, and release gates; generated C++ and upload checks may not redefine those values.

## folder structure
|-README.md — Documents release-artifact ownership and generation rules.
|-catamaze_policy.espdl — Frozen W8A16 ESP-DL artifact embedded into the product firmware.
|-policy_release.json — Canonical model identity, tensor contract, compatibility declaration, evidence, and gate values.

## To-Dos
- Retain prior release manifests and artifacts outside the active filenames when a rollback candidate is promoted.
