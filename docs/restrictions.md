<!--
Created at: 2026-11-14 02:05 EST
Created by: Codex
Last Modified at: 2026-11-14 11:27 EST
Last Modified by: Codex

本文档集中记录 CataMaze v1 实施过程中不可违反的产品、架构、硬件与运维限制。
-->

# CataMaze v1 Restrictions

Keywords `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are normative.

## 1. Current execution boundary

- Native gameplay and training correctness gates MUST run locally before remote GPU training begins.
- After those gates pass, RL benchmark, stability, training, and evaluation jobs MAY run on the approved remote training server.
- The user authorized ESP32 compile, diagnostic upload, and product upload work on 2026-11-14.
- Before the first upload, automation MUST discover the serial device, read chip/Flash identity without mutation, and verify the exact upload target. Flash erase remains prohibited unless separately authorized.
- Uploads MUST progress from a bounded diagnostic firmware to the product firmware; a generic successful compile is not hardware evidence.
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
- There is no physical WAIT control and no user-facing manual WAIT command. Empty queue and AI fallback still produce Wait Action.
- CLEAR short press removes pending actions; CLEAR long press opens Pause Menu and MUST preserve the queue.
- Releasing CLEAR after its 800 ms long-press commit MUST NOT emit short press.
- A full queue rejects new queued actions without replacing old actions.
- Button debounce is 20 ms by default.
- A held button MUST NOT auto-repeat; another event requires a debounced release followed by a new debounced press.
- GPIO10 is an unassigned spare and MUST NOT be initialized as a button.
- The user approved six-button Home/Setup ESP32 migration on 2026-11-14. The legacy seven-button adapter MUST be replaced and pass portable input tests, compile gates, read-only preflight, and fresh diagnostic evidence before product upload.
- GPIO4 and GPIO10 MUST both remain absent from product and diagnostic `pinMode`, `digitalRead`, `digitalWrite`, and button arrays.

## 5. Timing and concurrency

- Normal gameplay advances at one tick per second.
- Production logic MUST NOT use long blocking sleeps or `delay()` calls.
- Native automated tests MUST use a virtual clock.
- Exactly one simulation owner may mutate the game state.
- HTTP workers and future hardware callbacks may only enqueue bounded commands or read immutable snapshots.
- No unbounded command, event, audio, log, or input queue is permitted.
- Rendering and browser polling MUST NOT advance the simulation implicitly.
- Companion Idle animation and inactivity timing MUST remain outside Game Core state, hashes, AI/RL observations, rewards, and recurrent model memory.
- Wake MUST consume the first button intent so it cannot also mutate Home or a Game Session.
- A live Game Session MUST freeze before Inactivity Prompt appears and MUST NOT be abandoned without explicit Sleep confirmation.

## 6. Browser simulator

- The Native server MUST bind to `127.0.0.1` only.
- The default requested port MUST be zero so the OS selects an available port.
- The selected URL MUST be printed for humans and automation.
- Browser controls MUST use the same application command path as future physical controls.
- The two visible virtual OLEDs MUST render authoritative 128×64 one-bit framebuffers, not independently recreated HTML text.
- Normal browser state MUST NOT reveal hidden terrain, unseen enemies, private AI state, or future actions.
- The player Map OLED MUST NOT render any projectile, muzzle flash, trajectory, or gunshot direction graphic. Projectile state remains internal and may remain in legal AI observations.
- The HUD MUST render five HP slots as filled/outline hearts and three AMMO slots as filled/outline cartridge icons. Plain `current/max` text is not the product HUD.
- Static-file serving MUST use an allow-list and MUST NOT expose repository paths.
- Request bodies and field values MUST be bounded and validated.

## 7. Hardware truth and provisional values

- The controller is provisionally treated as ESP32-S3 N16R8-class, not as a confirmed exact board SKU.
- Flash ID, flash capacity, PSRAM mode, and PSRAM initialization MUST be checked before any future physical upload is accepted.
- Serial-port discovery MUST use device metadata and MUST NOT hard-code `/dev/cu.*` paths.
- The two OLEDs use independent hardware I²C controllers when both respond at `0x3C`.
- Map display content is limited to the player's legal 9×5 terrain and visible enemies, with all projectile graphics intentionally omitted.
- Every AI observation remains exactly 5×5. Player-only peripheral cells MUST NOT enter AI policies, action masks, recurrent memory, rewards, Native RL bindings, or training tensors.
- HUD content is limited to `TICK`, five HP hearts, three AMMO cartridges, `QUEUE`, and `POS`.
- GPIO4 MUST remain unconfigured and unassigned in production firmware; it is a released spare.
- Any row still marked planned, pending, or unverified in `hardware.md` MUST remain provisional in code.
- The product MUST NOT depend on a physical buzzer or another ESP32 audio transducer.

## 8. Optional audio transport

- The Game Core MUST emit abstract player-observable audio events, never tones, files, Serial lines, or Mac APIs.
- ESP32 audio output MUST use the versioned `CATAMAZE_AUDIO ` USB Serial protocol in `audio.md`.
- Audio transmission MUST be best-effort and non-blocking; insufficient capacity drops the event.
- No offline backlog or reconnect replay is permitted.
- Mac disconnect, companion failure, malformed lines, or missing assets MUST NOT affect game timing, state, hash, input, displays, or AI.
- Audio events MUST NOT expose coordinates, directions, hidden identities, HP, ammo, or map data.
- At most one highest-priority audio event may be emitted per tick.

## 9. Memory and embedded compatibility

- Portable code MUST avoid exceptions, RTTI dependencies, recursion proportional to map size, and unbounded allocation.
- Fixed game maxima MUST use fixed-capacity storage with explicit overflow handling.
- Portable code MUST NOT use `String`, Arduino containers, implementation-specific filesystem APIs, or host-only synchronization primitives.
- Heap allocation MAY occur during Native process setup, but steady-state core ticks MUST NOT require allocation.
- No code may assume `sizeof(long)`, host endianness, or native struct padding for serialized state.

## 10. Dependency and build reproducibility

- Build tools and libraries MUST be pinned to exact versions.
- The project-local `.venv` MUST be ignored by Git.
- Build outputs, coverage data, screenshots generated only for inspection, and local logs MUST be ignored unless intentionally promoted as test fixtures.
- A clean checkout MUST be buildable through documented commands without relying on undeclared global libraries.
- Native and embedded compilation flags MUST explicitly select C++17.
- Warnings from project code MUST be treated as errors in Native CI once the playable slice is complete.

## 11. Testing order

- Essential rule tests MUST be written while implementing the playable core.
- A complete playable game MUST precede million-tick stress testing, cross-platform hash gates, full CI hardening, and exhaustive hardware self-tests.
- Tests MUST remain proportional to the current milestone and MUST NOT block delivery of the first playable slice for future-platform infrastructure.
- No milestone passes merely because code compiles; each milestone has behavioral acceptance gates in `../plan.md`.
- Screenshot review is mandatory for browser milestones and MUST inspect both desktop and narrow viewport layouts.
- Hardware tests and results MUST NOT be simulated and reported as physical evidence.

## 12. Deferred features

The following MUST NOT be added to the current hackathon slice unless the plan is explicitly revised:

- OTA or remote firmware updates;
- persistent saved games;
- cloud services, authentication, databases, or telemetry upload;
- online AI inference;
- production security provisioning;
- battery-management firmware;
- reinforcement-learning training inside the game runtime.

Interfaces MAY reserve extension points, but speculative implementations are prohibited.

## 13. Repository documentation

- Every created folder and subfolder MUST contain the repository-standard `README.md` before code is added there.
- Every project file MUST include creation and last-modification metadata in a comment-compatible form.
- Important decisions MUST be documented before their implementation.
- New non-negotiable constraints MUST be added here and indexed by `docs/README.md`.
- User-owned uncommitted changes MUST NOT be staged or overwritten without explicit instruction.

## 14. Remote-server power safety

- Automation MUST NOT reboot, shut down, power off, halt, kexec, change init targets, trigger SysRq reboot, or cause any equivalent power transition on server `100.83.174.76` (`a-Default-string`).
- Automation MUST NOT stop or disable SSH, Tailscale, or host networking on that server.
- `sudo` does not authorize a power transition or removal of the server's power-safety guard.
- If a future training, driver, or package task requires a reboot, work MUST stop and the user must perform it outside Codex.

## 15. RL deployment boundary

- The first RL implementation targets Native training, evaluation, export, and optional Native gameplay inference.
- It MUST NOT introduce a network or cloud inference dependency into standalone gameplay.
- TorchScript and ONNX artifacts MUST NOT be represented as ESP32-compatible artifacts.
- ESP32 MUST retain the deterministic heuristic policy until a later documented decision defines and physically validates an embedded model runtime, quantization format, memory budget, and latency budget.
- Multi-GPU training MUST first reproduce a correct single-GPU baseline. The default four-V100 topology is one isolated training seed per GPU, not synchronous DDP.

## 16. China training-host dependency source

- Python dependencies on the approved V100 host MUST be downloaded through the Tsinghua PyPI mirror.
- The V100 training baseline MUST use PyTorch 2.6.0 with CUDA 12.4 user-space dependencies; CUDA 13 builds MUST NOT be installed for V100 training.
- Training MUST use physical GPU indices 1–4. Physical GPU 0 is a GTX 750 and MUST NOT be selected by any training or evaluation launcher.
- Per explicit operator direction, training MUST reuse `/home/a/minimind-venv`; automation MAY add only the missing pinned CataMaze build, test, logging, and editable-project packages to it.
- Automation MUST NOT create another training virtual environment or mutate the system Python, NVIDIA driver, or host CUDA toolkit.
