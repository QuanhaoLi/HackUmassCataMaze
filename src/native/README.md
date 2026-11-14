## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:26 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: compose and launch the Native CataMaze simulator.
- 架构思路：main remains thin; HTTP, process signals, and OS time are adapter concerns around shared libraries.

## folder structure
|-README.md — Documents the Native executable entry point.
|-main.cpp — Provides the headless interactive Native game and composes shared libraries.

## To-Dos
- Add the loopback browser adapter during M2 without moving rules into the executable.
