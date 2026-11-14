<!--
Created at: 2026-11-13 23:41 EST
Created by: Codex
Last Modified at: 2026-11-14 06:39 EST
Last Modified by: Codex

本文档定义 CataMaze v1 计划采用的强化学习奖励、共享循环策略网络、16GB GPU 训练流程与产品发布门槛。
-->

# CataMaze v1 强化学习、奖励与 16GB GPU 训练规格

## 1. 文档目标

本文件是 AI 训练系统的工程规格，不是概念草稿。实现必须与 `docs/gamerules.md` 的环境规则一致，并满足以下目标：

1. 三个 AI 使用同一个参数共享模型；
2. 每个 AI 保有独立的 observation、循环隐藏状态和 reward；
3. 人格通过条件输入和奖励系数产生可测量的行为差异；
4. 训练时可以使用特权信息计算 reward，但部署推理只能使用合法 observation；
5. 单张 16GB NVIDIA GPU 可以稳定完成训练、评估、断点恢复和导出；
6. 模型发布必须通过规则一致性、基线对比、人格差异、稳定性和性能门槛。

本文档中的“环境步”指一个完整游戏 tick；一个环境步最多产生三个 AI transition。“智能体步”指一个 AI 的单条 transition。训练规模必须明确使用哪一种计数，不得混用。

## 2. 问题定义

CataMaze 是部分可观测多智能体环境。对第 `i` 个 AI，在 tick `t`：

```text
oᵢ,t, hᵢ,t → πθ(aᵢ,t | oᵢ,t, hᵢ,t, personaᵢ)
             → environment.step(actions)
             → rᵢ,t, oᵢ,t+1, doneᵢ,t+1
```

- `oᵢ,t`：该 AI 的合法局部观察；
- `hᵢ,t`：该 AI 自己的循环隐藏状态；
- `personaᵢ`：`aggressive`、`cautious` 或 `explorer`；
- `aᵢ,t`：9 个离散动作之一；
- `rᵢ,t`：该 AI 独立计算的标量奖励；
- `doneᵢ,t`：该 AI 死亡或整局结束。

训练目标是最大化折扣回报：

```text
Gᵢ,t = Σₖ γᵏ rᵢ,t+k
```

v1 采用带合法动作掩码的 Recurrent PPO。采用 PPO 而不是纯启发式或首选 DQN 的原因：

- 动作空间小而离散，Categorical policy 直接适用；
- on-policy rollout 与多环境并行天然匹配；
- action mask 易于在 logits 层严格实现；
- 共享 actor-critic 与人格条件化简单；
- GRU 能处理 5×5 局部视野造成的部分可观测性；
- 不需要维护易过期的多智能体 replay buffer。

## 3. 训练与部署边界

### 3.1 训练环境

训练器必须直接调用纯内存环境：

```text
reset(seed) → observations
step(actions) → observations, rewards, terminations, truncations, infos
```

训练热路径不得调用 HTTP、数据库、Web UI、Terminal UI 或逐 tick 文本日志。Native 产品适配器、离线评估报告和发布记录不得反向进入训练环境依赖图。

### 3.2 部署环境

部署时模型只能接收 `docs/gamerules.md` 允许的 observation。以下数据只允许用于 reward、评估标签或调试，不得进入网络输入：

- 完整地图；
- 视野外玩家位置；
- 视野外子弹；
- 对手 HP/弹药；
- 最短路径真值；
- 未来动作；
- 随机 seed。

### 3.3 共享参数、独立状态

三个 AI 必须共享同一份 `θ`，但下列状态必须独立：

- GRU hidden state；
- episode return；
- visited 集合；
- reward component 累计；
- termination mask；
- observation normalization state不得按单个角色私有化，必须使用训练集共享统计。

不得把三个 AI 的 observation 拼成一个中央控制器输入。v1 采用集中训练、分散执行：训练器可批量更新共享参数，但每个 AI 的动作只由自己的 observation 和 hidden state决定。

## 4. 网络输入

### 4.1 空间输入

AI 的 5×5 observation 转为 `float32/uint8 [13, 5, 5]` 张量。玩家显示专用的 9×5 视野不属于训练 observation，不得进入本张量、action mask、reward 或循环状态。通道固定如下：

| 通道 | 内容 |
|---:|---|
| 0 | 墙 |
| 1 | 普通可行走地面或入口 `S` |
| 2 | 出口 `E` |
| 3 | 未知/被遮挡 `?` |
| 4 | 自己 |
| 5 | 玩家 |
| 6 | aggressive AI |
| 7 | cautious AI |
| 8 | explorer AI |
| 9 | 向上的子弹 |
| 10 | 向下的子弹 |
| 11 | 向左的子弹 |
| 12 | 向右的子弹 |

每个格子可以同时存在一个地形通道和一个实体/子弹通道。空间输入不得把实体压缩成单个 `P` 字符后再猜身份。

