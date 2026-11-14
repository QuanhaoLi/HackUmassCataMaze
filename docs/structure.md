<!--
Created at: 2026-11-14 02:05 EST
Created by: Codex
Last Modified at: 2026-11-14 04:33 EST
Last Modified by: Codex

本文档冻结 CataMaze v1 黑客松阶段的工程结构、工具链、目标边界与运行接口。
-->

# CataMaze v1 Engineering Structure

## 1. Status and scope

This document is the implementation contract for the first playable CataMaze v1 vertical slice. It is subordinate to `gamerules.md` for game behavior and to `restrictions.md` for non-negotiable boundaries.

The Native build is the verified reference implementation. The current delivery target extends that reference to an ESP32-S3 N16R8-class device through a thin adapter, read-only hardware preflight, bounded diagnostic upload, and then product upload. The Game Core and the two 128×64 framebuffer renderers remain shared and unchanged by platform wiring.

The following are intentionally deferred until after a playable Native game exists:

- 10,000-tick host/device state-hash comparison;
- million-tick stress testing;
- OTA, persistence, cloud services, and online inference;
- reinforcement-learning model deployment.

## 2. Frozen toolchain

| Concern | Selected technology | Version / policy |
|---|---|---|
| Language | ISO C++ | C++17 on every target |
| Build and environment orchestration | PlatformIO Core | `6.2.0`, installed in project-local `.venv` |
| Native platform | PlatformIO Native | exact package version pinned in `platformio.ini` |
| Embedded platform | PlatformIO Espressif 32 | `platformio/espressif32@8.0.0` |
| Embedded framework | Arduino Framework | Arduino ESP32 Core `3.3.12`, supplied by Espressif 32 platform 8.0.0 |
| Native compiler on the development Mac | Apple Clang | detected version 17; C++17 flags are explicit |
| Native unit tests | GoogleTest | PlatformIO Registry `1.17.0`, Native only |
| Native HTTP server | cpp-httplib | upstream single header `0.53.1`, SHA-256 pinned, NativeAdapter only |
| JSON serialization | JSON for Modern C++ upstream single header | `3.12.0`, SHA-256 pinned, NativeAdapter only |
| Browser client | HTML, CSS, JavaScript, Canvas 2D | no package manager and no bundler |
| Screenshot acceptance | Google Chrome headless | installed system browser; invoked from a repository script |

All versions must be pinned. Floating `latest`, unversioned Git branches, and implicit global dependencies are forbidden in committed build configuration.

## 3. Target matrix

### 3.1 `native`

The Native target runs on macOS or Linux and contains:

- the complete portable Game Core;
- the application coordinator;
- deterministic heuristic AI policies;
- the platform-independent two-screen pixel renderer;
- a NativeAdapter with monotonic time, loopback HTTP, and static web assets;
- an optional accelerated virtual clock for automated tests;
- structured logs to stderr.

The default server address is `127.0.0.1` with requested port `0`. Port zero delegates selection to the operating system, preventing collisions. After binding, the process prints exactly one discovery line:

```text
CATAMAZE_URL=http://127.0.0.1:<selected-port>
```

A caller may pass `--port <1..65535>` for a stable test port. Binding any non-loopback interface requires a future documented decision and is out of scope.

### 3.2 `esp32s3`

The future embedded target will contain:

- the same Game Core and application coordinator;
- ESP32Adapter implementations for GPIO, dual I²C OLEDs, monotonic time, USB Serial diagnostics, and non-blocking audio events;
- no HTTP server and no network dependency;
- no cloud or online inference requirement.

The provisional hardware class is ESP32-S3 N16R8. Exact PlatformIO board ID, flash mode, PSRAM mode, partition table, and any button row still marked pending in `hardware.md` remain `PENDING_HARDWARE_VERIFICATION` until the physical preflight resolves them. The documented dual-OLED buses have physical validation records. GPIO4 is an unassigned spare and must remain untouched. A successful generic compilation is not hardware evidence.

No `upload`, `flash`, `erase`, or equivalent target may be run during the Native phase.

## 4. Architecture

```text
Browser / automation
        |
        | HTTP on 127.0.0.1 only
        v
NativeAdapter -----------+
                         |
Future ESP32Adapter -----+--> Application Coordinator --> Pure C++ Game Core
                         |                                  |
TestAdapter -------------+                                  +--> deterministic events
                                                            +--> two 128x64 framebuffers
```

### 4.1 Game Core

The Game Core owns only deterministic domain state and rules:

