<!--
Created at: 2026-11-14 02:05 EST
Created by: Codex
Last Modified at: 2026-11-14 02:09 EST
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
| M0 | Documentation and reproducible Native toolchain | `IN_PROGRESS` |
| M1 | Complete headless Native game | `NOT_STARTED` |
| M2 | Browser-playable vertical slice with exact virtual OLEDs | `NOT_STARTED` |
| M3 | Native product hardening and expanded verification | `NOT_STARTED` |
| M4 | ESP32 adapter and compile-only integration | `NOT_STARTED` |
| M5 | Physical hardware integration, only after explicit upload approval | `NOT_STARTED` |
| M6 | Cross-platform determinism and release-candidate evidence | `NOT_STARTED` |

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
.venv/bin/pio test -e native -f test_core
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
.venv/bin/pio test -e native -f test_web
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

## Change control

- A failed milestone remains `IN_PROGRESS` or becomes `BLOCKED`; passing a subset of checks is not sufficient.
- Acceptance criteria may be tightened without invalidating earlier evidence, but removing a criterion requires a documented decision.
- The plan must be updated before changing milestone scope or order.
- Work stops at the current user's requested boundary: this run targets M0 through Native M1/M2/M3 work and does not upload hardware.