### 4.2 标量输入

标量向量固定为 46 维：

| 部分 | 维度 | 编码 |
|---|---:|---|
| 自身状态 | 6 | `hp/5`、`ammo/3`、`recharge_progress/2`、`x/49`、`y/49`、`tick/2000` |
| 上一动作 | 9 | one-hot |
| 上一动作结果 | 10 | one-hot |
| 声音 | 18 | 8 个方向 + SELF 的存在位和归一化最近距离 |
| 人格 | 3 | one-hot |
| 合计 | 46 | |

上一动作结果的 10 类固定为：

```text
NONE
MOVED
BLOCKED_WALL
BLOCKED_ENTITY
BLOCKED_CONFLICT
BLOCKED_BOUNDS
SHOT
NO_AMMO
WAITED
INVALID_FALLBACK
```

声音距离不存在时置 0，同时对应存在位置 0；不能只用距离 0 表示“没声音”，因为 `SELF` 声音的距离也为 0。

46 维标量索引固定为：自身状态 `[0,6)`、上一动作 `[6,15)`、上一动作结果 `[15,25)`、声音存在位 `[25,34)`、声音距离 `[34,43)`、人格 `[43,46)`。声音桶顺序固定为 `N, NE, E, SE, S, SW, W, NW, SELF`，距离除以听觉半径 `3`。当前规则只报告最近一次合法声音，因此每个 observation 至多激活一个声音桶；18 维布局为未来不改变模型 shape 的多桶扩展保留稳定合同。

### 4.3 合法动作掩码

动作顺序必须全系统统一：

```text
0 MOVE_UP
1 MOVE_DOWN
2 MOVE_LEFT
3 MOVE_RIGHT
4 SHOOT_UP
5 SHOOT_DOWN
6 SHOOT_LEFT
7 SHOOT_RIGHT
8 WAIT
```

mask 为 `[9]` 布尔向量：

- 墙和边界方向的移动为 0；
- 弹药为 0 时四个射击为 0；
- 死亡角色不再调用 policy；
- `WAIT` 对存活角色必须始终为 1；
- 实体冲突依赖其他角色同时动作，不能提前完全判断，因此相邻实体方向可以保留，由环境结算。

无效 logits 必须在构造 Categorical 分布前设为负无穷等价值。不得先采样再重抽，否则行为概率与 PPO log-prob 不一致。

## 5. 计划神经网络

### 5.1 总体结构

```text
13×5×5 spatial observation
  → Conv 13→64, 3×3, padding=1
  → GroupNorm(8), SiLU
  → Residual block: [Conv 64→64, GroupNorm, SiLU] × 2
  → Flatten(64×5×5=1600)
  → Linear 1600→256, SiLU
                                      ┐
46-d scalar observation              │
  → Linear 46→128, SiLU              ├→ Concat(256+128=384)
  → Linear 128→128, SiLU             │
                                      ┘
  → LayerNorm(384)
  → Linear 384→256, SiLU
  → GRU(input=256, hidden=256, 1 layer)
      ├→ Actor: Linear 256→9 → action mask → Categorical
      └→ Critic: Linear 256→1
```

预计参数量约 100 万，具体值必须由实现测试打印并写入 checkpoint metadata。该规模足以处理 5×5 局部观察，同时便于在 CPU 上部署。

### 5.2 设计约束

- 卷积层不得使用 BatchNorm；on-policy 小批次和非独立样本会让其统计不稳定。使用 GroupNorm。
- 激活函数使用 SiLU。
- GRU hidden size 为 256，不能在三个人格之间共享 hidden state。
- actor 和 critic 共享视觉、标量和 GRU 主干，但使用独立输出头。
- actor 最后一层使用正交初始化，gain `0.01`；critic gain `1.0`；其他线性/卷积层 gain `√2`。
- critic 输出原始标量，不使用激活。
- actor 输出 logits，不在模型内部先做 softmax。
- 所有 observation shape、dtype 和范围必须在进入模型前断言。
- episode 结束、AI 死亡或环境重置时，对应 GRU hidden state 必须清零。

### 5.3 推理方式

在线游戏默认使用带温度的随机策略：

```text
probs = softmax(masked_logits / temperature)
```

默认 `temperature = 0.8`。排位评估同时报告：

- stochastic：按概率采样；
- deterministic：选择合法动作中最大 logit。

不得用 epsilon-greedy 叠加在已训练 PPO policy 上。探索由训练期 entropy bonus 和策略分布完成。

## 6. 奖励设计原则

### 6.1 总公式

第 `i` 个 AI 在 tick `t` 的原始奖励为：

```text
rᵢ,t = r_terminal
     + r_player_combat
     + r_self_damage
     + r_friendly_fire
     + r_ammo
     + r_exploration
     + r_potential
     + r_efficiency
```

每个 component 必须单独记录，训练日志不能只保存总 reward。

### 6.2 共同终局奖励