- 50×50 terrain;
- player and three AI entities;
- HP, ammo, recharge phase, position, and life state;
- fixed-capacity 32-action player FIFO;
- bullet state and collision resolution;
- visibility and player-observable sound events;
- tick ordering and terminal-state precedence;
- deterministic maze generation and random-number state;
- structured domain events;
- serializable state hash.

The Game Core must not include or reference Arduino headers, GPIO numbers, HTTP concepts, operating-system clocks, threads, filesystem paths, or global random facilities.

### 4.2 Application Coordinator

The coordinator translates platform input into domain commands and coordinates:

- debounced input events;
- one-second real-time scheduling or accelerated virtual ticks;
- action queue mutation, including immediate `CLEAR`;
- one heuristic-policy decision for each living AI per tick;
- rendering snapshots after ticks and queue changes;
- sound-effect priority selection;
- immutable snapshots for adapters.

It depends on explicit ports such as `Clock`, `InputSource`, `DisplaySink`, `AudioEventSink`, and `DiagnosticsSink`. Platform implementations depend inward on these interfaces; the core never depends outward.

### 4.3 NativeAdapter

The NativeAdapter provides:

- a monotonic clock based on `std::chrono::steady_clock`;
- an OS-assigned loopback port;
- validated HTTP-to-command translation;
- immutable snapshot serialization;
- serving of a fixed, allow-listed web asset set;
- graceful shutdown on SIGINT/SIGTERM;
- no hidden mutation of Game Core state from HTTP worker threads.

HTTP handlers enqueue commands into one bounded application command queue. A single simulation owner executes all game mutations. Readers receive a copied immutable snapshot, avoiding data races and non-deterministic partial state.

### 4.4 ESP32Adapter

The future adapter will be a thin translation layer:

- `setup()` initializes validated displays, buttons, and Serial while leaving GPIO4 unconfigured;
- `loop()` runs non-blocking input scanning, tick scheduling, rendering, best-effort Serial audio events, and diagnostics;
- no long `delay()` calls;
- no heap allocation in steady-state gameplay;
- no network service;
- no duplicate implementation of game rules.

### 4.5 Initial heuristic AI policies

All three initial policies implement one `AiPolicy` interface. A policy receives only its own legal 5×5 observation, permitted sound cues, its own HP/ammo/action result, persona, and its private persistent memory. It never receives the full map or hidden player coordinates.

- **Aggressive:** shoot when the player is visible on an unobstructed cardinal line and ammo is available; otherwise choose a legal local move that reduces visible player distance. When the player is unseen, follow the most recent sound direction, then fall back to deterministic left-hand wall following.
- **Cautious:** shoot on a visible unobstructed cardinal line only when ammo is at least 2; prefer a legal move that increases distance from a visible player or visible incoming bullet. When no threat is visible, use deterministic right-hand wall following.
- **Explorer:** prefer legal adjacent cells with the lowest private visit count, using `UP, RIGHT, DOWN, LEFT` as the stable tie order rotated by its seeded initial heading. It shoots only when the player is visible on a cardinal line within two cells.

If a selected action is unavailable at execution time, the environment applies the normal rule result; policies do not receive hidden information to predict simultaneous conflicts. The policy interface remains replaceable by a future recurrent model without changing the engine.

## 5. Planned repository layout

Every directory is created only when its first implementation is needed, and every created directory receives its own `README.md` before code.

```text
README.md
plan.md
platformio.ini
requirements-dev.txt
docs/
  README.md
  gamerules.md
  hardware.md
  restrictions.md
  reward.md
  structure.md
lib/
  README.md
  catamaze_core/
    README.md
    include/catamaze/core/
    src/
  catamaze_app/
    README.md
    include/catamaze/app/
    src/
  catamaze_render/
    README.md
    include/catamaze/render/
    src/
src/
  README.md
  native/
    README.md
    main.cpp
  tools/
    README.md
    randomized.cpp
  esp32/
    README.md
    main.cpp
web/
  README.md
  index.html
  app.css
  app.js
test/
  README.md
  native/
    README.md
scripts/
  README.md
  native_smoke.sh
  screenshot_native.sh
```

ESP32 directories may be documented in advance but will not receive executable upload automation until the plan reaches the corresponding milestone.

## 6. Determinism contract

- All pseudo-random decisions use a repository-owned PCG32 implementation with explicit 64-bit seed and sequence values.
- `std::random_device`, implementation-defined distributions, wall-clock time, and pointer values may not influence game state.
- Iteration over unordered containers may not affect decisions or state hashes.
- Floating-point values are excluded from physical game resolution.
- Coordinates, actions, events, and tie-breaks use explicit stable ordering.
- A state hash covers rules version, seed, tick, terrain, entities, bullets, queue, recharge phases, AI memory, and terminal state.
- Native real-time mode and accelerated test mode must produce identical state for the same ordered command stream.

