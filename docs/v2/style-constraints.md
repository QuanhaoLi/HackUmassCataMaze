<!--
Created at: 2026-11-14 20:40 EST
Created by: Codex
Last Modified at: 2026-11-14 22:12 EST
Last Modified by: Codex
-->

# V2 bounded style constraints

## Inputs and privacy

The loss receives only tensors already supplied to one policy call:

- local `spatial[13,5,5]`;
- local `scalar[46]`;
- the current legal action mask;
- the three actor-head logits produced from that local recurrent state;
- the active-transition mask.

No global terrain, hidden player coordinate, teammate hidden state, future result or privileged simulator feature is permitted.

## Components

### Aggressive aligned-shot target

Player visibility is read from legal player channel5. If the player lies on the center row or column, the corresponding directional shot is legal, and the transition is active, aggressive head cross-entropy targets `SHOOT_UP/DOWN/LEFT/RIGHT`. Diagonal or invisible players produce no target.

### Cautious low-HP retreat target

Only when normalized HP is at most `0.60`, a visible cardinal player produces the opposite movement target. When no cardinal player is visible, a legal heard-sound direction may produce the opposite movement target. When neither cue exists, the legal Wait Action is the target. It never invents a route from hidden map state.

### Explorer recurrent first-visit target

Within an explorer recurrent training sequence, compare the normalized private position at `t+1` with that sequence's positions through `t`. If a legal movement action reached a position not previously present in the sequence, explorer cross-entropy reinforces the action at `t`. Blocked moves and revisits receive no auxiliary target. This is private trajectory memory already available to the recurrent policy; it does not read the full map or another entity's state.

If an explorer movement leads to a position already present earlier in the sequence, apply bounded complement loss `-log(1 - p(chosen_move)) / log(9)`. This discourages the observed revisit action without inventing an unobserved alternative.

### Cautious damage-avoidance target

For cautious sequences, if normalized HP at `t+1` is below HP at `t`, apply the same bounded complement loss to the chosen action at `t`. The signal uses only the cautious AI's own next private HP and does not attribute unseen shooters or future outcomes.

### Category margins

Across active observations:

- aggressive shoot probability must exceed cautious by `0.15`;
- aggressive shoot probability must exceed explorer by `0.15`;
- explorer move probability must exceed aggressive by `0.15`;
- explorer move probability must exceed cautious by `0.10`.

Each is a hinge; exceeding a margin adds no further incentive. Every hinge is divided by its own target margin before aggregation, making a fully missed constraint equal to `1`.

### Pairwise distribution floor

For each head pair, Jensen–Shannon divergence over the same legal action set uses normalized training hinge `max(0, 0.05 - JS) / 0.05`. The production acceptance gate remains `0.02`; the larger training target provides distribution-shift margin rather than weakening release criteria. Exceeding `0.05` adds no incentive.

## Total loss

```text
L_style = mean(10 * valid aggressive CE / log(9),
               3 * valid cautious CE / log(9),
               valid explorer recurrent first-visit CE / log(4),
               5 * cautious damage-avoidance,
               5 * explorer revisit-avoidance,
               category hinges,
               pairwise JS hinges)

L_total = L_PPO + value_coef * L_value - entropy_coef * H
          + 0.02 * L_style
```

Empty tactical subsets contribute zero, never NaN. All components and valid sample counts are logged. DDP averages the loss across ranks. The first raw-scale5M trial is retained as failed evidence because it reached only action JS `0.0185` and explorer first-visit uplift around12%; the normalized trial starts from that checkpoint with a fresh optimizer.

The first persona-neutral5M trial used a training target equal to the release gate (`0.02`). Its training-batch hinges converged, but independent Stage-D counterfactual JS remained `0.0085–0.0159`. The safety-margin trial starts from checkpoint `e6a521a10b54f44a9f3e7ad55dbbeaebabe0db564725050884a4c6f3b022c0ad`, changes only the training JS target to `0.05`, and keeps the release threshold at `0.02`.

The safety-margin trial passed JS and aggressive shooting but failed explorer novelty, cautious survival, hit rate and effectiveness. Local fog frontier is therefore rejected as a proxy for novel global position. The recurrent-target trial starts from safety-margin checkpoint `3faccbc0a29c00f51cabe14b18e47187a4d919b01de8a5a047d2cec51be58a4d`, replaces only frontier supervision and low-HP no-cue behavior, and retains every other coefficient and gate.

The recurrent-target trial passed every divergence and aggressive-shooting gate and moved explorer first visits to17.5% above the mean, but explorer revisit, cautious survival and aggressive hits still failed. The transition-credit trial starts from `7a972f9a97aecd7fa394004e09fbafeb65dce5e322c4c3deb9ab227dc4fe61fd`, adds only the two private next-state complement losses, and gives aligned-shot CE a fixed3× component weight. Reward and overall style coefficient remain unchanged.

The transition-credit trial passed explorer first visits, all divergence, aggressive shooting and combined effectiveness, but the sparse hit/survival/revisit terms remained too weak and shortest-path escape missed its per-opponent bound by3points. The weighted transition trial starts from `6947c4bc4a5bade4c92ba5d389e5de1211409d6894fa95e7ee177fabfbc3fef1` and changes only component multipliers shown above. Overall coefficient remains `0.02`.

## Controlled run

- source: reward-v3 heads-only5M checkpoint;
- trainable: persona gamma/beta and three actor/critic heads only;
- frozen: visual encoder, scalar encoder, fusion and GRU;
- curriculum: C;
- reward: `catamaze.reward.persona.v3` unchanged;
- learning rate: `3e-5`;
- first gate:5M steps;
- no extension unless persona and effectiveness metrics both improve.
