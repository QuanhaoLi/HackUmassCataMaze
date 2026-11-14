## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:13 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: verify Game Core, application, renderer, and Native HTTP behavior with GoogleTest.
- 架构思路：tests are grouped by subsystem and use explicit seeds and virtual time for reproducibility.

## folder structure
|-README.md — Documents Native test ownership.
|-test_bootstrap/ — Proves the pinned compiler, library discovery, and GoogleTest chain.

## To-Dos
- Add focused M1 and M2 suites while retaining the bootstrap diagnostic.
