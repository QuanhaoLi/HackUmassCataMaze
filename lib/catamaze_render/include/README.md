## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:11 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: expose stable public headers for pixel rendering.
- 架构思路：namespace hierarchy keeps framebuffer contracts portable and driver-free.

## folder structure
|-README.md — Documents the renderer include root.
|-catamaze/ — Provides the project namespace include hierarchy.

## To-Dos
- Keep display-driver and browser types out of this tree.
