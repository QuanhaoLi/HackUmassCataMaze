<!--
Created at: 2026-11-14 02:05 EST
Created by: Codex
Last Modified at: 2026-11-15 02:33 EST
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
| C1 | Companion Idle, expressive dual eyes, Wake, and inactivity shell | `IN_PROGRESS` |
| M3 | Native product hardening and expanded verification | `PASSED` |
| M4 | ESP32 adapter and compile-only integration | `PASSED` |
| M5 | Physical hardware integration after explicit upload approval | `IN_PROGRESS` |
| M6 | Cross-platform determinism and release-candidate evidence | `NOT_STARTED` |
| RL0 | Training contract, deployment boundary, and event attribution | `PASSED` |
| RL1 | In-memory environment, observation, mask, and reward foundation | `PASSED` |
| RL2 | Recurrent actor-critic and PPO implementation | `IN_PROGRESS` |
| RL3 | CPU smoke, deterministic replay, and checkpoint recovery | `PASSED` |
| RL4 | Single-V100 benchmark and two-hour stability qualification | `NOT_STARTED` |
| RL5 | Four-GPU DDP training of one production model and final evaluation | `NOT_STARTED` |
| RL6 | Atomic resident policy, manifest, parity, health, and fallback | `IN_PROGRESS` |

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
- Nine domain actions, 32-entry FIFO, explicit queue-clear mutation, and one action consumed per tick.
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
- Browser accepts directional navigation/movement, FIRE confirm/shoot, CLEAR short/long, pause, step, and reset without a WAIT control.
- Browser shows two virtual 128×64 OLED canvases sourced from authoritative framebuffers.
- Map OLED reveals only the player's legal 9×5 view.
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

- `/health`, snapshot, six-button input, reset, and clock endpoints pass positive and negative tests.
- The server chooses a free port when no port is specified.
- A browser automation sequence performs navigation, movement, one shot, CLEAR short, CLEAR long, pause, resume, and step; long release never clears the queue.
- Both framebuffer payloads are exactly 1,024 bytes after hexadecimal decoding.
- Headless Chrome produces desktop and narrow screenshots without console errors.

### Human acceptance

- Screenshots are visually inspected at full size.
- Both OLEDs are legible, aligned, and visibly distinct.
- A human can open the printed URL and play a complete game without terminal commands.
- The browser does not expose hidden map or AI information.

### Home/Setup revision evidence — 2026-11-14

- Portable `SystemController` boots to Home, uses the 30×30 recommended default, and owns Setup, read-only System/About, Game Session, Pause, abandon confirmation, and Result transitions.
- Reviewed presets 12×12, 20×20, 30×30, and 50×50 generate deterministic connected worlds with tick budgets 480, 800, 1,200, and 2,000; the player remains 9×5 and every AI remains 5×5.
- Twelve renderer tests cover deterministic Home, Setup, Game, Pause, confirmation, About/System, and Result framebuffers; the browser transports exact left/right 1,024-byte OLED buffers through snapshot schema v2.
- Real Chrome automation proved CLEAR long pauses without clearing, long release emits no short action, CLEAR short resumes the preserved queue, FIRE sampling shoots once, manual WAIT is rejected, and focused form input cannot leak into game controls.
- Fresh 1440×1050 and 390×1800 screenshots passed overflow, console-error, legibility, alignment, and six-button visual inspection.

## C1 — Companion Idle vertical slice

### Deliverables

- Portable product shell around the existing deterministic system/game controller.
- Companion Idle boot, consumed Wake, 30-second activity tracking, and guarded active-session Sleep.
- Nine reviewed dual-eye framebuffer expressions driven by an explicit monotonic timestamp.
- Exact left/right browser OLED output with no independent HTML recreation.
- ESP32 compile-only integration after Native acceptance; physical upload remains blocked by the open raw-button fault.

### Automated acceptance

```bash
.venv/bin/pio test -e native
./scripts/native_smoke.sh --mode browser
./scripts/screenshot_native.sh
./scripts/run_sanitizers.sh
./scripts/run_coverage.sh
```

Pass conditions:

