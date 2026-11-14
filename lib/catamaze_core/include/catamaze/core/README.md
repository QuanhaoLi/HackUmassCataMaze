## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:13 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: contain public domain types and deterministic engine interfaces.
- 架构思路：按稳定概念拆分头文件，避免 platform symbols and hidden mutable globals.

## folder structure
|-README.md — Documents public Game Core headers.
|-version.hpp — Exposes stable product, rules, and Game Core version identifiers.

## To-Dos
- Add types, PRNG, map, queue, observation, AI, and engine headers with focused ownership.
