## header
Created at: 2026-11-13 23:33 EST
Created by: Codex
Last Modified at: 2026-11-14 00:16 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: maintain the product-level CataMaze game-rule, hardware, and reinforcement-learning specifications.
- 架构思路：将确定性的游戏环境规则、硬件约束与可迭代的强化学习设计分离；`gamerules.md` 是环境与客户端共同遵守的规则真源，`hardware.md` 记录设备与接线约束，`reward.md` 是奖励、神经网络、训练和验收的工程真源。

## folder structure
|-README.md — Introduces and indexes the product documentation in this folder.
|-gamerules.md — Defines the complete normative game rules, state transitions, observations, actions, combat, terminal conditions, and edge cases.
|-hardware.md — Records the current controller, display, input, audio, power, and wiring constraints.
|-reward.md — Defines the planned reinforcement-learning objective, reward contract, neural network, 16GB-GPU training pipeline, evaluation, and release gates.

## To-Dos
- Keep all specifications synchronized whenever the environment contract, hardware interface, observation schema, action space, reward function, or model architecture changes.
- Add implementation ADRs before changing any frozen rule or training contract.
