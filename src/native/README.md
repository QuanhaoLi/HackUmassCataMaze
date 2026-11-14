## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:34 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: compose and launch the Native CataMaze simulator.
- 架构思路：main remains thin; HTTP, process signals, and OS time are adapter concerns around shared libraries.

## folder structure
|-README.md — Documents the Native executable entry point.
|-main.cpp — Provides the headless interactive Native game and composes shared libraries.
|-native_server.cpp — Implements the loopback HTTP adapter, single simulation owner, and immutable snapshots.
|-native_server.hpp — Declares Native server options and lifecycle.

## To-Dos
- Keep HTTP and operating-system concerns isolated from reusable libraries.