## 7. Native browser contract

### 7.1 Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Browser simulator shell |
| `GET` | `/app.css` | Fixed stylesheet |
| `GET` | `/app.js` | Fixed browser controller |
| `GET` | `/health` | Process readiness and version |
| `GET` | `/api/v1/snapshot` | Player-observable state and both framebuffers |
| `POST` | `/api/v1/action` | Enqueue one of nine actions or execute `CLEAR` |
| `POST` | `/api/v1/reset` | Reset using an explicit seed |
| `POST` | `/api/v1/clock` | Pause, step one tick, or select real-time mode |

Mutation requests accept JSON bodies no larger than 4 KiB. Unknown fields, actions, and content types are rejected. The Native server never exposes arbitrary filesystem paths.

### 7.2 Actual OLED output

The renderer produces two authoritative `128 × 64` one-bit framebuffers, each exactly 1,024 bytes in SSD1306 page order. The Native snapshot transports each framebuffer as a 2,048-character lowercase hexadecimal string. Browser Canvas code paints those bits without re-laying out text, ensuring screenshots show the same pixels intended for physical OLED transfer.

The API may include structured public state for automation, but the visible browser panels must be generated from the framebuffers. Hidden AI state is not included in the normal player snapshot.

The Map framebuffer deliberately omits every projectile even when its internal cell is legally visible. The HUD represents HP with five filled/outline heart glyphs and AMMO with three filled/outline cartridge glyphs. Numeric `player.hp` and `player.ammo` remain in the JSON envelope only for automation and accessibility; the visible OLED contract is icon-based.

### 7.3 JSON shapes

JavaScript cannot precisely represent every 64-bit integer, so seeds and state hashes are lowercase hexadecimal strings with a `0x` prefix.

Action request:

```json
{"action":"MOVE_UP"}
```

Allowed values are `MOVE_UP`, `MOVE_DOWN`, `MOVE_LEFT`, `MOVE_RIGHT`, `SHOOT_UP`, `SHOOT_DOWN`, `SHOOT_LEFT`, `SHOOT_RIGHT`, `WAIT`, and `CLEAR`. Browser key handling implements FIRE as a modifier before sending one of these already-resolved commands.

Reset request:

```json
{"seed":"0x000000000134fd5a"}
```

Clock requests:

```json
{"mode":"REALTIME"}
{"mode":"PAUSED"}
{"command":"STEP"}
```

The snapshot response has a versioned envelope:

```json
{
  "schema":"catamaze.snapshot.v1",
  "rules":"catamaze.rules.v1",
  "seed":"0x000000000134fd5a",
  "state_hash":"0x0000000000000000",
  "status":"RUNNING",
  "tick":0,
  "player":{"hp":5,"ammo":3,"queue":0,"x":1,"y":1},
  "map_frame_hex":"<2048 lowercase hex characters>",
  "hud_frame_hex":"<2048 lowercase hex characters>",
  "last_events":[]
}
```

Only bounded player-observable event summaries may appear in `last_events`.

## 8. Dependency boundaries

- `catamaze_core`: C++ standard library only; embedded-safe subset.
- `catamaze_app`: core plus abstract ports; no Arduino or HTTP.
- `catamaze_render`: core snapshots plus fixed bitmap font; no OLED driver.
- `native`: cpp-httplib and nlohmann/json allowed.
- `esp32`: Arduino and validated device libraries allowed only in the adapter.
- tests: GoogleTest and test-only helpers allowed.

Third-party code must have an explicit version, compatible license, and a single ownership location. No library may introduce a second implementation of queueing, physics, visibility, or action validation.

## 9. Build and run interface

Planned commands after bootstrap:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/pio run -e native
.venv/bin/pio test -e native
.venv/bin/pio run -e native -t exec
```

The eventual embedded compile command is:

```bash
.venv/bin/pio run -e esp32s3
```

The following remains forbidden until explicit later authorization:

```bash
.venv/bin/pio run -e esp32s3 -t upload
```

## 10. Quality strategy and ordering

Quality work is staged so infrastructure cannot delay the first playable game:

1. Essential rule tests accompany each core subsystem.
2. A complete playable Native loop is delivered.
3. The browser and exact framebuffer view are visually checked with screenshots.
4. Native sanitizer, coverage, randomized simulation, and API robustness are expanded.
5. ESP32 compilation and adapter work begin only after the Native game is stable.
6. Hardware-in-the-loop, long stress runs, and cross-platform determinism gates come last.

The authoritative milestone gates are in `../plan.md`.
