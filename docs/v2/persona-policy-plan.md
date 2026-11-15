<!--
Created at: 2026-11-14 18:52 EST
Created by: Codex
Last Modified at: 2026-11-14 19:41 EST
Last Modified by: Codex
-->

# V2 Persona Policy — 工程与完整落地计划

## 1. 交付目标

V2 只交付一个可审计的模型候选包，不部署固件。候选模型在保持 V1 环境、5×5 observation、九动作空间、合法动作 mask和单模型常驻约束不变的前提下，让 aggressive、cautious、explorer 形成稳定、可测量、可复现的神经网络行为差异。

V2 最终仍是一个共享模型，而不是三套完整模型：

- 共享视觉编码器、scalar encoder、fusion 和 GRU-256；
- persona one-hot 驱动轻量人格调制；
- 三套独立 actor head；
- 三套独立 critic head只参与训练，不进入最终 ESP32 actor-only 导出；
- 三个 AI 各自保留独立 hidden state；
- C++ 合法动作 mask继续是唯一动作合法性权威。

## 2. 严格版本与所有权拆分

### 2.1 V1 生产线

V1 由当前部署负责人独占。V2 工作不得改变其代码、构建、模型、manifest、串口 schema、默认 PlatformIO环境或物理板状态。

V1 冻结信息由部署负责人完成发布后提供：

- `V1_FREEZE_COMMIT`；
- FP32 checkpoint绝对路径和 SHA-256；
- V1 `.espdl` SHA-256；
- V1 固定评估报告；
- V1 Resident Policy manifest版本。

在 `V1_FREEZE_COMMIT` 未明确前，V2 可以落实文档、测试骨架和独立模型代码，但不得启动正式 warm-start训练或生成可晋级候选。

### 2.2 V2 候选线

V2 使用独立标识，禁止复用含糊的 `latest` 作为交付身份：

| 维度 | V2 标识 |
|---|---|
| Candidate line | `catamaze.policy.persona.v2-candidate` |
| Architecture | `catamaze.model.persona-rppo.v2` |
| Training contract | `catamaze.training.persona.v2` |
| Environment | 继续使用 `catamaze.environment.v1` |
| Observation | 继续使用 `catamaze.observation.v1` |
| Action schema | 继续使用九动作 V1 合同 |
| Initial reward | 继续使用 `catamaze.reward.v2` |
| Export contract | `catamaze.esp-step.persona.v2` |

架构实验和 reward 实验不得混在同一次正式 run。第一轮 V2 只改变模型与优化聚合方式，保持 V1 reward不变；若人格门槛仍失败，必须另开 `catamaze.reward.v3` ADR、配置和 run ID。

### 2.3 允许写入范围

模型实现阶段只允许修改或新增：

```text
training/v2/
configs/rl/v2/
tests/training/v2/
scripts/v2/
docs/v2/
```

运行产物只能写入：

```text
runs/v2/<run-id>/
.artifacts/v2/<candidate-id>/
```

每次提交前必须执行允许范围审计。若 `git diff --name-only` 出现 V1 生产路径，V2 工作立即停止，不得通过一起提交或自动格式化掩盖越界。

## 3. V2 网络设计

### 3.1 保持不变的输入

- `spatial [B,T,13,5,5]`；
- `scalar [B,T,46]`；
- `hidden [1,B,256]`；
- persona仍来自 scalar索引 `43:46`；
- 每个 AI 只能看到自己的合法5×5 observation和自己的 recurrent state。

### 3.2 共享主干

共享主干从 V1 checkpoint迁移：

1. Conv2D `13→64`；
2. GroupNorm + SiLU；
3. 64-channel residual block；
4. visual projection `1600→256`；
5. scalar MLP `46→128→128`；
6. fusion `384→256`；
7. GRU `256→256`。

### 3.3 人格调制

在 fusion 输出进入 GRU 前应用零初始化的 affine modulation：

```text
z_persona = z * (1 + gamma_persona) + beta_persona
```

`gamma` 和 `beta` 各为 `[3,256]`。用 persona one-hot 与参数表做 MatMul，再使用 Add/Mul；不引入 ESP-DL 不支持的动态控制流。零初始化保证模型迁移完成时人格调制是恒等映射。

### 3.4 独立 heads

- actor：三套 `Linear(256,9)`；
- critic：三套 `Linear(256,1)`，仅训练使用；
- actor初始化：三套都复制 V1 actor；
- critic初始化：三套都复制 V1 critic。