三个人格共享以下终局目标：

| 事件 | 奖励 | 说明 |
|---|---:|---|
| 玩家死亡 | `+20` | 对当时仍存活的每个 AI 独立发放 |
| 玩家逃脱 | `-20` | 对当时仍存活的每个 AI 独立发放 |
| 游戏超时 | `+10` | 玩家未逃脱，低于真正击杀的收益 |
| 自己造成玩家最后 1 点伤害 | 见人格表 | 个人击杀贡献奖励 |
| 自己死亡 | 见人格表 | 立即发放；死亡后不再产生 transition |

共同终局奖励表示所有敌对 AI 都以阻止玩家逃脱为主目标，但它们不共享 hidden state、局部 shaping reward 或 credit assignment，因此不构成可通信联盟。

### 6.3 不给予奖励的事件

以下事件 reward 必须为 0：

- 单纯存活一个 tick；
- 弹药自动恢复；
- 原地等待；
- 听到声音；
- 仅仅看到玩家；
- 子弹飞行中不追加命中奖励；射击时的弹药成本仍按人格表计算；
- 队友/其他 AI 的正常移动。

这样避免露营刷生存分、空仓刷弹药恢复和视觉事件刷分。

## 7. 人格奖励表

以下数值是 v1 初始值。共同终局奖励不随人格改变，其余 component 按表直接使用：

| 奖励事件 | aggressive | cautious | explorer |
|---|---:|---:|---:|
| 对玩家造成 1 HP 伤害 | `+2.00` | `+1.00` | `+0.50` |
| 亲自击杀玩家额外奖励 | `+8.00` | `+5.00` | `+3.00` |
| 自己损失 1 HP | `-0.75` | `-1.50` | `-1.00` |
| 自己死亡 | `-8.00` | `-15.00` | `-10.00` |
| 每次实际射击的弹药成本 | `-0.01` | `-0.05` | `-0.03` |
| 首次进入新格 | `+0.002` | `+0.005` | `+0.015` |
| 成功移动到已访问格 | `-0.002` | `-0.002` | `-0.008` |
| 每个非终局 tick | `-0.002` | `-0.0005` | `-0.0015` |
| 接近玩家的 potential 系数 `β` | `0.10` | `0.02` | `0.00` |

所有人格共同使用：

| 事件 | 奖励 |
|---|---:|
| 对其他 AI 造成 1 HP 误伤 | `-1.00` |
| 击杀其他 AI 的额外惩罚 | `-3.00` |
| 撞墙/越界动作 | `-0.02` |
| 实体占位或同格冲突导致移动失败 | `-0.005` |
| 产生 `INVALID_FALLBACK` | `-0.10` |

探索正奖励每局每个 AI 上限为 `+5.0`。达到上限后，新格 reward 为 0，但仍记录覆盖率。该上限防止 explorer 仅靠地图覆盖获得高于终局目标的回报。

## 8. Reward 的精确定义

### 8.1 伤害与击杀

- 伤害和击杀奖励只从结构化 `DAMAGE_APPLIED`、`DAMAGE_CREDIT` 和 `ENTITY_DIED` 事件计算，不能从 HP 差值或事件顺序反推射手。
- 每个受伤目标每 tick 产生一个 `DAMAGE_APPLIED`，其 `value` 是 HP cap 后的实际总伤害；事件 `actor` 和 `target` 都是受伤目标。
- 同 tick 每个命中该目标的唯一射手产生一个 `DAMAGE_CREDIT`，`actor` 是射手，`target` 是受伤目标，`value` 是该射手的命中弹数。
- 伤害 reward 按 `DAMAGE_APPLIED.value × shooter_hits / all_hits` 分配，因此所有射手 credit 之和严格等于实际伤害。若发生致死，个人击杀奖励在拥有 `DAMAGE_CREDIT` 的唯一射手之间等分，不按弹数重复计算。
- 伤害按实际扣除 HP 计算；对剩余 1 HP 的目标同时命中 3 发，只能累计 1 HP 的有效伤害奖励。
- 对玩家最后一击同时获得“伤害奖励”和“亲自击杀额外奖励”。
- 多个 AI 同 tick 命中并击杀玩家时，最后一击奖励按造成有效致死伤害的射手均分；共同终局奖励照常发放。
- AI 自伤在 v1 物理规则中不可能发生；若出现必须作为引擎缺陷，而不是奖励事件。

### 8.2 射击成本与延迟命中

- 每次实际消耗弹药并生成子弹时，立即发放人格表中的小额弹药成本；无弹药动作不重复收取该成本。
- 子弹之后实际造成伤害时，再向仍存活的射手发放伤害 reward。
- 子弹没有命中时不再追加第二次“射失”惩罚，避免同一射击被重复扣分。
- 射手死亡后，其历史子弹仍按物理规则继续飞行和造成伤害，但不再向已经终止的该 AI 轨迹回写 reward。
- 结构化事件仍必须保留原射手 ID，以便评估命中率和调试，但 on-policy rollout 一旦关闭不得事后修改。

