<!--
Created at: 2026-11-14 18:46 EST
Created by: Codex
Last Modified at: 2026-11-14 18:46 EST
Last Modified by: Codex
-->

---
status: accepted
---

# Atomic resident policy without manual switching

CataMaze exposes no player-selectable AI mode: one released Resident Policy is automatically active when its release manifest, startup reference envelope, memory, output, legal mask, and latency checks pass; otherwise Heuristic Fallback latches until reboot. A Policy Tick is atomic across all living AI—model actions and next hidden states commit only after every required inference succeeds within budget, and any failure makes the entire tick use deterministic heuristic actions—so one world transition can never mix model and fallback decisions.
