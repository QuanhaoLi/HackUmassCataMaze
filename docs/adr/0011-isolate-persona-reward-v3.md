<!--
Created at: 2026-11-14 20:04 EST
Created by: Codex
Last Modified at: 2026-11-14 20:04 EST
Last Modified by: Codex
-->

---
status: accepted
---

# Isolate persona reward v3 after V2 architecture ablation

The V2 multi-head architecture is not sufficient under V1 reward v2. At 10M staged steps it produced action and counterfactual JS above `0.02`, proving the persona path can specialize. After full-model fine-tuning to 25M cumulative steps, shared terminal and timeout incentives collapsed behavior again: combined action JS fell below `0.011`, counterfactual JS below `0.013`, explorer coverage did not separate, cautious survival failed, and hard-opponent escape regressed.

Ablations show this is not a disconnected architecture: removing all persona inputs reduces counterfactual JS to zero and action JS to approximately `0.00024`; removing modulation or independent heads changes behavior and effectiveness. Therefore V2 opens a separate `catamaze.reward.persona.v3` run rather than silently changing the architecture run or weakening gates.

Reward v3 exists only in `training/v2/`. V1 `training/reward.py`, V1 checkpoints, V1 reports, V1 firmware, and V1 release manifest remain immutable. The new run starts from the accepted 10M recurrent checkpoint, uses a new config/run ID, resets optimizer state, retains the same environment physics, observation and action contracts, and must re-pass every effectiveness, persona, export and quantization gate.
