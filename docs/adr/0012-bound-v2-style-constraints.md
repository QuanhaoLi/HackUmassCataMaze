<!--
Created at: 2026-11-14 20:40 EST
Created by: Codex
Last Modified at: 2026-11-14 21:03 EST
Last Modified by: Codex
-->

---
status: accepted
---

# Bound V2 style constraints after reward-only trials fail

Reward v3 was evaluated with both full-model and heads-only optimizer ownership. Full-model5M remained collapsed. Heads-only5M moved in the intended direction—aggressive shooting rose to15.6% above the mean, explorer first visits to9.2% above the mean, and aggressive/explorer counterfactual JS to0.018—but did not reach the frozen20%/0.02 gates; aggressive hit rate and cautious survival also failed.

V2 therefore adds a bounded auxiliary style loss instead of further increasing scalar rewards. The loss uses only information already legal in each AI's5×5 observation, scalar state and action mask. It supervises aggressive directional shooting only when the player is visibly aligned and that shot is legal; supervises cautious retreat only below60% HP when a legal opposite move exists; encourages explorer legal movement relative to the other heads; and applies a minimum pairwise JS hinge of0.02. It cannot access the full map, hidden player state, another AI's memory or future transitions.

The auxiliary coefficient is fixed at `0.02`; reward v3 and all effectiveness gates remain unchanged. The controlled run starts from reward-v3 heads-only checkpoint `0b45c37551aa7bf533e59ec77212fbc6c15c14dab97dde9efcc8228285e75f85`, keeps the shared trunk/GRU frozen, resets optimizer and environment state, and evaluates at5M before any extension. A model that becomes visibly different but violates V1 escape regression, timeout, friendly-fire or quantization gates is rejected.

The first raw-scale trial improved behavior but exposed scale imbalance: a JS gap is at most `0.02` while cross-entropy is commonly near `2`. The corrected trial normalizes every hinge by its target and every tactical CE by its maximum-category log scale, adds explorer local-fog frontier and cautious legal sound-retreat targets, retains coefficient `0.02`, and starts from raw-scale checkpoint `f9b6c54422a825388ddb3d164c07cf0dfbd45178963273866004e8b52fdc5567` with a fresh optimizer.
