<!--
Created at: 2026-11-14 02:05 EST
Created by: Codex
Last Modified at: 2026-11-14 02:09 EST
Last Modified by: Codex

本文档集中记录 CataMaze v1 实施过程中不可违反的产品、架构、硬件与运维限制。
-->

# CataMaze v1 Restrictions

Keywords `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are normative.

## 1. Current execution boundary

- The current phase MUST run and be tested on the local Mac only.
- No command may upload, flash, erase, reset, or otherwise mutate the connected ESP32.
- ESP32 code MAY be planned and later compiled without upload, but only after the playable Native milestones pass.
- Unknown hardware values MUST be labeled `PENDING_HARDWARE_VERIFICATION`; they MUST NOT be inferred from a similar board.
- Existing physical test evidence may be recorded, but no new hardware result may be claimed without an actual test.

## 2. Game Core isolation

- The Game Core MUST compile as C++17 without Arduino, ESP-IDF, HTTP, OS clock, GPIO, display-driver, or filesystem headers.
- The Game Core MUST NOT read global time, global randomness, environment variables, network input, or device state.
- Every state mutation MUST occur through an explicit command or tick transition.
- Physics, queue semantics, action legality, visibility, damage, ammo, and terminal logic MUST have one implementation source.
- Platform adapters MUST NOT repair, reinterpret, or duplicate domain rules.
- The Native web server MUST be optional; stopping it must not invalidate the engine design.

## 3. Determinism

- Map generation and AI choices MUST use the repository-owned PRNG and explicit seeds.
- The same rules version, seed, initial state, and ordered commands MUST produce the same state transition sequence.
- Physical resolution MUST use integer and enum values; floating-point comparisons MUST NOT decide movement, damage, or terminal state.
- Simultaneous resolution and all tie-breaks MUST use documented stable ordering.
- Debug logging, rendering frequency, HTTP polling, and machine speed MUST NOT affect game state.
- Tests MUST be able to advance time virtually without sleeping.

## 4. Player controls

- The player action FIFO capacity is exactly 32.
- One queued action is consumed per game tick; an empty queue produces `WAIT`.
- `UP`, `DOWN`, `LEFT`, and `RIGHT` enqueue movement when FIRE is not held at the direction press sample.
- FIRE is sampled at the debounced direction-press event.
- FIRE already held plus a direction press enqueues a shot in that direction.
- Pressing FIRE after a direction event MUST NOT change the queued action.
- FIRE alone has no game action.
- WAIT enqueues one wait action.
- CLEAR immediately removes all actions that have not started execution.
- A full queue rejects new queued actions without replacing old actions.
- Button debounce is 20 ms by default.
- A held button MUST NOT auto-repeat; another event requires a debounced release followed by a new debounced press.

## 5. Timing and concurrency

- Normal gameplay advances at one tick per second.
- Production logic MUST NOT use long blocking sleeps or `delay()` calls.
- Native automated tests MUST use a virtual clock.
- Exactly one simulation owner may mutate the game state.
- HTTP workers and future hardware callbacks may only enqueue bounded commands or read immutable snapshots.
- No unbounded command, event, audio, log, or input queue is permitted.
- Rendering and browser polling MUST NOT advance the simulation implicitly.

## 6. Browser simulator

- The Native server MUST bind to `127.0.0.1` only.
- The default requested port MUST be zero so the OS selects an available port.
- The selected URL MUST be printed for humans and automation.
- Browser controls MUST use the same application command path as future physical controls.
- The two visible virtual OLEDs MUST render authoritative 128×64 one-bit framebuffers, not independently recreated HTML text.
- Normal browser state MUST NOT reveal hidden terrain, unseen enemies, private AI state, or future actions.
- Static-file serving MUST use an allow-list and MUST NOT expose repository paths.
- Request bodies and field values MUST be bounded and validated.

## 7. Hardware truth and provisional values

- The controller is provisionally treated as ESP32-S3 N16R8-class, not as a confirmed exact board SKU.
- Flash ID, flash capacity, PSRAM mode, and PSRAM initialization MUST be checked before any future physical upload is accepted.
- Serial-port discovery MUST use device metadata and MUST NOT hard-code `/dev/cu.*` paths.
- The two OLEDs use independent hardware I²C controllers when both respond at `0x3C`.
- Map display content is limited to the player's legal 5×5 view.
- HUD content is limited to `TICK`, `HP`, `AMMO`, `QUEUE`, and `POS`.
- GPIO numbers and buzzer polarity MUST come from reconciled physical test evidence in `hardware.md`.
- Any row still marked planned, pending, or unverified in `hardware.md` MUST remain provisional in code.
- The active buzzer MUST be normally off and driven by a non-blocking state machine.

## 8. Memory and embedded compatibility

- Portable code MUST avoid exceptions, RTTI dependencies, recursion proportional to map size, and unbounded allocation.
- Fixed game maxima MUST use fixed-capacity storage with explicit overflow handling.
- Portable code MUST NOT use `String`, Arduino containers, implementation-specific filesystem APIs, or host-only synchronization primitives.
- Heap allocation MAY occur during Native process setup, but steady-state core ticks MUST NOT require allocation.
- No code may assume `sizeof(long)`, host endianness, or native struct padding for serialized state.

## 9. Dependency and build reproducibility

- Build tools and libraries MUST be pinned to exact versions.
- The project-local `.venv` MUST be ignored by Git.
- Build outputs, coverage data, screenshots generated only for inspection, and local logs MUST be ignored unless intentionally promoted as test fixtures.
- A clean checkout MUST be buildable through documented commands without relying on undeclared global libraries.
- Native and embedded compilation flags MUST explicitly select C++17.
- Warnings from project code MUST be treated as errors in Native CI once the playable slice is complete.

## 10. Testing order

- Essential rule tests MUST be written while implementing the playable core.
- A complete playable game MUST precede million-tick stress testing, cross-platform hash gates, full CI hardening, and exhaustive hardware self-tests.
- Tests MUST remain proportional to the current milestone and MUST NOT block delivery of the first playable slice for future-platform infrastructure.
- No milestone passes merely because code compiles; each milestone has behavioral acceptance gates in `../plan.md`.
- Screenshot review is mandatory for browser milestones and MUST inspect both desktop and narrow viewport layouts.
- Hardware tests and results MUST NOT be simulated and reported as physical evidence.

## 11. Deferred features

The following MUST NOT be added to the current hackathon slice unless the plan is explicitly revised:

- OTA or remote firmware updates;
- persistent saved games;
- cloud services, authentication, databases, or telemetry upload;
- online AI inference;
- production security provisioning;
- battery-management firmware;
- reinforcement-learning training inside the game runtime.

Interfaces MAY reserve extension points, but speculative implementations are prohibited.

## 12. Repository documentation

- Every created folder and subfolder MUST contain the repository-standard `README.md` before code is added there.
- Every project file MUST include creation and last-modification metadata in a comment-compatible form.
- Important decisions MUST be documented before their implementation.
- New non-negotiable constraints MUST be added here and indexed by `docs/README.md`.
- User-owned uncommitted changes MUST NOT be staged or overwritten without explicit instruction.

## 13. Remote-server power safety

- Automation MUST NOT reboot, shut down, power off, halt, kexec, change init targets, trigger SysRq reboot, or cause any equivalent power transition on server `100.83.174.76` (`a-Default-string`).
- Automation MUST NOT stop or disable SSH, Tailscale, or host networking on that server.
- `sudo` does not authorize a power transition or removal of the server's power-safety guard.
- If a future training, driver, or package task requires a reboot, work MUST stop and the user must perform it outside Codex.
