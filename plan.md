<!--
Created at: 2026-11-14 02:05 EST
Created by: Codex
Last Modified at: 2026-11-14 03:30 EST
Last Modified by: Codex

本文档按可玩性优先原则拆分 CataMaze v1 里程碑，并为每个里程碑定义可执行验收门槛。
-->

# CataMaze v1 Implementation Plan

## Planning rule

The project delivers a playable game before expensive hardening. A milestone passes only when every required automated command exits successfully and every listed behavioral check is demonstrated. Future milestone infrastructure is not allowed to delay the current playable slice.

Status values are `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, and `PASSED`.

## Milestone overview

| Milestone | Outcome | Status |
|---|---|---|
| M0 | Documentation and reproducible Native toolchain | `PASSED` |
| M1 | Complete headless Native game | `PASSED` |
| M2 | Browser-playable vertical slice with exact virtual OLEDs | `PASSED` |
| M3 | Native product hardening and expanded verification | `PASSED` |
| M4 | ESP32 adapter and compile-only integration | `NOT_STARTED` |
| M5 | Physical hardware integration, only after explicit upload approval | `NOT_STARTED` |
| M6 | Cross-platform determinism and release-candidate evidence | `NOT_STARTED` |
| RL0 | Training contract, deployment boundary, and event attribution | `IN_PROGRESS` |
| RL1 | In-memory environment, observation, mask, and reward foundation | `NOT_STARTED` |
| RL2 | Recurrent actor-critic and PPO implementation | `NOT_STARTED` |
| RL3 | CPU smoke, deterministic replay, and checkpoint recovery | `NOT_STARTED` |
| RL4 | Single-V100 benchmark and two-hour stability qualification | `NOT_STARTED` |
| RL5 | Four-GPU isolated multi-seed training and final evaluation | `NOT_STARTED` |
| RL6 | Versioned Native export, integration, fallback, and rollback | `NOT_STARTED` |

## M0 — Documentation and Native bootstrap

### Deliverables

- `docs/structure.md`, `docs/restrictions.md`, and this plan are complete and indexed.
- Existing game and hardware documents reflect the approved 20 ms debounce and FIRE modifier semantics.
- Project-local Python environment contains PlatformIO Core 6.2.0.
- `platformio.ini` contains a pinned Native environment and no executable upload step.
- Folder READMEs exist before source files.
- A minimal Native executable and one smoke test build under C++17.

### Automated acceptance

```bash
.venv/bin/pio --version
.venv/bin/pio run -e native
.venv/bin/pio test -e native
git diff --check
```

Pass conditions:

- PlatformIO reports Core 6.2.0.
- Native build and smoke test exit 0.
- No ESP32 upload command is invoked.
- No project-owned whitespace error is reported.

### Human acceptance

- The documented architecture clearly separates Game Core, application coordination, and adapters.
- The plan keeps long stress, CI, physical self-test, and cross-platform hashing out of the first playable slice.

## M1 — Complete headless Native game

### Deliverables

- Deterministic 50×50 maze generation from an explicit seed.
- Player and three distinct deterministic heuristic AI personas.
- Nine actions, 32-entry FIFO, immediate CLEAR behavior, and one action consumed per tick.
- Simultaneous movement conflicts, shooting, bullets, damage, ammo recharge, death, victory, and timeout.
- Legal 5×5 observations and hidden-state boundaries.
- A headless Native runner with virtual stepping and a deterministic scripted command interface.
- Minimal essential unit tests written alongside each subsystem.

### Automated acceptance

```bash
.venv/bin/pio test -e native -f native/test_core
.venv/bin/pio run -e native
./scripts/native_smoke.sh --mode headless
```

Pass conditions:

- Fixed seed creates the same map and initial state in repeated runs.
- A scripted victory game reaches `VICTORY` before tick 2,000.
- A scripted combat game reaches `DEATH` through legal bullet damage.
- A no-escape scenario reaches `TIMEOUT` exactly at tick 2,000.
- Queue full, FIFO order, CLEAR, blocked movement, simultaneous conflict, ammo recharge, and death-over-victory precedence have passing focused tests.
- No browser, network, ESP32, million-tick, or CI requirement blocks M1.

### Human acceptance

- A developer can inspect a textual snapshot after every virtual tick and understand the complete game state available to the player.
- The game can be played to a terminal result through the headless command interface.

## M2 — Browser-playable vertical slice

### Deliverables

- Native server binds an available loopback port and prints `CATAMAZE_URL`.
- Browser accepts movement, FIRE-modified shots, WAIT, CLEAR, pause, step, and reset.
- Browser shows two virtual 128×64 OLED canvases sourced from authoritative framebuffers.
- Map OLED reveals only the player's legal 5×5 view.
- HUD OLED displays only TICK, HP, AMMO, QUEUE, and POS.
- Three heuristic AI personas make the game complete without an online service.
- Desktop and narrow-layout screenshots are generated and inspected.

### Automated acceptance

```bash
.venv/bin/pio test -e native -f native/test_web
./scripts/native_smoke.sh --mode browser
./scripts/screenshot_native.sh
```

Pass conditions:

- `/health`, snapshot, action, reset, and clock endpoints pass positive and negative tests.
- The server chooses a free port when no port is specified.
- A browser automation sequence performs at least movement, one shot, WAIT, CLEAR, pause, and step.
- Both framebuffer payloads are exactly 1,024 bytes after hexadecimal decoding.
- Headless Chrome produces desktop and narrow screenshots without console errors.

### Human acceptance

- Screenshots are visually inspected at full size.
- Both OLEDs are legible, aligned, and visibly distinct.
- A human can open the printed URL and play a complete game without terminal commands.
- The browser does not expose hidden map or AI information.

## M3 — Native product hardening

### Deliverables

- Expanded rule, renderer, API, and concurrency test suites.
- AddressSanitizer and UndefinedBehaviorSanitizer Native builds.
- Deterministic randomized simulations with invariant checking.
- Coverage reporting and explicit budgets.
- Graceful shutdown, malformed-request handling, queue saturation behavior, and log hygiene.
- CI configuration for Native build and tests only after local commands are stable.

### Automated acceptance

```bash
.venv/bin/pio test -e native
./scripts/run_sanitizers.sh
./scripts/run_randomized.sh --ticks 100000
./scripts/run_coverage.sh
```

Pass conditions:

- All Native tests pass under normal, ASan, and UBSan builds.
- 100,000 randomized ticks produce no invariant failure, crash, leak, or undefined behavior.
- Core line coverage is at least 85%; core branch coverage is at least 75%.
- Repeating the randomized run with the same seed produces the same final state hash.
- CI runs only commands already proven locally.

### Human acceptance

- Failures identify seed, tick, action stream, and state hash.
- Test runtime remains short enough for normal development; million-tick runs remain deferred.

### Completion evidence — 2026-11-14

- Normal Native suite: 30/30 tests passed.
- AddressSanitizer suite: 30/30 tests passed; LeakSanitizer is explicitly unavailable in Apple Clang's macOS runtime.
- UndefinedBehaviorSanitizer suite: 30/30 tests passed with no recovery.
- Randomized invariant run: 100,000 ticks across 61 games, repeated output hash `0x0739ad1063a70f69`.
- Portable core/application coverage: 86.91% lines and 77.88% branches, above the 85% / 75% gates.
- Browser smoke: random loopback port, versioned API, malformed requests, commands, reset, and graceful SIGTERM passed.
- Visual QA: 1440×1050 desktop and true 390×1800 CSS-viewport screenshots passed overflow checks and manual inspection.
- Horror-visibility revision: player Map has blank roads, solid walls, one-slash fog, no projectile pixels under any projectile state, and an outline-diamond player; HUD has five filled/outline hearts and three filled/outline ammo cartridges.
- Audible-event adapter: successful own shot is observable as `OWN_SHOT`; player damage and nearby enemy shots use higher-priority buzzer rhythms without exposing shooter coordinates.

## M4 — ESP32 adapter and compile-only integration

### Entry gate

- M2 and M3 are `PASSED`.
- Exact board configuration remains documented as provisional unless physical evidence resolves it.

### Deliverables

- Pinned `esp32s3` PlatformIO environment.
- Thin adapters for clock, USB Serial diagnostics, dual displays, buttons, and active buzzer.
- Compile-time GPIO configuration isolated from domain code.
- Startup diagnostics for expected flash/PSRAM capabilities implemented but not claimed as physically passed.
- Embedded build only; no upload.

### Automated acceptance

```bash
.venv/bin/pio run -e esp32s3
```

Pass conditions:

- Firmware compiles with C++17 and Arduino Core 3.3.12.
- Linker memory report fits provisional N16R8 budgets.
- No HTTP, JSON, or host-only dependency appears in the firmware dependency graph.
- No `upload`, `flash`, or `erase` target is invoked.

## M5 — Physical hardware integration

### Entry gate

- The user explicitly authorizes an ESP32 upload in a future request.
- Board identity, flash mode, PSRAM mode, GPIO map, and buzzer polarity are reconciled with physical evidence.

### Deliverables

- Automated serial-port discovery by USB metadata.
- Pre-upload flash identity check.
- Physical display, input, and buzzer adapters validated in isolation, then together.
- Hardware results recorded in `docs/hardware.md` without inference.

### Pass conditions

- Device-reported flash and PSRAM match the approved configuration.
- Both I²C buses independently find exactly one display at `0x3C`.
- All seven buttons pass HIGH → LOW → HIGH and 20 ms debounce tests without repeat.
- FIRE modifier semantics match Native behavior.
- Buzzer is off at boot and plays only approved non-blocking patterns.
- One complete game is playable on the physical device.

## M6 — Cross-platform determinism and release-candidate evidence

### Deliverables

- Shared golden command streams run on Native and ESP32.
- Cross-platform state hashes, framebuffer hashes, and event traces are compared.
- Long-duration stability and million-tick Native stress are added.
- Final dependency, size, timing, and known-limit report is produced.

### Pass conditions

- Native and ESP32 match state hashes for at least 10,000 ticks over the approved golden seeds.
- Native completes a one-million-tick invariant run with no sanitizer failure.
- Physical device completes the agreed endurance duration without watchdog reset, heap growth, stuck input, or display corruption.
- A complete game remains playable after all hardening work.

## RL0 — Training contract and event correctness

### Deliverables

- An ADR reconciles Native RL inference with standalone ESP32 gameplay and defines four-V100 usage.
- `docs/reward.md`, `docs/restrictions.md`, and this plan agree on the deployment and remote-execution boundary.
- Structured damage and death events preserve every contributing shooter and effective damage after HP capping.
- Simultaneous lethal hits have an explicit deterministic credit-allocation rule that supports equal kill-credit sharing.

### Acceptance

- Focused C++ tests cover single hit, overkill, simultaneous multi-shooter damage, friendly fire, and lethal credit.
- Existing state-hash, sanitizer, randomized, and gameplay behavior remain deterministic.
- No training reward needs to infer shooter credit from event ordering or mutable post-step state.

## RL1 — Environment and reward foundation

### Deliverables

- A pinned Native Python extension exposes batched pure-memory reset, observation, step, and structured info without HTTP or subprocesses.
- Observation encoding has exactly `[13, 5, 5]` spatial and `[46]` scalar shapes with one versioned schema.
- One action-mask implementation enforces wall, boundary, ammo, death, and always-legal `WAIT` rules.
- Reward calculation emits every named component plus an exact total and maintains independent per-agent visited state.
- Player opponent policies and randomized training spawns use explicit seeds.

### Acceptance

- Golden trajectories cover every reward row and terminal outcome.
- Property tests show masked actions are never sampled and private world state never enters model input.
- Environment replay is identical for fixed seed and ordered actions.
- A 64-environment CPU benchmark reports agent transitions per second and identifies the sampling bottleneck.

## RL2 — Recurrent actor-critic and PPO

### Deliverables

- The specified CNN, scalar MLP, 256-unit GRU, actor head, and critic head are implemented in pinned PyTorch.
- Recurrent rollout storage preserves initial hidden states, termination/truncation masks, old log-probabilities, values, and raw reward components.
- GAE and clipped PPO implement advantage normalization, value clipping, entropy scheduling, KL early stop, gradient clipping, and learning-rate decay.

### Acceptance

- Network, masking, hidden-reset, recurrent sequence, GAE, PPO-ratio, and CPU/GPU parity tests pass.
- A PPO update changes parameters without NaN/Inf and leaves padded/dead-agent timesteps out of every loss.
- Printed parameter count and tensor shapes match checkpoint metadata.

## RL3 — Smoke and recovery qualification

### Deliverables

- The player-policy curriculum, fixed evaluation suite, metrics, checkpointing, and exact resume path are complete.
- A 100,000-agent-step FP32 smoke run executes with the release configuration scaled only in duration.

### Acceptance

- Reward components sum exactly, illegal-action rate is zero, and every done agent clears its GRU state.
- A checkpoint resume produces the same next update as an uninterrupted reference run.
- Fixed-seed stochastic and deterministic evaluations replay exactly on the same software and hardware configuration.
- The run records resolved configuration, git revision, four contract versions, dependency versions, RNG states, and memory use.

## RL4 — Single-V100 stability qualification

### Deliverables

- The approved training host passes environment, CUDA, throughput, storage, and checkpoint diagnostics without changing host power or network state.
- One V100 establishes the FP32 reference and completes a continuous two-hour run.

### Acceptance

- Peak allocated memory remains below 14GB with no OOM, leak trend, NaN/Inf, throughput collapse, or invalid action.
- Evaluation, logging, checkpoint save/load, and failure-checkpoint paths all execute during the run.
- End-to-end agent transitions per second, GPU utilization, and CPU sampling utilization are reported before any topology change.

## RL5 — Four-GPU isolated multi-seed training

### Deliverables

- Four isolated single-GPU jobs train four independent seeds concurrently; the fifth required seed runs after a slot becomes available.
- Each job owns a distinct run directory, RNG state, checkpoint lineage, and GPU assignment.
- Final candidates are evaluated against random-valid, heuristic, feed-forward, no-persona, previous-production, and candidate baselines.

### Acceptance

- At least four of five seeds pass every effect, personality, correctness, and performance gate in `docs/reward.md`.
- Player escape rate improves by at least 20% relative to the heuristic baseline while player death rate increases rather than only timeout rate.
- Friendly fire, personality separation, confidence intervals, mean, standard deviation, and failure cases are reported.

## RL6 — Native export and rollback

### Deliverables

- A versioned TorchScript or ONNX Native artifact passes numerical parity against PyTorch.
- Native gameplay can select the model policy without changing Game Core rules and falls back to the heuristic policy on any model failure.
- Previous production artifacts remain selectable for rollback.

### Acceptance

- Export parity, CPU p95 latency, batched three-agent latency, resident memory, timeout, invalid-output, and fallback tests pass.
- Normal standalone ESP32 builds have no model runtime or network dependency.
- No embedded-model compatibility is claimed without a later ADR and physical-device evidence.

## Change control

- A failed milestone remains `IN_PROGRESS` or becomes `BLOCKED`; passing a subset of checks is not sufficient.
- Acceptance criteria may be tightened without invalidating earlier evidence, but removing a criterion requires a documented decision.
- The plan must be updated before changing milestone scope or order.
- The current user-authorized scope adds the RL0–RL6 track and remote four-V100 training after its correctness gates; it does not authorize hardware upload or any remote-server power transition.
