<!--
Created at: 2026-11-14 06:57 EST
Created by: Codex
Last Modified at: 2026-11-14 07:34 EST
Last Modified by: Codex

本文档定义 CataMaze 双屏复古 Home、Setup、Pause 和 Result 导航体验及六键输入合同。
-->

# CataMaze Home and Navigation

## 1. Purpose

CataMaze boots into a small handheld launcher rather than directly into gameplay. The launcher lets the player start a run, choose a reviewed map preset, inspect system status, and understand the controls without changing the deterministic Game Core or the AI/RL observation contract.

The experience should feel like a compact late-1990s/early-2000s dual-screen handheld: crisp one-bit graphics, strong selection bars, immediate button feedback, minimal animation, and a clear split between the screen that the player acts on and the screen that explains the current focus.

## 2. Research basis

- Nintendo DS used one screen for status/context and the other for selectable launcher panels, establishing a clear dual-screen division of responsibility. [Nintendo DS official manual](https://csassets.nintendo.com/noaext/image/private/t_KA_PDF/ds_english)
- Playdate pauses the game before presenting system actions and supports restart/options without mixing them into the running game UI. It also recommends testing at real physical size rather than trusting a scaled simulator. [Playdate official design guidance](https://sdk.play.date/1.12.0/Designing%20for%20Playdate.html)
- Analogue Pocket uses a restrained vertical launcher with direct labels such as Play, Library, Tools, and Settings. [Analogue official overview](https://www.analogue.co/press/item/2-Analogue%20Pocket%20-%20Transparent%20Limited%20Editions/%2AAnalogue%20Pocket%20Transparent%20Limited%20Editions%20Overview.pdf)

Applied principles:

- Immediate inverse-video feedback on button press.
- One dominant task per screen.
- The path into and out of a mode is symmetric.
- No input lockout during decorative transitions.
- Common actions stay at the top level; destructive or rare actions require one deeper confirmation.
- The dual screens cooperate rather than mirror the same information.

## 3. Frozen six-button contract

There are six physical buttons: `UP`, `DOWN`, `LEFT`, `RIGHT`, `FIRE`, and `CLEAR`. There is no physical WAIT button.

| Button | Home / Setup / menus | Game Session |
|---|---|---|
| `UP` / `DOWN` | Move focus vertically | Move up / down |
| `LEFT` / `RIGHT` | Change the focused value | Move left / right |
| `FIRE` | Confirm / enter | Hold first, then press a direction to shoot |
| `CLEAR` short press | Return one level | Clear pending Action Queue entries |
| `CLEAR` long press, 0.8 s | Return directly to Home | Pause and open Pause Menu |

An empty Action Queue still produces the domain `Wait Action` automatically. AI fallback and RL action index 8 also remain `Wait Action`; only the physical WAIT button and manual WAIT enqueue path are removed.

### 3.1 CLEAR gesture state machine

```text
IDLE
  └─ press ─> PRESSED
                 ├─ release before 800 ms ─> SHORT_COMMITTED ─> IDLE
                 └─ reach 800 ms ──────────> LONG_COMMITTED
                                                   └─ release ─> IDLE
```

Rules:

- Press feedback appears immediately when CLEAR goes down.
- A long press commits exactly once when held duration reaches 800 ms.
- Releasing after a long commit must not emit a short press.
- In Game Session, long press freezes the world before opening Pause Menu and preserves the Action Queue byte-for-byte.
- In Game Session, short press clears only pending actions; it does not pause.
- Long press never repeats while held.
- The same interpretation is used by Native keyboard/pointer input and the future ESP32 button adapter.

## 4. System state model

```text
BOOT
  -> HOME
       -> SETUP
       -> SYSTEM
       -> ABOUT
       -> GAME
            -> PAUSE
                 -> GAME          (Resume)
                 -> GAME          (Restart, same preset and seed)
                 -> CONFIRM_HOME
                       -> HOME
            -> RESULT
                 -> GAME          (Replay, same seed)
                 -> GAME          (New Run, new seed)
                 -> HOME
```

Only `GAME` advances ticks. Home, Setup, System, About, Pause, confirmation, and Result do not advance AI, bullets, ammo recharge, or timeout.

Boot always enters Home. There is no implicit auto-resume in v1.

## 5. Dual-screen responsibility

### Left OLED — action and focus

The left OLED owns:

- the current menu list;
- the inverse selection bar;
- the editable field focus;
- the 9×5 player map during gameplay;
- the frozen 9×5 map while paused;
- the final map/result illustration after a run.

### Right OLED — context and preview

The right OLED owns:

- details about the selected Home item;
- current Setup values and their consequences;
- map-size preview and dynamic tick budget;
- hardware/software status summaries;
- Pause Menu choices;
- Result statistics;
- the normal icon HUD during gameplay.

The screens must not duplicate the same menu. Focus lives on one screen; explanation lives on the other.

## 6. Retro visual system

- One-bit only: black background, white foreground, no simulated grayscale except sparse deliberate dithering.
- Five-by-seven product font with uppercase labels.
- Selected rows use a solid white bar with black text.
- A one-pixel outer frame may identify a system panel; game map tiles have no per-cell grid.
- Decorative corners, small arrows, and checker/dither fills may evoke cartridge-era UI but must never compete with text.
- Navigation changes respond immediately; optional transitions are at most 100 ms and non-blocking.
- No bounce, scrolling inertia, translucent effects, or animation that requires additional full-screen I²C writes.
- The browser must paint the exact two framebuffers used by the OLED drivers.

## 7. Screen designs

### 7.1 Boot

Left:

```text
  CATAMAZE
  [maze mark]
```

Right:

```text
SYSTEM CHECK
CORE   OK
MAP    OK
HUD    OK
```

Boot display is skippable as soon as checks complete. It must not delay input with a fixed splash timer.

### 7.2 Home

Left:

```text
CATAMAZE

> PLAY
  MAP SETUP
  SYSTEM
  ABOUT
```

Right when `PLAY` is focused:

```text
NEW RUN

MAP    30x30
LIMIT  1200
PLAYER 9x5
AI     5x5
```

Right when `MAP SETUP` is focused:

```text
MAP PRESET

4 SIZES
SQUARE MAPS
FIRE TO EDIT
```

### 7.3 Setup

Left:

```text
MAP SETUP

> SIZE   30x30
  START GAME
```

- `LEFT` / `RIGHT` cycles the size while `SIZE` is focused.
- `FIRE` on `START GAME` confirms the Setup and begins a New Run.
- CLEAR short returns to Home without discarding the currently confirmed preset.
- CLEAR long returns directly to Home and also does not mutate the confirmed preset.

Right:

```text
MEDIUM

SIZE   30x30
LIMIT  1200
ENEMY  3
AI FOV 5x5
```

The right screen also draws a centered proportional square preview. It previews scale only; it must not expose the generated maze before a run begins.

### 7.4 System

Left:

```text
SYSTEM

> HARDWARE
  SOFTWARE
  CONTROLS
```

Right shows bounded information for the selected row, such as dual `0x3C` display status, firmware/rules version, or the six-button legend. System is read-only in v1.

### 7.5 About

Left shows the CataMaze mark and version. Right states that the player has a 9×5 display advantage while each AI remains limited to 5×5. CLEAR short returns Home.

### 7.6 Game

Left is the existing 9×5 map. Right is the existing five-row HUD. Home chrome and menu labels disappear completely.

### 7.7 Pause Menu

Left keeps the exact last rendered map framebuffer frozen. Right:

```text
PAUSED

> RESUME
  RESTART
  HOME
```

- `RESUME` preserves and continues the Action Queue.
- `RESTART` creates a fresh state with the same map preset and seed.
- `HOME` opens `CONFIRM_HOME` because it abandons the current Game Session.
- CLEAR short is equivalent to Resume.
- CLEAR long while already paused has no additional effect.

### 7.8 Confirm Home

Right:

```text
LEAVE RUN?

> CANCEL
  LEAVE
```

Default focus is `CANCEL`. CLEAR short also cancels. Confirmation is required only because leaving destroys the unsaved run.

### 7.9 Result

Left preserves the final player map. Right:

```text
VICTORY
TICK   00481

> REPLAY
  NEW RUN
  HOME
```

Death and timeout use the same structure with their respective title.

## 8. Map presets

v1 supports exactly four reviewed square presets:

| Canonical name | Size | Tick budget | Intended experience |
|---|---:|---:|---|
| `TINY` | 12×12 | 480 | Very short run and hardware demo |
| `SMALL` | 20×20 | 800 | Quick run |
| `MEDIUM` | 30×30 | 1,200 | Recommended default |
| `ORIGINAL` | 50×50 | 2,000 | Long-form current game |

The formula is `max_ticks = map_size × 40`.

Map sizes cannot be edited as arbitrary numbers. The active map is always square, at most 50×50, and uses the same maximum fixed storage. Coordinates outside the active square are not part of the world.

Changing the pending preset never mutates a current Game Session. A New Run snapshots the confirmed preset and seed into its state hash. Restart retains both. New Run from Result generates a new seed.

The wider player display remains 9×5 for all presets. Every AI observation remains 5×5.

## 9. Native implementation contract

The first implementation target was Mac Native. It provides:

- a portable system/navigation controller independent of HTTP and Arduino;
- a versioned `GameConfig` containing map preset, active size, tick budget, and seed;
- exact left/right system framebuffers;
- browser input that distinguishes CLEAR short and 800 ms long press without emitting both;
- a versioned Native snapshot describing system mode and confirmed/pending Setup;
- no physical WAIT control or manual WAIT API entry;
- continued automatic Wait Action behavior for empty queues and AI/RL;
- completed Native screenshots, interaction tests, sanitizers, randomized testing, and coverage evidence before embedded migration.

## 10. Verification gates

- CLEAR release after long press never clears the Action Queue.
- Pause freezes tick, AI, bullets, ammo recharge, and timeout.
- Resume preserves state hash and queue.
- Restart preserves preset and seed but resets world state.
- Home abandonment requires confirmation and ends the Game Session.
- All four presets generate connected deterministic mazes with one exit and four distinct spawns.
- Tick budgets are exactly 480, 800, 1,200, and 2,000.
- AI/RL spatial tensors remain `[13,5,5]`; action count remains 9 with Wait Action at index 8.
- Player Map remains 9×5 for every preset.
- Home/Setup/Pause/Result dual-screen golden framebuffer tests pass.
- Desktop and true 390px browser screenshots are visually inspected.
- Normal, ASan, UBSan, randomized, and coverage gates pass before requesting ESP approval.

## 11. Explicit non-goals

- No arbitrary map dimensions.
- No rectangular world maps.
- No mid-session map resizing.
- No saved-game resume in v1.
- No touch, pointer drag, scrolling momentum, or animated carousel.
- No change to AI view size, action schema, persona model, or RL tensor dimensions.

## 12. Approved ESP32 migration contract

The user explicitly approved careful ESP32 migration after the Native gates passed on 2026-11-14. Embedded work must proceed in this order:

1. Implement a portable, allocation-free six-button interpreter and prove 20 ms debounce, no-repeat presses, FIRE-before-direction sampling, 800 ms CLEAR long commit, and post-long short suppression with Native unit tests.
2. Remove GPIO10 from every product and diagnostic button array. GPIO10 and GPIO4 remain unconfigured spares.
3. Compose the existing `SystemController` and `SystemRenderer` in ESP32 firmware; the two physical OLEDs display the same left/right framebuffers accepted on Native.
4. Compile both diagnostic and product environments without uploading.
5. Auto-detect exactly one approved serial device and run read-only chip, Flash, and PSRAM preflight.
6. Upload diagnostic firmware only, then require 16 MB Flash, initialized 8 MB PSRAM, one `0x3C` display on each independent I²C bus, all four I²C lines HIGH, six released inputs, and explicit `gpio4_configured=false` / `gpio10_configured=false` evidence.
7. Only after the diagnostic passes, upload the product image and require a bounded boot record proving Home mode, 30×30 default, six inputs, both displays, memory, and spare-GPIO status.
8. Keep M5 open until the user physically verifies all six press/release paths, FIRE sampling, CLEAR short, CLEAR long, and a complete game.

No Flash erase is authorized. A compile, upload acknowledgement, illuminated RGB LED, or idle button mask alone is not sufficient physical gameplay evidence.