### 8.3 探索与重访

- 只有成功移动才计算探索 reward。
- 目标位置不在该 AI 本局 `visited` 集合时为首次进入。
- 出生格不产生首次进入 reward。
- 移动失败、等待和射击不算重访。
- `visited` 不跨局保留。

### 8.4 Potential-based shaping

只对 aggressive 和 cautious 使用接近玩家的 potential：

```text
Φ(s) = -clip(shortest_path_distance(ai, player) / 100, 0, 1)
r_potential = β × (γ Φ(s') - Φ(s))
```

- 距离由完整世界状态计算，只用于 reward，不进入 observation。
- 若任一实体死亡或两者不连通，本 tick potential reward 为 0。
- 使用与 PPO 相同的 `γ`，保持 potential-based shaping 的一致性。
- explorer 的 `β = 0`，避免追逐奖励覆盖其探索人格。

### 8.5 Reward 范围和归一化

- 环境输出原始 reward，不做 clipping。
- 训练器对 advantage 做每 minibatch 标准化。
- value target 可以使用共享的 running return normalization，但 checkpoint 必须保存统计量。
- 日志同时记录 raw reward、normalized value target 和各 component。
- 任意单 tick 的绝对 reward 超过 50 时必须告警；超过 100 时中止训练并检查事件重复结算。

## 9. PPO 目标与超参数

使用 clipped PPO：

```text
L_policy = -E[min(ρₜ Aₜ, clip(ρₜ, 1-ε, 1+ε) Aₜ)]
L_value  = 0.5 × value_loss
L_entropy = -c_ent × entropy
L_total = L_policy + c_vf L_value + L_entropy
```

v1 默认超参数：

| 参数 | 值 |
|---|---:|
| `gamma` | `0.995` |
| `gae_lambda` | `0.95` |
| `clip_coef` | `0.20` |
| `value_clip_coef` | `0.20` |
| `learning_rate` | `3e-4` 线性衰减到 `3e-5` |
| `optimizer` | AdamW |
| `adam_eps` | `1e-5` |
| `weight_decay` | `1e-4` |
| `update_epochs` | `4` |
| `entropy_coef` | `0.020` 衰减到 `0.005` |
| `value_loss_coef` | `0.5` |
| `max_grad_norm` | `0.5` |
| `target_kl` | `0.02` |
| `gru_sequence_length` | `64` |
| `burn_in` | `0`，on-policy hidden 从 rollout 保存 |

若一次 update 的 `approx_kl > 0.03`，必须提前停止本次剩余 epoch。连续 10 次 update 超限时降低学习率并触发训练告警。

## 10. 玩家对手与课程学习

训练 AI 时不能依赖真人持续输入。训练器维护玩家策略池：

1. **stationary**：只等待，用于学习移动、射击和动作掩码；
2. **random-valid**：随机合法移动/射击；
3. **wall-follower**：使用局部规则探索出口；
4. **shortest-path noisy**：拥有路径规划，但以固定概率走次优动作；
5. **combat planner**：会躲避可见子弹并在直线上射击；
6. **frozen player-policy pool**：未来训练出的玩家策略快照。

课程阶段按智能体步计：

| 阶段 | 智能体步 | 对手采样 | 目标 |
|---|---:|---|---|
| A | 0～5M | stationary 70%，random 30% | 学会合法行动、靠近和命中 |
| B | 5M～20M | random 40%，wall-follower 60% | 学会搜索移动目标 |
| C | 20M～50M | wall-follower 30%，shortest-path 50%，combat 20% | 学会拦截、避弹和资源管理 |
| D | 50M～100M | 全策略池动态采样 | 提高泛化和抗策略过拟合 |

课程晋级同时受步数和评估门槛控制。若当前阶段胜率、稳定性或人格差异未达标，不得仅因步数达到就晋级。

v1 晋级门槛固定如下；每项使用未参与训练的固定 seed、stochastic 策略和每个列出对手至少 300 局：

| 晋级 | 最低步数 | 固定评估门槛 |
|---|---:|---|
| A → B | `5M` | stationary 玩家死亡率 ≥ `25%`；random-valid 玩家逃脱率 ≤ `10%` |
| B → C | `20M` | wall-follower 玩家逃脱率 ≤ `30%` 且玩家死亡率 ≥ `10%` |
| C → D | `50M` | shortest-path noisy 和 combat planner 各自玩家逃脱率 ≤ `80%`；aggressive 射击率不低于 cautious；cautious 死亡率不高于 aggressive；explorer 首次访问率不低于 aggressive |

所有晋级还要求最近区间无 NaN/Inf、非法动作、环境不变量失败、checkpoint 恢复失败或连续 KL 超限。未达门槛时继续当前阶段并保留评估报告，不允许降低门槛或仅按步数强制晋级。D 阶段不再自动晋级；它进入最终多 seed 发布验收。

