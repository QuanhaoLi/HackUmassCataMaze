## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:11 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: expose stable public headers for application coordination.
- 架构思路：namespace hierarchy isolates application interfaces from domain and platform implementations.

## folder structure
|-README.md — Documents the public application include root.
|-catamaze/ — Provides the project namespace include hierarchy.

## To-Dos
- Keep platform-specific types out of public interfaces.