因此 V2 在 step 0必须与 V1 数值等价；人格差异只能来自后续训练，不能来自随机初始化事故。

预计新增参数低于7,000，总参数保持低于1.03M。V2 模型候选预算：

- FP32参数量 `<1.03M`；
- W8A16 `.espdl` `≤1.8MB`；
- 预计 PSRAM模型分配 `≤2.0MB`；
- 预计内部模型分配 `≤190KB`。

## 4. 训练语义

### 4.1 每人格独立统计

三个 AI 继续共享主干梯度，但以下量必须逐人格计算：

- return；
- GAE；
- advantage normalization；
- value loss；
- entropy；
- KL、clip fraction和explained variance报告。

每个 minibatch先求各人格有效样本均值，再对三个人格等权平均。不能因某个人格存活更久、transition更多而让它控制共享梯度。

### 4.2 Reward 变更纪律

V2 架构首轮完整复用 `catamaze.reward.v2`。只有在下列条件同时成立时，才允许提议 reward v3：

1. 多头和人格调制实现正确；
2. step-0 V1等价测试通过；
3. 至少25M agent steps训练完成；
4. 效果能力没有退化，但人格差异门槛仍失败；
5. ablation证明失败不是 head选择、loss聚合或评估缺陷。

任何 reward v3必须独立配置、独立 checkpoint链和独立报告，不能覆盖 V2 架构基线。

### 4.3 可复现性

- 训练使用仓库 PRNG与显式 seed；
- checkpoint保存模型、三人格 optimizer状态、scheduler、curriculum、全局 RNG和每 rank采样状态；
- resume后的下一段 rollout必须逐位复现；
- V2 候选推理默认使用 masked argmax作为工程基线；若未来采用 seeded categorical sampling，必须单独 ADR并把策略 RNG纳入 state hash和存档合同。

## 5. 工程执行顺序

以下阶段不可交换。每一阶段只有在退出门全部通过后才能进入下一阶段。

### Phase 0 — 文档与隔离门

工作：

- 接受 ADR-0010；
- 建立本目录；
- 冻结允许写入范围；
- 记录 V1 部署负责人和 V2 模型负责人边界。

退出门：

- 文档评审通过；
- `git diff` 不包含任何 V1 生产修改；
- 未执行训练、量化、固件编译或上传。

### Phase 1 — V1 合同快照

工作：

- 从部署负责人读取 `V1_FREEZE_COMMIT`；
- 对 checkpoint、ONNX、ESP-DL和manifest计算 SHA-256；
- 冻结 V1 固定评估 seeds、opponent pool和persona指标；
- 在 V2 manifest草案中记录完整 lineage。

退出门：所有 V1 输入均有不可变路径、hash和版本；不得依赖可移动的 `latest.pt`。

### Phase 2 — V1 基线复算

工作：

- 只读加载 V1 checkpoint；
- 在固定 seeds上重新运行每人格评估；
- 输出 outcome、shots、hits、death、first visits、revisit、动作分布和pairwise JS divergence；
- 保存原始 episode级结果，不能只保留聚合 JSON。

退出门：复算结果与 V1 发布报告在统计容差内一致，否则先解决基线差异，禁止开始 V2 训练。

### Phase 3 — V2 模型与迁移测试

工作：

- 在 `training/v2/` 实现共享主干、人格调制和三头 actor/critic；
- 实现 V1→V2 checkpoint迁移器；
- 零初始化 modulation并复制 heads；
- 写 shape、gradient、head选择、序列 reset和序列化测试。

退出门：

- 同一 observation/hidden下，迁移后的三个 head与 V1 logits最大误差 `≤1e-6`；
- V2 value与 V1 value最大误差 `≤1e-6`；
- persona one-hot只选择对应 head；
- 每个 head均收到非零梯度；
- 不修改 V1 `training/model.py`。

### Phase 4 — V2 PPO 聚合与回放

工作：

- 实现逐人格 GAE、normalization和等权 loss聚合；
- 验证死亡 mask、episode reset和三份 hidden隔离；
- 实现 V2 checkpoint save/resume；
- 增加数值故障和非法动作断言。

退出门：golden rollout、resume-next-rollout、NaN/Inf、action mask和梯度测试全部通过。

### Phase 5 — CPU smoke

工作：100k agent-step CPU smoke，覆盖收集、更新、checkpoint、resume和固定评估。

退出门：

- 零非法动作、零 NaN/Inf；
- 三个 head参数均发生更新；
- 内存无持续增长；
- resume精确复现。