训练出生点必须随机化。固定地图训练时必须覆盖出口附近、远离出口、狭窄走廊和开放区域；不能让网络只记住少量出生坐标。

## 11. 单张 16GB GPU 的训练配置

### 11.1 建议硬件

- 1 张 16GB NVIDIA GPU；
- 8 个以上 CPU 物理核心，推荐 16 核；
- 32GB 以上系统内存；
- 20GB 以上可用磁盘空间；
- Linux 作为正式训练环境；
- 支持当前 PyTorch 的 NVIDIA 驱动和 CUDA runtime。
- V100 正式环境固定为 PyTorch `2.6.0` 与 CUDA `12.4` 用户态依赖，并通过清华 PyPI 镜像安装；不得在 V100 上安装 CUDA 13 build。

这个模型只有约 100 万参数，16GB 显存的主要压力不是参数，而是 recurrent PPO 的序列激活和 minibatch。环境模拟通常是 CPU 瓶颈。

### 11.2 平衡配置

计划配置文件 `configs/rl/ppo_16gb.yaml` 应包含等价参数：

```yaml
seed: 20261113
device: cuda
total_agent_steps: 100_000_000

environment:
  num_envs: 64
  max_episode_ticks: 2000
  players_per_env: 1
  agents_per_env: 3
  deterministic_rules: true

rollout:
  environment_steps: 128
  sequence_length: 64
  store_spatial_as_uint8: true
  storage_device: cpu_pinned

minibatch:
  sequences: 32
  update_epochs: 4

model:
  spatial_channels: 13
  scalar_features: 46
  conv_channels: 64
  visual_embedding: 256
  scalar_embedding: 128
  gru_hidden: 256
  action_count: 9

ppo:
  gamma: 0.995
  gae_lambda: 0.95
  clip_coef: 0.20
  value_clip_coef: 0.20
  learning_rate: 0.0003
  final_learning_rate: 0.00003
  entropy_coef: 0.020
  final_entropy_coef: 0.005
  value_loss_coef: 0.5
  max_grad_norm: 0.5
  target_kl: 0.02
  normalize_advantage: true

precision:
  mode: fp32
  allow_tf32: true

checkpoint:
  every_agent_steps: 1_000_000
  keep_latest: 3
  keep_best: 5

evaluation:
  every_agent_steps: 500_000
  episodes_per_persona_per_opponent: 300
```

每次 rollout 理论上最多产生：

```text
64 env × 128 tick × 3 AI = 24,576 agent transitions
```

以 64 长度切分后约为 384 条序列。每 minibatch 使用 32 条序列，即最多 2,048 个 transition；这个配置对 16GB 显存有较大安全余量。

### 11.3 精度策略

首个正确性基线必须使用 FP32：

- observation encoder、GRU、log-prob、value 和 loss 均为 FP32；
- 可以启用 TF32 加速支持的矩阵运算；
- 不得在正确性基线前直接启用 FP16。

若 GPU 支持 BF16，可在基线一致后测试 BF16 autocast，但以下部分仍应保持 FP32：

- masked logits 和 Categorical log-prob；
- advantage normalization；
- value target；
- PPO ratio 与 loss 累加；
- gradient norm。

只有当固定 seed 短跑的回报、KL、entropy 和动作分布与 FP32 基线无系统性偏差时，才允许把 BF16 作为默认配置。

### 11.4 显存预算

实现必须在训练启动时打印：

- 参数量；
- optimizer state 预计大小；
- rollout buffer 大小；
- 单 minibatch tensor shape；
- `torch.cuda.max_memory_allocated()`；
- `torch.cuda.max_memory_reserved()`。

16GB 卡的发布配置要求峰值 allocated 小于 14GB，预留至少 2GB 给 CUDA runtime、碎片和评估批次。按当前小模型，正常峰值应显著低于该上限；若接近 14GB，通常表示 rollout 被错误地完整展开到 GPU 或保留了计算图。

### 11.5 OOM 调整顺序

发生 OOM 时按以下顺序调整，每次只改一项并记录：

1. `minibatch.sequences: 32 → 16 → 8`；
2. 确认 rollout 存在 CPU pinned memory，且旧 minibatch graph 已释放；
3. `num_envs: 64 → 32`；
4. `rollout.environment_steps: 128 → 64`；
5. 最后才把 `gru_hidden: 256 → 192`。

不得通过关闭 action mask、缩短 observation 或删掉 critic 来解决 OOM。sequence length 不应低于 32，否则迷宫记忆能力会明显受损。

### 11.6 四张 V100 的执行拓扑

四张 V100 不改变单次训练的 PPO batch 语义。工程顺序固定为：

