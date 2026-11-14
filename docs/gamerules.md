<!--
Created at: 2026-11-13 23:37 EST
Created by: CataDragon
Last Modified at: 2026-11-14 06:39 EST
Last Modified by: Codex

本文档定义 CataMaze v1 的确定性游戏规则、状态转换、可观察信息与终局条件。
-->

# CataMaze v1 — Game Rules

CataMaze is a **standalone, single-player maze escape game** running on an ESP32-S3 handheld. The player searches for an exit while avoiding or fighting three AI enemies. The game advances at **one tick per second** during normal play. Each tick resolves one player action and one action per living AI.

## 1. Game Setup

| Parameter | Rule |
|---|---|
| Map | 50 × 50 cells |
| Player display vision | 9 × 5 cells, centered on the player |
| AI policy vision | 5 × 5 cells, centered on that AI |
| Gunshot hearing range | 7 × 7 cells (3 cells in every direction) |
| Enemies | 3: aggressive, cautious, explorer |
| HP | Starts at 5; maximum 5; no regeneration |
| Ammo | Starts at 3; maximum 3; restores 1 every 2 ticks |
| Damage | 1 HP per bullet hit |
| Input queue | 32 pending actions maximum |
| Duration | 2,000 ticks maximum |
| Sound output | Optional Mac speakers driven by best-effort USB Serial events |

The map uses `#` (wall), `.` (path), `S` (entrance marker), and `E` (single exit). Map edges are walls except at the exit. The player and three AI spawn on different reachable cells, never on `E`; spawning at `S` is not required.

The v1 implementation uses versioned generator `dfs-grid-v1`:

1. Fill the 50×50 map with walls. Logical maze cells are the 24×24 odd-coordinate cells where `x,y ∈ {1,3,...,47}`.
2. Starting at `(1,1)`, run an iterative depth-first backtracker. Candidate directions begin in `UP, RIGHT, DOWN, LEFT` order and are shuffled only by the repository-owned PCG32 generator initialized from an explicit 64-bit seed.
3. Mark `(1,1)` as `S`. Among reachable logical cells adjacent to an outer boundary, select the one with greatest shortest-path distance from `S`; break equal-distance ties by lower `y`, then lower `x`.
4. Open exactly one adjacent boundary cell as `E`. If several boundary sides touch the selected logical cell, choose `RIGHT, DOWN, LEFT, UP` in that order.
5. Place the player on `S`. Sort remaining walkable non-`E` cells by descending shortest-path distance from the player, then lower `y`, then lower `x`; assign the first three distinct cells to aggressive, cautious, and explorer respectively.

General rules do not require every future generator to spawn the player at `S`, but `dfs-grid-v1` does. Reusing the same generator version and seed must reproduce the same terrain, exit, and initial entity positions on every target.

## 2. Two OLED Screens

Both displays are **GME12864, 128 × 64, monochrome**. They show different information and must never reveal hidden game state.

### Screen 1 — Map

Shows **only the player's current 9 × 5 field of view**, not the full 50 × 50 maze:

- `@` — player, always at column 5 / row 3, the center of the 9×5 view.
- `#` — visible wall; `.` — visible path; `S` / `E` — entrance or exit when visible.
- `P` — visible AI enemy. Player projectiles and enemy projectiles are never drawn on the Map OLED.
- `?` — obscured cell, including cells hidden behind walls; outside the map counts as a wall.

Walls block line of sight, including diagonal views through a blocked corner. Enemies and terrain outside the current view must remain hidden. The map redraws after each tick. The player receives no projectile sprite, muzzle flash, trajectory line, or directional gunshot graphic; the intended horror feedback is audible gunfire followed by damage feedback and HP loss when a hit occurs.

The player-only view is 9×5. The 128×64 Map OLED renders nine 12×12 square tiles across five rows, with 10-pixel left/right margins and 2-pixel top/bottom margins. This intentionally gives the human player wider peripheral vision. It does not change movement distance, shooting range, map geometry, or any AI observation.

Every AI remains restricted to its own 5×5 observation. The player's extra left/right cells must never enter an AI policy input, recurrent state, action mask, reward feature, or 13×5×5 training tensor.

### Screen 2 — HUD

Displays these **five persistent fields only**:

```text
TICK        00125
HP          ♥ ♥ ♥ ♥ ♡
AMMO        ▮ ▮ □
QUEUE       07/32
POS         12,28
```

The HUD has no title row. All five labels begin at pixel `x=1`; all numeric values and icon groups begin at pixel `x=44`. Row origins are `y=3`, `15`, `27`, `39`, and `51`, keeping the right-hand content vertically aligned.

- `TICK` — completed world updates (0–2,000).
- `HP` — exactly five heart slots. Each remaining HP is one filled heart; each lost HP is one outline heart.
- `AMMO` — exactly three ammunition slots. Each available shot is one filled cartridge; each unavailable shot is one outline cartridge.
- `QUEUE` — actions still waiting / capacity (0–32).
- `POS` — player's `(x, y)` on the 50 × 50 map.

There is **no `STATUS` field**. The HUD refreshes after ticks and immediately when the queue changes. On victory, death, or timeout, an end message may replace the normal display.

## 3. Controls and Queue

