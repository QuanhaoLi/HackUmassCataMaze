<!--
Created at: 2026-11-14 18:52 EST
Created by: Codex
Last Modified at: 2026-11-14 20:40 EST
Last Modified by: Codex
-->

# CataMaze V2 model candidate line

## Purpose

本目录只定义 V2 人格模型候选线。V2 模型团队负责架构、训练、评估、导出、量化和候选交付包；不修改、不构建、不上传、不切换正在由另一位负责人部署的 V1 产品固件。

## Documents

- `persona-policy-plan.md` — 冻结 V1/V2 边界，并规定从合同快照到 V2 模型交付、再到部署负责人后续落地的完整工程顺序。
- `reward-v3.md` — Defines the isolated post-ablation persona reward correction without changing V1 reward v2.
- `status.md` — 记录 V2 当前不可变 lineage、已通过门、失败证据和正在执行的阶段。
- `style-constraints.md` — Freezes the post-reward causal policy constraints and their bounded loss.

## Authority

- 当前生产事实仍由 `../model.md`、`../hardware.md`、ADR-0007 和 ADR-0009 定义。
- 本目录中的任何 V2 候选都不是生产模型。
- 只有产品负责人显式批准晋级，并由 V1 部署负责人完成独立候选固件门禁后，V2 才能成为新的 Resident Policy。

## Scope boundary

V2 模型工作允许新增以下命名空间，实施时不得就地改写 V1 文件：

- `training/v2/`
- `configs/rl/v2/`
- `tests/training/v2/`
- `scripts/v2/`
- `docs/v2/`
- `runs/v2/` 与 `.artifacts/v2/`（忽略的运行产物）

V2 模型负责人不得修改或调用以下生产面：

- `src/esp32/`
- `platformio.ini`
- `scripts/esp32_*`
- V1 `policy_release.json`、V1 `.espdl` 和默认产品环境
- 物理 ESP32 上传、擦除或切换

共享的 Native 环境、observation、action mask和训练基础设施只能作为只读依赖。若 V2 必须改变共享合同，必须先新增 ADR并取得产品负责人批准，不能在模型实现中顺手修改。
