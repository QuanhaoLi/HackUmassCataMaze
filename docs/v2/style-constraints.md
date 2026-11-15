<!--
Created at: 2026-11-14 20:40 EST
Created by: Codex
Last Modified at: 2026-11-14 21:03 EST
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

Only when normalized HP is at most `0.60`, a visible cardinal player produces the opposite movement target. When no cardinal player is visible, a legal heard-sound direction may produce the opposite movement target. The term is active only when that move is legal. It never invents a route from hidden map state.

### Explorer local frontier target

For every legal movement, count fog cells in the destination-centered local3×3 window of the existing5×5 observation. Explorer cross-entropy targets the legal move with the largest local fog frontier. This uses no visited-set or full-map privilege; ties follow the frozen action order.

### Category margins

Across active observations:

- aggressive shoot probability must exceed cautious by `0.15`;
- aggressive shoot probability must exceed explorer by `0.15`;
- explorer move probability must exceed aggressive by `0.15`;
- explorer move probability must exceed cautious by `0.10`.

Each is a hinge; exceeding a margin adds no further incentive. Every hinge is divided by its own target margin before aggregation, making a fully missed constraint equal to `1`.

### Pairwise distribution floor

For each head pair, Jensen–Shannon divergence over the same legal action set uses normalized hinge `max(0, 0.02 - JS) / 0.02`. This prevents identical heads but does not reward unbounded divergence.

## Total loss

```text
L_style = mean(valid aggressive CE / log(9),
               valid cautious CE / log(9),
               valid explorer frontier CE / log(4),
               category hinges,
               pairwise JS hinges)

L_total = L_PPO + value_coef * L_value - entropy_coef * H
          + 0.02 * L_style
```

Empty tactical subsets contribute zero, never NaN. All components and valid sample counts are logged. DDP averages the loss across ranks. The first raw-scale5M trial is retained as failed evidence because it reached only action JS `0.0185` and explorer first-visit uplift around12%; the normalized trial starts from that checkpoint with a fresh optimizer.

## Controlled run

- source: reward-v3 heads-only5M checkpoint;
- trainable: persona gamma/beta and three actor/critic heads only;
- frozen: visual encoder, scalar encoder, fusion and GRU;
- curriculum: C;
- reward: `catamaze.reward.persona.v3` unchanged;
- learning rate: `3e-5`;
- first gate:5M steps;
- no extension unless persona and effectiveness metrics both improve.
