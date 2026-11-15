<!--
Created at: 2026-11-15 06:30 EST
Created by: Codex
Last Modified at: 2026-11-15 06:48 EST
Last Modified by: Codex

本文档定义无需后端的 CataMaze Cloudflare Pages 双屏演示器及其发布验收合同。
-->

# CataMaze Static Showcase

## 1. Purpose

The public showcase lets a judge or visitor experience the two-screen CataMaze product from a phone or desktop without installing a toolchain, connecting an ESP32, or running the Native server. It is a self-contained presentation and interaction surface, not a replacement implementation of the released product runtime.

The first production hostname is `https://hackumass-catamaze.pages.dev`.

## 2. Product boundary

| Concern | Public showcase | Native / ESP product |
|---|---|---|
| Runtime | Browser-local JavaScript demonstration | Shared pure C++17 Game Core |
| Hosting | Static Cloudflare Pages assets | Local process / offline firmware |
| Displays | Canvas rendering in the reviewed OLED visual language | Exact shared 1-bit framebuffers |
| AI | Deterministic local showcase heuristics | Released Resident Policy with automatic heuristic fallback |
| Determinism claim | Stable within one browser release and seed | Authoritative state hashes and cross-target contract |
| Network after load | None | Native loopback only / ESP fully offline |

The page must visibly label its runtime as `BROWSER SIM`. Product copy must not imply that ESP-DL inference, exact C++ state hashes, or physical hardware are executing in the visitor's browser.

## 3. Entry and state flow

```text
LOAD -> COMPANION_IDLE
          -- any of six buttons, consumed --> HOME
HOME -- FIRE on PLAY --> GAME
HOME -- arrows --> MAP SETUP / SYSTEM / ABOUT
GAME -- CLEAR hold 800 ms --> PAUSE
GAME -- 30 s inactivity --> INACTIVITY PROMPT
PAUSE / PROMPT --> GAME or COMPANION_IDLE
```

- Every load begins in Companion Idle with two coordinated animated eyes.
- The Wake input is consumed and cannot also navigate, start, move, shoot, or clear.
- The first Home focus is PLAY; a second deliberate FIRE starts the default 30×30 demonstration.
- Setup exposes 12×12, 20×20, 30×30, and 50×50 presets.
- An empty game queue produces Wait automatically on each 600 ms tick.
- FIRE alone does not enqueue an action. Holding FIRE before a direction enqueues a shot in that direction.
- CLEAR short clears pending game actions. CLEAR held for 800 ms pauses once without also clearing the queue.
- The local page may be reloaded to reset all state; no persistence is required.

## 4. Dual-screen experience

Both canvases have a 128×64 logical resolution and render with nearest-neighbor scaling.

- Companion Idle: each OLED is one eye; both form one face.
- Home and menus: left OLED owns focus and choice; right OLED owns context and preview.
- Game: left OLED shows a nine-by-five player view using square cells; right OLED shows tick, five HP hearts, three ammo cartridges, queue depth, and position.
- Projectiles are never drawn. Shooting, nearby enemy fire, damage, death, and victory are communicated through synchronized display changes and optional Web Audio only.
- The surrounding page may use restrained depth and responsive motion, but the OLED pixels remain one-bit mint-on-black and animation stays sparse.

## 5. Mobile and accessibility contract

- The page fits 320 CSS pixels and wider without horizontal scrolling.
- Portrait stacks the two screens; landscape and desktop place them side by side when space permits.
- The D-pad mirrors physical direction and the FIRE/CLEAR controls keep stable positions.
- Pointer-down gives immediate visual feedback. Pointer capture makes release and cancellation safe when a finger leaves a button.
- Keyboard parity uses arrows, Space for FIRE, and C for CLEAR.
- Status changes use a polite live region; controls have explicit accessible names; canvas fallback text identifies each display.
- Safe-area insets protect controls on notched phones.
- Reduced-motion users receive static/cross-fade feedback while retaining state clarity.

## 6. Local simulation scope

The demonstration owns a bounded local state machine, seedable maze, player, three deterministic heuristic enemies, FIFO action queue, ammo recovery, line-of-sight shooting, collision/damage, win/death/timeout, and a 600 ms clock. This scope exists to make the public artifact meaningfully playable.

It does not reimplement training tensors, recurrent hidden state, ESP-DL quantization, C++ serialization, product state hashes, USB Serial, GPIO, I²C, or hardware diagnostics.

## 7. Release gates

A public revision passes only when all of the following are true:

1. JavaScript parses without errors and the static document has no missing local assets.
2. A localhost HTTP probe returns the page, CSS, JavaScript, and security headers where applicable.
3. Real Chrome verifies Idle on first paint, consumed Wake, second-FIRE Play, movement, FIRE-plus-direction ammo consumption, CLEAR short, and CLEAR long.
4. Real Chrome captures and reviews a desktop layout and a 390×844 mobile layout.
5. Both layouts have zero horizontal overflow and all six controls meet the minimum hit-target size.
6. The Cloudflare deployment returns HTTPS 200 for `/`, `/app.css`, and `/app.js`, and the page contains the expected release marker.

Deployment does not constitute Native, ESP32, model, or physical-display acceptance.

## 8. Initial production evidence

The `2026.11.15.1` release passed on 2026-11-15:

- Cloudflare Pages production project `hackumass-catamaze`, deployment `d14c3c6b-0b3e-46c2-bac2-fd6471cc6491`, source commit `379202e7bbdbf3c0b7f977abed9f8dee817fbd36`;
- production hostname `https://hackumass-catamaze.pages.dev` returned HTTPS 200 for the document, stylesheet, and JavaScript;
- response headers enforced CSP `connect-src 'none'`, clickjacking denial, MIME-sniffing denial, no referrer, same-origin opener isolation, and disabled camera, microphone, geolocation, payment, motion-sensor, and USB permissions;
- local and production Chrome acceptance passed at 1440×1050 and 390×844 CSS viewports;
- production interaction evidence covered Idle boot, consumed Wake, second-FIRE Play, movement queueing, CLEAR short, FIRE-before-direction shooting, wall-shot ammo consumption, CLEAR 800 ms pause without queue clearing, inactivity prompt, and Continue;
- both widths had zero horizontal overflow; OLED widths were about 498.6 and 309.5 CSS pixels respectively, and the smallest mobile control measured about 51.2 CSS pixels;
- reviewed Idle and Playing screenshots covered both desktop and mobile layouts; the Playing HUD visibly changed one filled ammo cartridge to an outline after a shot;
- GitHub Native C++ quality run `43710358856` passed for the source commit.

The `2026.11.15.2` copy revision removes the decorative `HANDHELD + COMPANION` eyebrow from the public header and changes the visible product subtitle from `dual-OLED sim` to `online demo`. The `BROWSER SIM` runtime badge remains so the page continues to state its non-authoritative runtime boundary clearly.
