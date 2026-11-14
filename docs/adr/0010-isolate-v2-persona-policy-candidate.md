<!--
Created at: 2026-11-14 18:52 EST
Created by: Codex
Last Modified at: 2026-11-14 18:52 EST
Last Modified by: Codex
-->

---
status: accepted
---

# Isolate the V2 persona policy candidate from V1 deployment

V2 is an independent model-candidate line, not an in-place upgrade. It may reuse the frozen V1 environment, observation, action mask, reward baseline and checkpoint as read-only inputs, but all V2 implementation, configuration, tests, runs and artifacts live under V2-specific namespaces. The V2 owner stops after producing a hashed checkpoint/ONNX/ESP-DL evaluation bundle and must not modify the V1 firmware, default build, release manifest, upload workflow or physical board.

V2 uses one shared encoder and GRU, zero-initialized persona affine modulation, three actor heads and three training-only critic heads. V1 behavior is copied into every head so the migrated model is numerically equivalent at step 0. Architecture and reward changes are evaluated in separate runs. Product integration begins only after explicit handoff to the deployment owner and follows an isolated candidate build, replay, physical latency/memory, 10,000-tick endurance and explicit promotion sequence.
