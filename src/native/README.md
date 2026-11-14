## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:13 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: compose and launch the Native CataMaze simulator.
- 架构思路：main remains thin; HTTP, process signals, and OS time are adapter concerns around shared libraries.

## folder structure
|-README.md — Documents the Native executable entry point.
|-main.cpp — Boots the Native target and composes adapters around shared libraries.

## To-Dos
- Expand the bootstrap executable with the Native application and browser adapter during M1/M2.
