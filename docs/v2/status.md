<!--
Created at: 2026-11-14 19:41 EST
Created by: Codex
Last Modified at: 2026-11-14 19:41 EST
Last Modified by: Codex
-->

# V2 Persona Policy status

## Isolation

- V1 freeze commit: `619ba18`.
- V1 FP32 checkpoint: 100,364,306 agent steps, SHA-256 `afdf4534fe03db5da010286a57a6f285a961a64ed9400d8a0cf4e460d4e23ca8`.
- V1 final evaluation SHA-256: `adff6e77d94fa58abed330b98b854f8be54f3401c46008632c6014cea0484284`.
- V2 warm-start SHA-256: `4458eb4bd85acc1328d212aa25654eb12451bb298c47221ee02a86361737160c`.
- V2 has not modified, compiled, uploaded, or switched the V1 firmware or physical board.

## Engineering gates passed

- V1→V2 migration errors are exactly zero for selected logits, all three heads, value heads, and recurrent hidden state.
- V2 parameter count: 1,017,502; step-0 gamma/beta are zero.
- Persona-balanced recurrent PPO, checkpoint replay, staged parameter ownership, evaluator, actor-only export, and quantization sampling tests pass.
- Full Python suite passed after V2 isolation work.
- Formal CPU smoke: 100,078 steps, 1,072 updates, 1,369 steps/s, exact checkpoint restore on every update.
- Single V100 qualification: 1,004,178 steps, 4,855 steps/s, maximum KL `0.01985`.
- Four-V100 DDP qualification: 1,046,309 steps, 18,982 steps/s (`3.91×` single-card), maximum KL `0.00954`, approximately 305MB maximum allocated memory per rank.
- Actor-only step-0 ONNX: 4,065,686 bytes, no critic initializers, no unsupported operators, maximum logits error `3.34e-6`, maximum hidden error `5.13e-6`.

## Training evidence

### Heads-only / curriculum A

- 5,056,464 agent steps.
- 17,456 steps/s; maximum KL `0.00954`.
- Checkpoint SHA-256: `eade6a5688ef49e25f65ffdc2688358a5fe2afb1b3118934f2be6e5cf86da33c`.
- The 300-episode stationary/random-valid evaluation failed every complete persona gate. This failure is retained as evidence that independent heads alone are insufficient.

### Recurrent / curriculum B

- 5,056,399 additional agent steps.
- 18,724 steps/s; maximum KL `0.00837`; final explained variance `0.799`.
- Checkpoint SHA-256: `d155f283f73754c9dbb9d7142f8221bde4a6de27dc8b8c1385f63137bf85c597`.
- Wall-follower evaluation passed action divergence, counterfactual divergence, aggressive shooting, cautious survival, and V1 escape-regression gates.
- It still failed aggressive hit-rate and explorer first-visit/revisit gates; therefore it is not a candidate.

### Full model / curriculum C

- In progress from the recurrent checkpoint at learning rate `3e-5`.
- Target: 15M additional steps, producing the first 25M cumulative V2 candidate point.

## Current release status

No V2 release candidate exists yet. The model may be called prepared only after full-stage evaluation, ablations, actor-only export, per-persona 10,000-sample quantization, checksummed handoff bundle, and the explicit stop-before-firmware boundary all pass.