- Boot is Companion Idle and every input wakes to Home without executing its normal Home/Game meaning.
- Inactivity changes state at exactly 30,000 ms using wrap-safe explicit time.
- Active-session prompt freezes state/queue, defaults to Continue, and requires explicit Sleep confirmation.
- All reviewed eye frames and prompt layouts pass deterministic pixel tests.
- Real Chrome verifies Wake, Continue, Sleep, exact OLED payloads, no console errors, and no horizontal overflow at 1440 px and 390 px.
- Existing Game Core, AI/RL schema, system navigation, sanitizers, coverage, and randomized gates remain green.
- The ESP32 product environment compiles with the current policy integration, but no companion image is uploaded until six raw buttons pass.

### Human acceptance

- The two screens read as one expressive face at physical scale.
- Expression timing feels alive without rapid flashing or blocking input.
- A user can distinguish Companion Idle, Home, Pause Menu, and Inactivity Prompt without instruction.
- M5 remains separate: physical buttons, ESP-DL latency/fallback, eyes, audio, and a complete Game Session still require hardware observation.

### Native completion evidence — 2026-11-14

- Portable shell tests prove all seven resolved Wake intents are consumed, 30,000 ms boundaries and `millis()` wrap are exact, and Continue/Sleep preserve or abandon the correct session.
- All nine expressions have deterministic pixel coverage; Chrome captures Neutral, Look Right, Curious, Surprised, and Neutral return at desktop size plus a clean 390 px layout.
- Normal, ASan, and UBSan suites each pass 86/86; randomized 100,000 ticks retain hash `0xaa4060b19cb592b1`; coverage is 90.72% lines and 82.05% branches.
- Native snapshot v3 and browser automation pass Wake, second-FIRE Play, 30-second prompt, Continue, explicit Sleep, and exact framebuffer checks.
- Local model checks pass artifact SHA-256, the frozen 10,000-observation 98.61% agreement report, four export/recurrent tests, and the portable provider/fallback integration test.
- Combined Companion Idle plus ESP-DL product firmware compiles at 55,012 bytes RAM and 2,912,175 bytes Flash. The replacement remote passed all six raw-input transitions and the guarded companion/model image is physically installed; the 30-second physical prompt/endurance checks keep C1 `IN_PROGRESS`.
- Native real-time sampling measured five consecutive intervals at 598.7–601.6ms with a 599.4ms mean, validating the 600ms Tick Cadence independently of virtual stepping.
- A 64-seed stationary-player encounter baseline found median first visibility at 27s / 1m36s / 4m02s / 11m38s for 12/20/30/50 maps at 600ms cadence; Tiny is the reviewed quick model-demonstration preset.

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

- Normal Native suite: 86/86 tests passed.
- AddressSanitizer suite: 86/86 tests passed; LeakSanitizer is explicitly unavailable in Apple Clang's macOS runtime.
- UndefinedBehaviorSanitizer suite: 86/86 tests passed with no recovery.
- Randomized invariant run: 100,000 ticks across 54 games, repeated output hash `0xaa4060b19cb592b1`.
- Portable core/application coverage: 90.72% lines and 82.05% branches, above the 85% / 75% gates; the portable six-button interpreter itself remains fully line-covered.
- Ammo recovery regression proves full ammo cannot bank recharge credit; a successful shot from full now visibly remains at two rounds for the following tick instead of restoring in the same transition.
- Wall-shot regression proves a successful shot into an adjacent wall consumes ammo, creates no projectile, remains at two rounds for two subsequent tick boundaries, and only then restores.
- Browser smoke: random loopback port, versioned API, malformed requests, commands, reset, and graceful SIGTERM passed.
- Visual QA: 1440×1050 desktop and true 390×1800 CSS-viewport screenshots passed overflow checks and manual inspection.
- Horror-visibility revision: player Map has blank roads, solid walls, one-slash fog, no projectile pixels under any projectile state, and an outline-diamond player; HUD has five filled/outline hearts and three filled/outline ammo cartridges.
- Audible-event adapter: successful own shot is observable as `PLAYER_SHOT`; player damage and nearby enemy shots use higher-priority Mac-speaker sounds without exposing shooter coordinates.
- HUD revision: title removed; labels begin at `x=1`, every value/icon group begins at `x=44`, and row origins are `3/15/27/39/51`.
- Player-only view revision: human display is 9×5 with 12×12 square tiles; AI policy/RL observation remains exactly 5×5 and is contract-tested.
- Mac companion protocol/assets: 3/3 strict parser, sequence wrap/deduplication, and generated WAV tests passed.

