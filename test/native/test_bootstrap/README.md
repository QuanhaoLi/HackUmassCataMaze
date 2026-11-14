## header
Created at: 2026-11-14 02:13 EST
Created by: Codex
Last Modified at: 2026-11-14 02:13 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: prove the pinned Native toolchain can compile and execute GoogleTest against Game Core.
- 架构思路：保持最小 smoke suite；后续规则测试进入独立、可筛选的 sibling suites。

## folder structure
|-README.md — Documents the bootstrap test suite.
|-test_bootstrap.cpp — Verifies stable product and rules version identifiers.

## To-Dos
- Retain as a fast build-chain diagnostic after broader tests are added.