### Phase 6 — 单 V100资格验证

工作：使用现有 `/home/a/minimind-venv`，通过清华 PyPI镜像补齐缺失包；在物理 GPU 1执行1M agent-step资格运行。

退出门：吞吐、显存、KL、clip fraction和persona loss均稳定；不得新建 venv、改变驱动、系统 CUDA或服务器电源/网络状态。

### Phase 7 — 4×V100 DDP资格验证

工作：四张 V100各绑定一个 rank，共同训练一个模型；不做四个 seed。先复用 V1 已验证的全局256 env/128 sequence minibatch拓扑，再用短 benchmark确认 V2吞吐。

退出门：

- DDP相对单卡有效加速；
- 三人格 loss和advantage跨 rank正确归约；
- rank 0独占 checkpoint/evaluation；
- 无 OOM和cuBLAS allocation failure。

### Phase 8 — 分阶段 warm-start训练

按顺序执行：

1. `0–5M`：课程 A，冻结共享视觉主干和GRU，只训练 modulation、actor heads和critic heads；
2. `5–10M`：课程 B，解冻 fusion与GRU，主干低学习率；
3. `10–25M`：课程 C，全模型低学习率联合微调；
4. `25–50M`：只有效果与人格曲线持续改善时进入课程 D；
5. `50–100M`：只有固定评估仍未收敛且无退化时使用，不因预算存在而盲跑。

每5M agent steps固定评估并生成不可覆盖的 checkpoint。任何阶段效果显著退化时回退到上一候选，不在同一 run中临时改 reward。

### Phase 9 — 人格与效果验收

最终候选使用未参与训练的配对 seed；每人格、每玩家对手至少1,000局并报告95%置信区间。

硬门：

- aggressive每100 tick射击和有效命中至少比三人格均值高20%；
- cautious死亡率相对 aggressive至少低15%；
- explorer每100 tick首次访问格至少比三人格均值高20%，且重访率显著低于 aggressive；
- 三人格动作分布不能全部 pairwise JS `<0.02`；
- 任一人格阻止玩家逃脱的能力不得比 V1 同人格低超过5个百分点；
- AI误伤率不高于总命中5%；
- 不能通过增加 timeout伪装效果提升。

同时执行 counterfactual persona suite：固定完全相同的 observation和hidden，只切换 persona，验证 head选择和动作分布差异。

### Phase 10 — Ablation与候选选择

至少比较：

- V1生产模型；
- V2完整模型；
- 无 modulation；
- 单共享 actor head；
- 去除 persona输入；
- V2 feed-forward无GRU版本。

只有 V2完整模型同时赢得人格门和效果门时才能成为候选；仅仅“看起来不同”不构成晋级依据。

### Phase 11 — Actor-only导出

导出固定 batch-1、single-step ONNX：

```text
inputs:
  spatial      [1,13,5,5]
  scalar       [1,46]
  hidden       [1,1,256]
outputs:
  logits_all   [1,3,9]
  next_hidden  [1,1,256]
```

critic heads不得进入 ESP32图。GroupNorm继续做等价 primitive分解。PyTorch与ONNX在随机和真实 recurrent样本上的最大误差必须 `≤1e-5`，并执行 ESP-DL operator allowlist检查。

### Phase 12 — 逐人格量化

量化 calibration必须人格平衡：每人格至少512条真实 recurrent样本，且 calibration与evaluation完全分离。

顺序：

1. W8A16；
2. 若任一人格失败，定位敏感 op并采用混合精度；
3. 仍失败才使用 W16A16，不直接放宽门槛。

每人格至少10,000条合法 observation。硬门：

- 每个人格 masked action agreement `≥99.0%`；
- 不允许只用三人格总平均掩盖某个 head失败；
- 无 masked action被选择；
- hidden error、logit error和逐 head混淆矩阵完整保存。

### Phase 13 — 候选交付包

V2 模型负责人只交付以下不可变目录，不修改产品固件：

```text
.artifacts/v2/<candidate-id>/
  checkpoint.pt
  model_fp32.onnx
  model_w8a16.espdl
  manifest.json
  training_config.yaml
  training_metrics.jsonl
  evaluation_summary.json
  evaluation_episodes.jsonl
  ablations.json
  quantization_report.json
  operator_report.json
  checksums.sha256
  HANDOFF.md
```

`manifest.json`必须包含：V1 lineage、代码 commit、所有合同版本、参数量、训练 steps、seed、DDP topology、每人格门槛、文件 hash、工具版本和已知限制。