## M4 — ESP32 adapter and compile-only integration

### Entry gate

- M2 and M3 are `PASSED`.
- Exact board configuration remains documented as provisional unless physical evidence resolves it.

### Deliverables

- Pinned `esp32s3` PlatformIO environment.
- Thin adapters for clock, USB Serial diagnostics/audio events, two independent displays, and buttons.
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

### Completion evidence — 2026-11-14

- `esp32s3_diagnostic` compile passed on PlatformIO Espressif32 8.0.0 / Arduino Core 3.3.12.
- Production `esp32s3` compile passed with only shared app/core/render and Wire dependencies.
- Current production memory: 46,444 bytes static RAM (14.2%) and 375,667 bytes app Flash (5.7% of partition).
- Product firmware contains canonical `CATAMAZE_AUDIO` and boot diagnostics and contains no httplib/nlohmann dependency.
- Static source audit found no GPIO4 pin initialization or write.
- Display output is queued and serviced one 16-byte I²C chunk per loop to preserve input responsiveness at 100 kHz.

## M5 — Physical hardware integration

### Entry gate

- The user explicitly authorized ESP32 diagnostic and product uploads on 2026-11-14.
- Board identity, flash mode, PSRAM mode, and GPIO map are reconciled with physical evidence.

### Deliverables

- Portable six-button input interpreter with Native tests for debounce, no-repeat, FIRE sampling, and CLEAR short/long suppression.
- ESP32 Home/Setup integration through the shared `SystemController` and exact `SystemRenderer` framebuffers.
- Automated serial-port discovery by USB metadata.
- Pre-upload flash identity check.
- Physical display and input adapters validated in isolation, then together.
- USB Serial audio events and the Mac speaker companion validated without creating a gameplay dependency.
- Hardware results recorded in `docs/hardware.md` without inference.

### Pass conditions

- Device-reported flash and PSRAM match the approved configuration.
- Both I²C buses independently find exactly one display at `0x3C`.
- All six buttons pass HIGH → LOW → HIGH and 20 ms debounce tests without repeat; CLEAR long/short suppression passes.
- FIRE modifier semantics match Native behavior.
- GPIO4 remains unconfigured and the disconnected-Mac game remains fully playable.
- Each canonical audio event reaches the Mac speaker without hidden-state fields or gameplay blocking.
- One complete game is playable on the physical device.

### Current physical evidence — 2026-11-14

- Active replacement-board preflight confirmed ESP32-S3 rev 0.2, 16 MB Quad Flash, 8 MB PSRAM, CH343 USB-UART, and 3.3 V configuration.
- Diagnostic firmware upload and verified Flash write succeeded; GPIO4 remained unconfigured.
- All six active button inputs were HIGH/released during observation. Manual press/debounce/long-press sequences remain pending.
- With displays reconnected, a fresh diagnostic found one `0x3C` device on each controller, all four lines HIGH, zero bus errors, and returned `pass=true`.
- The accepted image uses 16-bit maze workspace indices, deferred construction, and a 48 KiB loop task.
- Physical product boot returned `ready=true`, both `0x3C` displays, GPIO4 unconfigured, and loop stack high-water `26188` without rebooting.

### Approved Home/Setup migration sequence — 2026-11-14

- User approval has been received to replace the legacy seven-button ESP32 image.
- The old image is not accepted as evidence for Home/Setup, CLEAR long/short, map presets, or GPIO10 spare status.
- A new product upload is permitted only through `scripts/esp32_upload_product.sh` after the new portable input tests, both ESP32 compile gates, read-only identity preflight, and diagnostic v2 pass.
- M5 remains `IN_PROGRESS` after automated upload until the user completes the six-button and full-game physical checks.

