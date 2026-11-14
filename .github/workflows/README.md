## header
Created at: 2026-11-14 02:51 EST
Created by: Codex
Last Modified at: 2026-11-14 02:51 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: define reproducible pull-request and main-branch quality gates.
- 架构思路：workflows call project-owned scripts and never encode a second build or test process.

## folder structure
|-README.md — Documents workflow ownership.
|-native.yml — Builds and tests the Native C++17 product on Linux without hardware access.

## To-Dos
- Keep action versions pinned and mirror locally validated commands only.
