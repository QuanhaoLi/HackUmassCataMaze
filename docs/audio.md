<!--
Created at: 2026-11-14 04:33 EST
Created by: Codex
Last Modified at: 2026-11-14 04:33 EST
Last Modified by: Codex

本文档冻结 CataMaze v1 的 USB Serial 音频事件协议、Mac 扬声器 companion 与断连语义。
-->

# CataMaze v1 — Optional Mac Audio

## 1. Product decision

CataMaze v1 has no physical buzzer or other onboard sound transducer. GPIO4 is released as an unassigned spare and production firmware must not configure or drive it.

The ESP32-S3 owns all game simulation and remains fully playable when no Mac is connected. Audio is an optional output adapter:

```text
Game/Application AudioEvent
          |
          v
ESP32 non-blocking USB Serial adapter
          |
          v
Mac audio companion -> Mac speakers
```

Disconnecting the Mac, closing the companion, or saturating Serial output makes the game silent. None of those conditions may pause, slow, reset, or otherwise change gameplay.

## 2. Canonical events

| Event | Meaning | Priority |
|---|---|---:|
| `PLAYER_DEATH` | Player HP reached zero | 5 |
| `PLAYER_VICTORY` | Player reached `E` alive | 5 |
| `PLAYER_DAMAGE` | One or more HP were removed this tick | 4 |
| `ENEMY_SHOT_HEARD` | Enemy fired inside the player's 7×7 hearing area | 3 |
| `PLAYER_SHOT` | A queued player shot successfully consumed ammo | 2 |

Input rejection, no-ammo actions, timeout, idle ticks, ammo regeneration, unseen enemy shots, and out-of-range enemy shots produce no audio event.

If several events occur in one tick, output only one event at the highest priority. Equal-priority events collapse to one notification. Audio arbitration is deterministic and must not feed back into the Game Core.

## 3. Serial wire format

USB Serial runs at 115,200 baud. Each event is one ASCII line with a fixed discriminator followed by compact JSON:

```text
CATAMAZE_AUDIO {"schema":"catamaze.audio.v1","seq":42,"tick":125,"event":"PLAYER_DAMAGE"}
```

Contract:

- Prefix is exactly `CATAMAZE_AUDIO `, including the trailing space.
- Line terminator is `\n`.
- `schema` is exactly `catamaze.audio.v1`.
- `seq` is an unsigned 32-bit monotonically increasing sequence number; wrap is allowed.
- `tick` is the completed game tick associated with the event.
- `event` is one of the five canonical strings above.
- A complete line must be at most 128 bytes.
- Audio lines must not contain entity IDs, coordinates, directions, HP, ammo, map data, or other hidden state.
- Ordinary diagnostics must never use the `CATAMAZE_AUDIO ` prefix.

USB transport has no retry layer. `seq` supports duplicate suppression and gap diagnostics; gaps are accepted and never trigger replay.

## 4. ESP32 transport behavior

The Serial adapter is best-effort and non-blocking:

1. Select the single highest-priority audio event at the end of a tick.
2. Format it into a fixed-size stack buffer.
3. Check Serial write capacity.
4. Write the complete line only when capacity is sufficient; otherwise increment a dropped-event diagnostic and discard it.

The adapter must not wait for a Mac, call an unbounded flush, allocate in the tick path, retain an offline backlog, or replay old audio after reconnect. Game hashes and outcomes must be identical with the adapter enabled, disabled, connected, disconnected, or saturated.

## 5. Mac audio companion

The companion is a separate Native process. It:

- discovers the USB-to-UART device by metadata rather than a hard-coded `/dev/cu.*` path;
- opens the device at 115,200 baud;
- reconnects with bounded backoff after disconnect;
- ignores all lines without the exact prefix;
- validates schema, size, sequence, tick, and event before playback;
- drops malformed, duplicate, stale, or unknown events;
- preloads sound assets before listening;
- plays through the current Mac default output device;
- never sends commands back to the game in v1.

The target latency from receipt of a complete Serial line to playback start is under 80 ms p95. The Native browser simulator may synthesize the same canonical events with Web Audio, using the same names and priority order.

## 6. Failure semantics

| Failure | Required behavior |
|---|---|
| Mac disconnected | Game continues; event is discarded |
| Companion closed | Game continues; event is discarded |
| Serial capacity insufficient | Drop current event; never block |
| Malformed line on Mac | Ignore and log bounded diagnostic |
| Duplicate `seq` | Ignore duplicate sound |
| Sequence gap | Continue from newest event; never request replay |
| Audio asset missing | Companion logs error; game remains unaffected |

## 7. Verification gates

- Every canonical event has a stable serialization golden test.
- Same-tick priority selection is exhaustive.
- No serialized audio line exceeds 128 bytes or contains forbidden fields.
- Full/disconnected Serial output returns immediately and records a drop.
- Connected and disconnected 100,000-tick runs produce identical state hashes.
- The Mac parser rejects malformed prefixes, JSON, schemas, event names, duplicates, and stale sequences.
- Reconnect does not replay old events.
- GPIO4 is absent from production pin initialization and writes.
- Physical acceptance measures end-to-end playback latency and validates all five sounds without changing game timing.
