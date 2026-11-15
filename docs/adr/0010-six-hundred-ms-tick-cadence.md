<!--
Created at: 2026-11-15 02:30 EST
Created by: Codex
Last Modified at: 2026-11-15 02:30 EST
Last Modified by: Codex
-->

---
status: accepted
---

# Six-hundred-millisecond product tick cadence

CataMaze changes real-time Game Session cadence from 1,000 ms to 600 ms so queued input, ammunition feedback, and enemy encounters feel responsive while retaining one deterministic action per tick. Tick budgets and virtual transitions remain unchanged; wall-clock session lengths scale by 0.6. Because the product must reserve at least 100 ms for input, Game Core, dual displays, audio, and scheduling, the complete three-AI Resident Policy latency gate tightens from 900,000µs to 500,000µs.