1. CPU 正确性与 100k agent-step smoke；
2. 单张 V100 的 FP32 数值、吞吐、显存和断点恢复基线；
3. 单张 V100 连续两小时稳定性；
4. 四张 V100 各运行一个隔离的训练 seed；
5. 任一 GPU 空闲后运行第五个发布所需 seed。

每个进程只绑定一张 GPU，并使用独立 run 目录、端口空间、checkpoint lineage 和 RNG 状态。首版不使用同步 DDP；只有端到端 profiling 证明 DDP 能提高 agent transitions/s，且不会改变 rollout、KL、课程或复现语义时，才允许通过新 ADR 引入。

## 12. 16GB GPU 训练操作方法

以下命令定义计划中的训练 CLI 合同；代码实现时应保持接口稳定。

### 12.1 环境检查

```bash
nvidia-smi
python --version
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

训练启动前必须确认：

- CUDA 可用；
- 目标 GPU 有约 16GB 总显存；
- 没有未知进程占用大部分显存；
- 项目测试通过；
- 当前 git commit、规则版本和配置文件已记录。

### 12.2 安装训练依赖

计划项目应提供 train extra：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[train]'
```

`[train]` 至少应包含 PyTorch、NumPy、Gymnasium/PettingZoo 兼容接口、配置解析、TensorBoard、测试与静态检查依赖。正式项目必须锁定依赖版本和 CUDA 构建，不应让生产训练临时解析浮动最新版。

### 12.3 训练前正确性检查

```bash
pytest -q
python -m training.validate_env --episodes 1000 --seeds 1:1000
python -m training.validate_reward --golden-trajectories tests/fixtures/reward
python -m training.benchmark_env --num-envs 64 --ticks 10000
python -m training.smoke --config configs/rl/ppo_16gb.yaml --agent-steps 100000
```

smoke run 必须满足：

- 无 NaN/Inf；
- 无非法动作被采样；
- GRU state 在 done 后清零；
- reward component 之和等于总 reward；
- checkpoint 可保存、加载并继续；
- 固定 seed 的评估轨迹可复现；
- 峰值显存低于 14GB。

### 12.4 正式训练

```bash
CUDA_VISIBLE_DEVICES=0 python -m training.train_ppo \
  --config configs/rl/ppo_16gb.yaml \
  --run-name catamaze-rppo-v1-seed20261113
```

训练日志必须写入独立 run 目录，例如：

```text
runs/catamaze-rppo-v1-seed20261113/
├── resolved_config.yaml
├── metadata.json
├── metrics.jsonl
├── tensorboard/
├── checkpoints/
├── evaluations/
└── artifacts/
```

`metadata.json` 至少保存：git commit、环境版本、reward 版本、模型版本、seed、GPU 型号、CUDA/PyTorch 版本、开始时间和命令行。

### 12.5 断点恢复

```bash
CUDA_VISIBLE_DEVICES=0 python -m training.train_ppo \
  --config runs/catamaze-rppo-v1-seed20261113/resolved_config.yaml \
  --resume runs/catamaze-rppo-v1-seed20261113/checkpoints/latest.pt
```

checkpoint 必须包含：

- model parameters；
- optimizer state；
- learning-rate/entropy scheduler；
- global environment/agent step；
- curriculum stage 和 opponent sampler；
- return normalization statistics；
- Python、NumPy、PyTorch CPU/CUDA RNG state；
- 最佳评估指标；
- 配置和版本 metadata。

恢复后不得把学习率、entropy 或课程阶段重置到开头。

### 12.6 训练时间估算

训练时间取决于 CPU 环境吞吐，而不是只取决于 16GB GPU。必须先运行 benchmark，并用实测 agent transitions/s 估算：

```text
预计纯采样时间（秒） = 100,000,000 / agent_transitions_per_second
```

再额外预留 PPO 更新、评估和 checkpoint 时间。示例：

| 实测吞吐 | 100M 步纯采样时间 |
|---:|---:|
| 1,000 agent steps/s | 约 27.8 小时 |
| 2,500 agent steps/s | 约 11.1 小时 |
| 5,000 agent steps/s | 约 5.6 小时 |
| 10,000 agent steps/s | 约 2.8 小时 |

这些是算术估算，不是性能承诺。正式排期应使用目标机器连续 30 分钟 benchmark 的 p50 吞吐，并增加至少 30% 余量。

## 13. 训练监控

每次 update 至少记录：

### 优化指标

- policy loss；
- value loss；
- entropy；
- approx KL；
- clip fraction；
- explained variance；
- gradient norm；
- learning rate；
- samples/s 和 updates/s；
- GPU allocated/reserved memory；
- CPU 环境吞吐。

### 游戏指标

- 玩家死亡率、逃脱率、超时率；
- episode tick p50/p90/p99；
- 每个人格 episode return；
- 每个人格存活率；
- 对玩家命中率和射击次数；
- AI 误伤率；
- 首次访问格数和重访率；
- 撞墙、冲突和 `INVALID_FALLBACK` 率；
- 弹药为空比例；
- 各动作选择频率；
- 各 reward component 总量。

