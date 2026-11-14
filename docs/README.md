## header
Created at: 2026-11-13 23:33 EST
Created by: Codex
Last Modified at: 2026-11-14 04:33 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: maintain the product-level CataMaze game, engineering structure, restrictions, hardware, and reinforcement-learning specifications.
- 架构思路：将确定性的游戏规则、工程结构、不可违反的限制、硬件事实与强化学习设计分离；每份文档只有一个清晰职责，并由本 README 建立索引。

## folder structure
|-README.md — Introduces and indexes the product documentation in this folder.
|-audio.md — Defines optional USB Serial audio events, the Mac speaker companion, and disconnect behavior.
|-gamerules.md — Defines the complete normative game rules, state transitions, observations, actions, combat, terminal conditions, and edge cases.
|-hardware.md — Records the current controller, display, input, audio, power, and wiring constraints.
|-restrictions.md — Defines non-negotiable architecture, determinism, safety, hardware, scope, and testing restrictions.
|-reward.md — Defines the planned reinforcement-learning objective, reward contract, neural network, 16GB-GPU training pipeline, evaluation, and release gates.
|-adr/ — Records durable architecture decisions that clarify or change frozen contracts.
|-structure.md — Freezes the C++17 architecture, pinned toolchain, target matrix, directory plan, browser contract, and quality strategy.

## To-Dos
- Keep all specifications synchronized whenever the environment contract, hardware interface, observation schema, action space, reward function, or model architecture changes.
- Add implementation ADRs before changing any frozen rule or training contract.
- Keep milestone acceptance gates synchronized with `../plan.md`.
