<!--
Created at: 2026-11-14 11:27 EST
Created by: Codex
Last Modified at: 2026-11-14 11:27 EST
Last Modified by: Codex
-->

---
status: accepted
---

# Companion shell outside Game Core

CataMaze boots into Companion Idle, where the two OLEDs form one expressive face; any first button intent is consumed to Wake into Home. Companion animation and the 30-second activity clock live in a portable product shell around the existing deterministic system/game controller, so they cannot alter Game Core hashes, AI/RL observations, policy hidden state, ticks, or map generation. Non-game menus sleep directly after inactivity, while an active or paused Game Session first enters a default-Continue confirmation because silent abandonment would be destructive.
