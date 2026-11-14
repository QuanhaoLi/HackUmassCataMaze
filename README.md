## header
Created at: 2026-11-13 23:42 EST
Created by: Codex
Last Modified at: 2026-11-14 00:16 EST
Last Modified by: Codex

## brief intro
- Goal for this repository: build the product-grade CataMaze game and its trainable, personality-conditioned AI agents.
- 架构思路：先以 `agents/` 固化工程约束，以 `docs/` 固化游戏环境和强化学习合同；后续实现必须先更新对应文档，再按清晰分层落代码与测试。

## folder structure
|-README.md — Introduces the repository and indexes its top-level structure.
|-.gitignore — Excludes local operating-system metadata from version control.
|-agents/ — Contains mandatory operating instructions for coding agents; see `agents/README.md`.
|-docs/ — Contains the normative game-rule and reinforcement-learning specifications; see `docs/README.md`.

## To-Dos
- Implement the deterministic game environment defined in `docs/gamerules.md`.
- Implement and validate the reinforcement-learning system defined in `docs/reward.md`.
- Add a README before adding any new folder or subfolder.