### Home/Setup automated hardware evidence — 2026-11-14

- The release script passed 54 focused core/input tests immediately before hardware operations and both firmware environments compiled with pinned Espressif32 8.0.0 / Arduino 3.3.12.
- Product size is 46,476 bytes static RAM (14.2%) and 389,971 bytes application Flash (6.0% of the partition); the dependency graph contains only shared CataMaze libraries and Wire.
- Read-only preflight reconfirmed active-board serial `5CE6032515`, MAC `84:fc:e6:53:bf:94`, ESP32-S3 rev 0.2, 16 MB Quad Flash at 3.3 V, and 8 MB embedded PSRAM.
- Two consecutive diagnostic v2 runs passed with one `0x3C` device per bus, zero I²C errors, four HIGH bus lines, six released inputs, and GPIO4/GPIO10 unconfigured.
- Product write and hash verification passed. `catamaze.boot.v2` returned `ready=true`, `system_mode=HOME`, map 30×30, tick budget 1,200, six buttons, both displays at `0x3C`, and stack high-water 26,144.
- No full-chip erase command was issued. M5 remains `IN_PROGRESS` because visual content, all six physical transitions, CLEAR timing, FIRE sampling, audio during a shot, and a complete game require user observation.

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

### Completion evidence — 2026-11-14

- Native damage events now record one HP-capped `DAMAGE_APPLIED` plus per-shooter `DAMAGE_CREDIT` records; simultaneous lethal credit is deterministic.
- Focused engine and reward tests cover single-source damage, multi-shooter overkill, lethal splits, self damage, friendly fire, and component totals.
- Full Native tests passed 35/35 under both AddressSanitizer and UndefinedBehaviorSanitizer.
- The repeated 100,000-tick randomized invariant run passed with hash `0xca19bec167ee6693` after the intentional event-schema version change.

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

### Completion evidence — 2026-11-14

- The pybind11 batch bridge executes the portable C++ Game Core directly and returns only versioned legal tensors plus structured training labels.
- Twelve reviewed golden trajectories plus focused tests cover terminal, combat, death, friendly-fire, ammo, exploration, collision, invalid-fallback, potential, and timeout-bootstrap rewards.
- Exact reset/step replay, canonical environment serialization, partial reset isolation, seeded opponent policies, and randomized spawn replay pass.
- A 64-environment, 10,000-tick CPU benchmark sustained approximately 38,053 agent transitions/s.
- Seeds 1–1,000 completed 1,888,741 environment steps and 5,370,253 agent steps without illegal fallback, non-finite reward, component mismatch, capacity overflow, resource-range failure, or living-entity overlap.

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

### Completion evidence — 2026-11-14

- The final CPU qualification executed five full recurrent-PPO updates and 121,640 agent steps with zero illegal actions, NaN/Inf, component mismatch, or checkpoint failure.
- The model contains 1,010,826 parameters; final average KL was approximately `0.01152`, maximum minibatch KL `0.02053`, entropy `1.74456`, and no KL early stop fired.
- Exact checkpoint recovery reproduces the next environment hashes, observations, sampled actions, old log-probabilities, values, rewards, recurrent hidden state, and subsequent rollout.
- Fixed-seed deterministic and stochastic evaluators replay exactly and emit per-opponent/per-persona outcome, return, death, action, shot, hit, visit, and revisit metrics.
- The qualification artifact records resolved config, git revision, all four contract versions, Python/PyTorch/CUDA and dependency versions, peak RSS (`703,201,280` bytes), metrics JSONL, and a 12MB atomic checkpoint.

## RL4 — Single-V100 stability qualification

### Deliverables

- The approved training host passes environment, CUDA, throughput, storage, and checkpoint diagnostics without changing host power or network state.
- One V100 establishes the FP32 reference and completes a continuous two-hour run.

### Acceptance

- Peak allocated memory remains below 14GB with no OOM, leak trend, NaN/Inf, throughput collapse, or invalid action.
- Evaluation, logging, checkpoint save/load, and failure-checkpoint paths all execute during the run.
- End-to-end agent transitions per second, GPU utilization, and CPU sampling utilization are reported before any topology change.

