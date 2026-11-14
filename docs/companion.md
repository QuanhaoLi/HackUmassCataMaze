<!--
Created at: 2026-11-14 11:27 EST
Created by: Codex
Last Modified at: 2026-11-14 11:27 EST
Last Modified by: Codex

本文档定义 CataMaze 双屏桌宠模式、唤醒语义、无操作确认与跨平台验收合同。
-->

# CataMaze Companion Idle

## 1. Product decision

CataMaze is both a handheld maze game and a desktop companion. The normal resting state is Companion Idle: the left OLED is the left eye and the right OLED is the right eye. Game Core state does not advance and no Game Session exists while resting.

The companion shell surrounds the existing Home and Game Session. It does not enter Game Core, AI observations, policy tensors, rewards, state hashes, map seeds, or action schemas.

## 2. State flow

```text
BOOT
  -> COMPANION_IDLE
       -- any button / consumed --> HOME
       -- 30 s menu inactivity --> COMPANION_IDLE

PLAYING or PAUSED
  -- 30 s no button activity --> INACTIVITY_PROMPT
       -> CONTINUE --> exact prior Game Session state
       -> SLEEP --> abandon session --> COMPANION_IDLE
```

Rules:

- The Wake button intent is consumed. It must not also select PLAY, move focus, enqueue movement, shoot, or clear a queue.
- Home, Setup, System, About, and Result return directly to Companion Idle after 30 seconds without physical/browser button activity because no live action is at risk.
- Playing is paused before Inactivity Prompt appears. Tick, AI, bullets, ammo recharge, timeout, and Action Queue remain frozen.
- An already paused Game Session remains paused when Continue is chosen.
- Inactivity Prompt defaults to Continue. Sleep requires explicit selection and FIRE confirmation.
- Inactivity Prompt never auto-selects Sleep; it may remain visible indefinitely.
- CLEAR short cancels Inactivity Prompt and returns to the prior active/paused state. CLEAR long has no destructive shortcut there.
- CLEAR long from Home enters Companion Idle immediately.
- The 30-second timer measures button intent activity, not ticks, rendering, HTTP polls, audio, or AI work.
- Unsigned millisecond arithmetic must remain correct across timer wraparound.

## 3. Eye language

Both screens are one face, not two unrelated icons. All eyes use authoritative 128×64 one-bit framebuffers and remain legible at physical size.

Reviewed frames:

| Frame | Left OLED | Right OLED | Feeling |
|---|---|---|---|
| `NEUTRAL` | open eye, centered pupil | mirrored open eye | calm |
| `LOOK_LEFT` | pupil left | pupil left | attentive |
| `LOOK_RIGHT` | pupil right | pupil right | attentive |
| `BLINK_HALF` | half lid | half lid | transition |
| `BLINK_CLOSED` | closed curve | closed curve | blink |
| `HAPPY` | upward closed crescent | mirrored crescent | pleased |
| `CURIOUS` | narrower eye | wider eye | curious asymmetry |
| `SLEEPY` | low half lid | low half lid | drowsy |
| `SURPRISED` | round wide eye | round wide eye | startled |

The v1 animation is a deterministic 24-second loop so Native and ESP32 produce the same frame for the same elapsed idle time. Blinks use bounded 100–200 ms transition frames; longer expressions remain for 1.5–4.5 seconds. Rendering must never block input or a game tick.

## 4. Timing and display budget

- Companion evaluation uses explicit adapter-provided monotonic milliseconds; the shell never reads an OS or Arduino clock directly.
- Native evaluates shell time at least every 100 ms even when its developer game clock is paused.
- ESP32 evaluates shell time every non-blocking loop.
- A framebuffer transfer may be chunked, but a newer companion frame replaces an older pending frame rather than forming an unbounded animation queue.
- Entering Home or Inactivity Prompt replaces both companion eye frames immediately.
- Reduced-motion browser preferences do not change authoritative OLED frames; the animation already uses sparse discrete changes with no flashing.

## 5. Native acceptance

- Boot snapshot is `IDLE`, not Home.
- Every one of the six intents wakes to Home and is consumed.
- The second deliberate FIRE starts Play.
- Menu inactivity transitions at exactly 30,000 ms.
- Playing inactivity freezes the state hash and Action Queue before showing the prompt.
- Continue restores the exact prior active/paused state; Sleep abandons it and shows eyes.
- Every reviewed expression has deterministic non-empty left/right golden framebuffer coverage.
- Browser automation verifies Wake, inactivity, Continue, Sleep, form-input isolation, desktop layout, and true 390 px layout.
- Native normal, ASan, UBSan, randomized, and coverage gates remain green.

## 6. ESP32 and model boundary

- ESP32 must reuse the accepted portable companion shell and exact companion framebuffers.
- The currently known GPIO fault blocks companion product upload until all six raw HIGH→LOW→HIGH paths pass diagnostic firmware without resets.
- ESP-DL policy inference runs only during Game Session ticks. Companion Idle and its eye animation never allocate model tensors or advance recurrent hidden state.
- A failed or unavailable model keeps the deterministic heuristic fallback; it must not prevent Companion Idle, Wake, Home, or display operation.
- Physical acceptance requires both eyes to be visually inspected across the full expression loop, all six Wake paths, the 30-second prompt, model/fallback diagnostics, and return to Companion Idle.