必须分人格、分对手策略、分课程阶段统计，不能只看全局平均。

## 14. 异常检测与停止条件

出现以下任一情况必须自动停止并保留故障 checkpoint：

- loss、logit、value、reward、advantage 或 gradient 出现 NaN/Inf；
- 非法动作被 policy 采样；
- reward component 与总 reward 不一致；
- 单 tick 绝对 reward 超过 100；
- 连续 10 次 update `approx_kl > 0.03`；
- gradient norm 在裁剪前连续 100 次超过 100；
- 所有人格 entropy 快速降到 0 且评估未改善；
- `INVALID_FALLBACK` 率超过 `0.01%`；
- 固定 seed 评估无法重放；
- allocated 显存超过 14GB 或发生 OOM；
- 环境不变量失败。

训练进程不得尝试重启或关机训练服务器。驱动、CUDA 或硬件故障应保存可用诊断后退出，由运维人员处理。

## 15. 评估协议

### 15.1 固定评估集

评估必须使用训练未消费的固定 seed 集，并覆盖：

- 每种人格；
- 每个玩家对手类型；
- 不同出生距离；
- 走廊、交叉口、出口附近和开放区域；
- 有/无其他 AI 存活的局面；
- 低 HP、低弹药和飞行子弹压力场景。

每次正式评估至少执行每人格、每对手 300 局，同时报告 95% 置信区间。最终候选模型应提高到 1,000 局。

### 15.2 比较基线

至少比较：

1. random-valid；
2. 当前人格启发式策略；
3. 去掉 GRU 的同规模 feed-forward 模型；
4. 去掉 persona 输入的共享模型；
5. 上一个生产模型；
6. 当前候选模型。

### 15.3 人格差异验收

在控制相同 seed 和对手后，候选模型必须满足：

- aggressive 每 100 tick 的射击和有效命中数至少比三人格均值高 20%；
- cautious 死亡率至少比 aggressive 低 15% 相对值，且无弹药射击率不高于 `0.1%`；
- explorer 每 100 tick 首次访问格数至少比三人格均值高 20%，重访率显著低于 aggressive；
- 三个人格的动作分布 Jensen-Shannon divergence 不得全部低于 `0.02`，避免人格条件被网络忽略；
- 任一人格的玩家逃脱阻止率不得比启发式同人格基线低超过 5 个百分点。

若这些目标与共同终局目标冲突，优先保证玩家逃脱阻止能力，再调整 shaping 系数，而不是改变物理规则。

## 16. 产品发布门槛

模型只有同时满足以下条件才能进入生产：

### 正确性

- 所有规则、reward golden trajectory 和 action-mask 测试通过；
- 10,000 局评估无非法动作、NaN、状态泄漏或不变量错误；
- 保存/恢复前后动作分布在相同输入和 hidden state 下完全一致；
- checkpoint metadata 完整。

### 效果

- 相比启发式基线，固定评估集上的玩家逃脱率至少下降 20% 相对值；
- 不以超时替代真实对抗：玩家死亡率必须提升，不能只有 TIMEOUT 增长；
- AI 误伤率不高于总命中数的 5%；
- 人格差异验收全部通过；
- 至少 5 个训练 seed 中有 4 个达到门槛，并报告均值与标准差。

### 性能

- 生产 CPU 上单 observation 推理 p95 小于 5ms；
- 同一游戏三个 AI 批量推理 p95 小于 10ms；
- 常驻模型内存小于 100MB；
- 16GB GPU 训练配置连续运行 2 小时无 OOM、内存持续增长或吞吐崩溃。

### 回滚

- 保留上一生产模型；
- 模型和环境版本可独立选择；
- 在线异常率、延迟或玩家反馈越过阈值时可以无数据迁移地回滚；
- 回滚不得改变已保存游戏的规则版本。

## 17. 导出与 Native 推理

发布产物至少包含：

```text
model.pt
model_metadata.json
observation_schema.json
action_schema.json
reward_version.txt
environment_version.txt
evaluation_report.json
```

Native 模型策略必须：

- 按游戏和实体保存 256 维 GRU hidden state；
- 游戏恢复时从保存的 hidden state 恢复，或明确重建并记录行为不连续；
- 对三个 AI 做一次批量前向；
- 在模型外统一应用 action mask；
- 设置严格推理超时；
- 模型异常时回退到 `WAIT` 或经过验证的启发式策略；
- 记录模型版本、采样温度、动作概率摘要和最终动作；
- 不在游戏推理中进行梯度更新。

本阶段的 TorchScript/ONNX 导出只面向 Native。独立 ESP32 产品不得依赖网络推理，并继续使用经过验证的启发式策略。任何 ESP32 神经网络部署都必须由后续 ADR 单独定义模型格式、量化、运行时、内存、延迟和物理设备验收；本文件不宣称当前 PyTorch 架构可直接部署到 ESP32。