There are **nine queued actions**: move up/down/left/right, shoot up/down/left/right, and wait. No diagonal moves or shots. Seven physical buttons produce them:

- A debounced direction press samples FIRE at that moment.
- If FIRE is already held, the direction enqueues a shot; otherwise it enqueues movement.
- FIRE pressed by itself has no action. Pressing FIRE after a direction event does not alter the queued action.
- WAIT enqueues one wait action.
- CLEAR immediately deletes all queued actions that have not begun execution.
- Default debounce is 20 ms. Holding a button never repeats; a new event requires a debounced release followed by another press.

- Inputs enter a **FIFO queue**; maximum length is 32.
- Each tick consumes **one** queued player action; if empty, the player waits.
- A full queue rejects new actions without overwriting previous ones.
- CLEAR deletes pending actions only, not the action already executing.
- Wall collisions, entity collisions, and ammo shortages are checked **when an action executes**, not when it is queued.

## 4. Tick Resolution and Movement

All four entities select actions from the **same tick-start state**. Each tick proceeds in this order:

1. Take the first queued player action (or wait); each living AI selects one action based on its own permitted observations. Invalid or unavailable AI actions become wait.
2. Resolve movement simultaneously. Walls, map boundaries, and cells occupied at tick start block entry. Two entities targeting the same cell, or trying to swap positions, both fail.
3. Advance existing bullets, spawn valid new shots, and calculate simultaneous damage.
4. Remove dead entities; restore ammo; update visited cells and in-game gunshot events.
5. Check end conditions, advance the tick, and refresh both screens.

Blocked moves still consume their action. All AIs follow the same movement, HP, and combat rules as the player. AI observations may contain legally visible projectile direction channels for deterministic avoidance and future model compatibility, while the human player's Map OLED intentionally omits every projectile.

## 5. Shooting, HP, and In-Game Sound

- Shooting uses **1 ammo**. If ammo is `0`, no bullet or gunshot event is created.
- New bullets spawn in the adjacent cell. Existing bullets advance **one cell per tick**, never through walls. A bullet disappears when it hits an entity, wall, or map edge.
- A new shot aimed into an adjacent wall or outside the map still consumes ammo and disappears immediately. A new shot whose adjacent cell contains an entity hits during that same tick.
- Bullets do not collide with other bullets. Opposing bullets may cross or share a cell; each continues until it hits an entity, wall, or map edge.
- Every hit deals **1 HP**. Multiple hits in one tick add together and are applied simultaneously. A bullet cannot hurt its original shooter; AI can hit other AI.
- Bullets remain in flight after their shooter dies. HP never regenerates.
- Ammo regenerates by **1 after every 2 eligible tick completions**, capped at 3. Shooting does not erase partial recharge progress.
- An actual shot creates a **game-world sound event** heard by entities within 3 cells in either axis, even through walls. An observer receives approximate direction, not the hidden shooter's identity or exact location.
- Projectile simulation is never rendered to the player. A successful own shot emits optional `PLAYER_SHOT` audio and changes the AMMO icon when the action executes. An enemy hit emits optional `PLAYER_DAMAGE` audio and changes one filled heart to an outline heart.

## 6. Optional Mac Audio — USB Serial Events

CataMaze has no onboard buzzer. The ESP32-S3 may emit a best-effort audio event over USB Serial, and an optional Mac companion plays the corresponding sound through the Mac speakers.

| Game event | Serial audio event |
|---|---|
| Player fires successfully | `PLAYER_SHOT` |
| Player takes damage | `PLAYER_DAMAGE` |
| Nearby enemy fires **within the player's 7 × 7 hearing area** | `ENEMY_SHOT_HEARD` |
| Player reaches exit alive | `PLAYER_VICTORY` |
| Player dies | `PLAYER_DEATH` |
| Input rejected / no ammo / timeout | No event |

Audio output rules:

- **Only player-observable events produce audio**; off-screen or out-of-range enemy shots must remain silent.
- Serial audio output does not create additional in-game sound events or affect AI hearing.
- Emit at most one highest-priority event per tick: **death/victory > damage > heard enemy shot > own shot**.
- Serial transmission must never block game ticks, buttons, OLED refreshes, or AI.
- If no Mac companion is connected, the game continues normally without sound and without replaying missed audio later.
- The complete protocol and failure semantics are defined in `audio.md`.

## 7. End Conditions

At the end of each tick, check in this order:

1. **Death:** player HP reaches 0.
2. **Victory:** player remains alive and is on `E`.
3. **Timeout:** 2,000 ticks have elapsed without escape.

Death overrides victory if both happen in the same tick. Eliminating all AI does not win the game. After any end condition, the game stops advancing.

## 8. Standalone Implementation

- The **ESP32-S3** owns the map, state, queue, tick loop, and both OLED renderers. No Mac, audio companion, or online server is required for play.
- Each AI sees only its own 5 × 5 view and permitted sound cues; no full-map access or opponents' private HP/ammo.
- With the same map, rule version, AI policy, seed, and input sequence, game outcomes should be reproducible. If saving is implemented, preserve the tick, all entities, bullets, ammo recovery, and pending queue.
- Network concurrency, API authentication, multi-session capacity, and database transactions from the earlier server-oriented draft are **out of scope** for this handheld version.