退出门：从空的只读校验目录按 `checksums.sha256`验证通过；候选包中没有 `latest`软引用、绝对临时路径或未记录依赖。

到此 V2 模型负责人的任务结束。不得自行修改 `src/esp32`、构建产品固件或上传板卡。

## 6. 交付后的完整落地顺序

以下步骤由部署负责人执行，写入本文是为了让模型方案具备完整落地闭环；不授权 V2 模型负责人执行。

### Deploy 1 — 交付验签

- 在独立目录验证所有 SHA-256；
- 核对 manifest合同与当前产品；
- 复跑最小 ONNX/ESP-DL参考向量；
- 拒绝任何缺失 lineage或版本不匹配的候选。

### Deploy 2 — 独立候选构建面

- 新建 `esp32s3_v2_candidate`环境；
- 不修改 V1 默认环境和 V1模型文件；
- V2 adapter、manifest和串口 schema使用 V2命名；
- 编译时仍保留 V1启发式 fallback。

### Deploy 3 — Compile-only门

- Native完整测试；
- V2 release-manifest测试；
- ESP32 candidate compile；
- Flash、静态 RAM和链接 map审计；
- 不接触物理板。

### Deploy 4 — Native replay与shadow对比

- 对同一 observation/hidden同时运行 V1和V2；
- 记录逐人格动作差异，不改变世界状态；
- 验证 head选择、hidden reset、state hash和fallback原子性。

### Deploy 5 — 独立硬件资格验证

- 只允许使用非 V1部署中的测试板，或由部署负责人明确安排维护窗口；
- 先执行只读芯片/Flash/PSRAM预检；
- 运行 startup reference envelope；
- 测量三 AI 顺序推理 p50/p95/p99、内部 RAM、PSRAM和栈余量；
- 硬门：p95 `≤900ms`，且相对 V1 126ms参考不得无解释地显著退化。

### Deploy 6 — 10,000-tick耐久

- 覆盖12/20/30/50地图；
- 覆盖三人格存活/死亡、暂停、重开和终局；
- 零 watchdog、零 heap增长、零 hidden串扰、零 mixed model/fallback tick；
- 记录真实 fallback计数，必须为0。

### Deploy 7 — 产品行为验收

- 固定种子盲测 V1/V2；
- 验证风格能被观察但不会破坏公平性；
- 验证玩家无法通过 UI获知隐藏 persona state或模型内部值；
- 保留 V1结果作为回滚基线。

### Deploy 8 — 显式晋级

只有产品负责人明确批准后：

- 将 V2 candidate artifact晋级为 Resident Policy；
- 更新默认产品环境、release manifest和产品文档；
- 保留 V1 artifact、commit和回滚命令；
- 再执行一次完整受保护发布流程。

### Deploy 9 — 发布后观察与回滚

- 本地记录模型版本、启动门、推理延迟和fallback原因；
- 不引入网络遥测；
- 任一 tensor、finite、mask、latency或稳定性门失败，原子回退启发式；
- 产品行为退化时按 V1不可变 manifest回滚，不迁移游戏数据、不改变规则版本。

## 7. 禁止的捷径

- 不在 V1 文件中用条件编译塞入 V2；
- 不让 V2 覆盖 V1 `.espdl`、manifest或 `latest.pt`；
- 不在同一正式 run同时改变架构、reward和curriculum；
- 不用四张 GPU跑四个随意 seed替代单模型 DDP效率；
- 不用总平均量化精度替代逐人格精度；
- 不因模型能编译就宣称能在 ESP32运行；
- 不由 V2 模型负责人自行刷写正在部署 V1 的板卡；
- 不以放宽人格门槛或增加 timeout换取“训练完成”。

## 8. 完成定义

“V2 模型准备好”仅在以下条件全部满足时成立：

1. V1 lineage已冻结并复算；
2. V2 step-0与 V1等价；
3. 训练、resume、DDP和数值门全部通过；
4. 三人格效果与差异硬门全部通过；
5. ablation证明完整设计必要；
6. FP32 ONNX通过数值和operator门；
7. 逐人格量化门通过；
8. 候选交付包 hash完整、可离线复验；
9. 没有修改或部署 V1产品面；
10. `HANDOFF.md`明确列出部署负责人下一步与剩余物理门。

ESP32集成、物理验证和产品晋级属于后续部署流程，不属于 V2 模型准备完成的定义。