模型可以导出为 TorchScript 或 ONNX，但导出版本必须通过与原 PyTorch 模型的 logits/value 数值对齐测试。最大容许误差：FP32 `1e-5`，BF16 导出 `1e-2`。

## 18. 奖励和模型测试

### 18.1 Reward 单元测试

至少包含：

- 每种人格对玩家造成 1 点伤害；
- 最后一击伤害加击杀奖励；
- 多 AI 同 tick 致死时均分个人击杀奖励；
- 有效伤害不超过目标剩余 HP；
- AI 误伤和误杀；
- 自己受伤和死亡；
- 射击成本、存活时的延迟命中与死后子弹不回写 reward；
- 新格、重访和探索上限；
- potential shaping 的正负方向；
- 玩家死亡、逃脱和超时；
- 死亡 AI 不继续获得 transition；
- component 和等于 total。

### 18.2 网络测试

- spatial `[B,T,13,5,5]` 与 scalar `[B,T,46]` shape；
- 不同 batch/sequence 长度；
- hidden reset mask；
- 全部非法但 WAIT 合法；
- masked action 概率严格为 0；
- 保存/加载 logits 一致；
- CPU/GPU 前向对齐；
- deterministic/stochastic 模式；
- persona one-hot 改变输出梯度；
- 极端合法 observation 不产生 NaN。

### 18.3 集成测试

- 1,000 局随机 rollout 无环境不变量失败；
- PPO smoke update 后参数确实变化；
- rollout 中 old log-prob 与动作对应；
- truncated episode 正确 bootstrap，terminated episode 不 bootstrap；
- dead agent mask 不污染其他序列；
- checkpoint 中断/恢复后的下一 update 与不中断基线一致；
- 16GB 配置显存和吞吐记录完整。

## 19. 计划代码结构

实现阶段应先为每个新增目录创建符合仓库约束的 `README.md`，再落代码。建议结构：

```text
training/
├── README.md
├── env.py                 # 纯内存多智能体环境适配器
├── observation.py         # 13×5×5 + 46 维编码
├── action_mask.py         # 唯一合法动作掩码实现
├── reward.py              # 结构化事件到 reward components
├── model.py               # CNN + MLP + GRU actor-critic
├── rollout.py             # recurrent rollout storage
├── ppo.py                 # GAE 与 PPO update
├── opponents.py           # 玩家策略池
├── curriculum.py          # 课程调度
├── evaluator.py           # 固定 seed 评估
├── checkpoint.py          # 完整状态保存/恢复
├── train_ppo.py           # 正式训练入口
├── validate_env.py        # 环境不变量长跑
├── validate_reward.py     # reward golden trajectory
├── benchmark_env.py       # CPU/环境吞吐基准
└── smoke.py               # 训练烟雾测试

configs/
├── README.md
└── rl/
    ├── README.md
    └── ppo_16gb.yaml

tests/
├── README.md
├── training/
│   ├── README.md
│   ├── test_observation.py
│   ├── test_action_mask.py
│   ├── test_reward.py
│   ├── test_model.py
│   ├── test_rollout.py
│   └── test_checkpoint.py
└── fixtures/
    └── reward/
```

action mask、observation schema 和 reward 事件枚举必须各有唯一实现来源，不能在环境、模型和在线服务中复制三套略有差异的逻辑。

## 20. 版本管理

以下任一变化都必须提升相应版本：

- 物理、观察、动作或终局变化：`environment_version`；
- reward 数值、事件或计算顺序变化：`reward_version`；
- 网络 shape、层结构或 hidden state 变化：`model_arch_version`；
- 训练超参数、课程或对手池变化：`training_config_version`。

checkpoint 必须绑定四个版本。环境或 observation 不兼容时不得强行加载旧模型。reward 改变通常要求从头训练或至少从明确记录的预训练 checkpoint 重新优化，并重新通过全部发布门槛。

## 21. 实施顺序

严格按以下顺序交付：

1. 完成并冻结 `gamerules.md` 对应的确定性环境；
2. 建立结构化事件和黄金轨迹；
3. 实现 observation encoder 与唯一 action mask；
4. 实现并单测 reward components；
5. 实现约 100 万参数的 CNN + MLP + GRU actor-critic；
6. 实现 recurrent rollout、GAE 和 PPO；
7. 完成 100k agent-step smoke run；
8. 完成固定 seed 可复现性和 checkpoint 恢复测试；
9. 在 16GB GPU 上运行 2 小时稳定性测试；
10. 执行 100M agent-step 多 seed 正式训练；
11. 完成人格、基线、性能和回滚验收；
12. 版本化导出并灰度发布。

在第 1～8 步未通过之前，不应启动长时间 GPU 训练。产品级 RL 的首要条件是环境和 reward 正确；更长训练不能修复错误规则、信息泄漏或重复奖励。
