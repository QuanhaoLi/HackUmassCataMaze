<!--
Created at: 2026-11-14 21:09 EST
Created by: Codex
Last Modified at: 2026-11-14 22:29 EST
Last Modified by: Codex
-->

---
status: accepted
---

# Neutralize persona conditioning in the V2 shared trunk

The normalized style-loss run made its internal same-trunk head hinges converge, but deployment-equivalent counterfactual JS remained below the `0.02` gate. The mismatch is structural: training compared three heads on one persona-conditioned recurrent feature, while deployment changes persona, recomputes the conditioned trunk, and selects the corresponding head. An unused head under one conditioned feature is not the policy produced by another persona.

V2.1 therefore makes the shared trunk persona-neutral and puts all explicit style ownership in the three actor heads. Persona gamma/beta are fixed at zero. The three persona columns of the first scalar layer are replaced by their column mean, so every one-hot persona contributes the same average V1 feature instead of deleting the learned feature entirely. Visual encoder, scalar encoder, fusion and GRU are frozen; only actor and training-only critic heads update.

This makes `logits_all` on one local recurrent feature exactly correspond to all three deployment persona alternatives, so category/JS constraints and counterfactual evaluation measure the same object. Reward remains `catamaze.reward.persona.v3`, coefficient remains `0.02`, legal observation/action contracts remain unchanged, and the controlled run starts from recurrent checkpoint `d155f283f73754c9dbb9d7142f8221bde4a6de27dc8b8c1385f63137bf85c597` with a fresh optimizer. Previous persona-conditioned branches remain immutable failed evidence.

The first neutral-trunk trial showed that a training JS target equal to the release gate does not generalize across seeds. A follow-up starts from checkpoint `e6a521a10b54f44a9f3e7ad55dbbeaebabe0db564725050884a4c6f3b022c0ad` and changes only the bounded training target from `0.02` to `0.05`; the release gate remains unchanged.

The JS-margin follow-up passed divergence but disproved local fog frontier as a novelty proxy. A final controlled run starts from `3faccbc0a29c00f51cabe14b18e47187a4d919b01de8a5a047d2cec51be58a4d`, reinforces only explorer actions whose next private position is new within the recurrent sequence, and gives low-HP cautious samples a Wait target only when no legal visible/sound retreat cue exists.

That run nearly met exploration but exposed remaining transition-level failures. A final transition-credit run starts from `7a972f9a97aecd7fa394004e09fbafeb65dce5e322c4c3deb9ab227dc4fe61fd`, penalizes only the probability of actually chosen explorer revisit and cautious damage-followed actions, and weights aligned-shot CE3×. These use private adjacent sequence state only and do not change inference inputs.

Transition credit passed novelty but sparse components remained underweighted. The weighted follow-up starts from `6947c4bc4a5bade4c92ba5d389e5de1211409d6894fa95e7ee177fabfbc3fef1` and changes only aligned-shot, cautious retreat/damage and explorer-revisit component multipliers to10×/3×/5×/5× inside the already bounded `0.02` style coefficient.

Because weighted transition still inherited hard-opponent regression, the final control resets model lineage to immutable V1-equivalent warm-start `4458eb4bd85acc1328d212aa25654eb12451bb298c47221ee02a86361737160c`, then applies the same neutral-trunk transform and head-only weighted style optimization. This isolates style adaptation from all prior recurrent/full V2 drift.
