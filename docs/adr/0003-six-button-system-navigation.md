<!--
Created at: 2026-11-14 06:57 EST
Created by: Codex
Last Modified at: 2026-11-14 06:57 EST
Last Modified by: Codex
-->

---
status: accepted
---

# Six-button system navigation and retained Wait Action

CataMaze removes the physical WAIT button and uses six buttons across Home, Setup, menus, and gameplay. CLEAR short and 0.8-second long press are separate intents so pausing never clears the Action Queue; the domain Wait Action remains at action index 8 for empty queues, AI fallback, and RL compatibility. This avoids a seventh physical control while preserving the frozen game and model action schema.

## Consequences

Input adapters must delay CLEAR short-press commitment until release, commit long press once at 800 ms, and suppress the later short event. Navigation is mode-dependent, but the six physical controls and their canonical intents remain consistent across Native and ESP32.