## RL5 — Four-GPU DDP production training

### Deliverables

- Four DDP ranks train one shared model; each rank owns an environment shard, GRU state, opponent state, and RNG state.
- Rank 0 owns the single run directory, model/optimizer checkpoint lineage, evaluation reports, and curriculum decisions.
- Final candidates are evaluated against random-valid, heuristic, feed-forward, no-persona, previous-production, and candidate baselines.

### Acceptance

- The synchronized production model passes every effect, personality, correctness, and performance gate in `docs/reward.md`.
- Player escape rate improves by at least 20% relative to the heuristic baseline while player death rate increases rather than only timeout rate.
- Friendly fire, personality separation, confidence intervals, DDP throughput scaling, and failure cases are reported.

## RL6 — Atomic resident policy integration

### Deliverables

- One machine-readable release manifest generates or validates C++ identity/gate constants and upload acceptance.
- `Application` submits one atomic three-AI Policy Tick; no world transition can mix model and heuristic actions.
- Model hidden states commit only after all living-AI inferences and the complete-tick latency gate pass.
- Bounded Policy Health exposes ACTIVE/FALLBACK, reason, inference/failure counts, recent/max latency, memory, and artifact identity through System and Serial diagnostics.
- An offline Native parity adapter replays the frozen recurrent fixtures against a source ONNX artifact when that artifact is available; normal gameplay has no ONNX/Torch dependency.
- Previous release manifests and artifacts remain selectable at build/release time for rollback, not through a player menu.

### Acceptance

- Manifest drift, wrong artifact hash/size, tensor mismatch, non-finite output, illegal action, partial inference failure, and complete-tick timeout all have deterministic regression tests.
- Normal, ASan, UBSan, coverage, randomized, ESP32 compile, startup envelope, and guarded upload gates pass.
- Native and ESP32 recurrent traces match accepted tolerances when the source ONNX release artifact is present.
- The 10,000-tick physical endurance run reports no watchdog, heap trend, hidden corruption, mixed-policy tick, or unexpected fallback.

### Atomic v1 integration evidence — 2026-11-14

- `policy_release.json` is the single authority for SHA, bytes, shapes, exporter/runtime compatibility, agreement, reference tolerances, and complete-tick latency; Python tests and the ESP build reject drift.
- `Application` calls one Resident Policy module per tick. Focused regression proves a failing module cannot leak provisional model actions into the world transition and Restart does not clear a fallback latch.
- ESP-DL writes actions and next hidden states into provisional arrays and commits hidden state only after all living AI pass finite-output, legal-mask, and complete-tick latency gates.
- Policy Health is present in Native snapshot v3, the System software screen, boot v4, and a bounded runtime fallback Serial event.
- Normal, ASan, and UBSan suites each pass 86/86; randomized 100,000 ticks retain hash `0xaa4060b19cb592b1`; coverage is 90.72% lines and 82.05% branches.
- Guarded physical release passed manifest validation, six-button/dual-display diagnostics, write verification, and boot with `MODEL_ACTIVE`, `NONE`, zero failures, 126,239µs three-inference startup, 55,012 bytes static RAM, 2,912,167 bytes Flash, and stack high-water 26,068.
- The 600ms cadence revision tightens complete three-AI inference from 900,000µs to 500,000µs; the accepted v1 boot measurement remains approximately 126ms and passes with more than 370ms policy-budget margin.
- RL6 remains `IN_PROGRESS`: the source v1 ONNX release artifact is not present locally for Native recurrent-trace parity, and the 10,000-tick physical endurance gate remains outstanding.

## Change control

- A failed milestone remains `IN_PROGRESS` or becomes `BLOCKED`; passing a subset of checks is not sufficient.
- Acceptance criteria may be tightened without invalidating earlier evidence, but removing a criterion requires a documented decision.
- The plan must be updated before changing milestone scope or order.
- The current user-authorized scope adds the RL0–RL6 track and remote four-V100 training after its correctness gates; it does not authorize hardware upload or any remote-server power transition.
