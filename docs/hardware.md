<!--
Created at: 2026-11-13 23:50 EST
Created by: CataDragon
Last Modified at: 2026-11-14 07:34 EST
Last Modified by: Codex

本文档记录 CataMaze v1 当前硬件清单、已验证的双屏接线、显示职责与驱动约束。
-->

# CataMaze v1 — Hardware

## 1. Verified Controller

- Controller: ESP32-S3 revision v0.2 development board with 16 MB Quad Flash and 8 MB embedded OPI PSRAM (N16R8-class configuration), confirmed by read-only esptool probing on 2026-11-14.
- Development connection: onboard CH343 USB-UART bridge (USB VID:PID `1A86:55D3`, active-board serial `5CE6032515`); upload, diagnostics, and optional Mac audio run at 115,200 baud with dynamically discovered port paths. Product operation does not depend on native USB CDC.
- Framework used for hardware validation: Arduino ESP32 Core 3.3.12.
- Both displays run at 3.3 V and use 100 kHz I²C.
- GPIO33–GPIO37 are reserved by the board's OPI PSRAM and must not be assigned to displays or other peripherals.
- Avoid GPIO19/GPIO20 for project peripherals because they are the ESP32-S3 native USB pair; GPIO43/GPIO44 are the console UART. The current generic ESP32-S3 Arduino board profile assigns GPIO48 to its built-in RGB LED, so do not reuse it without first verifying the exact development-board schematic.

Read-only preflight evidence from the active replacement board:

| Property | Observed value |
|---|---|
| Chip | ESP32-S3 QFN56 revision v0.2 |
| CPU/features | Dual core + LP core, 240 MHz, Wi-Fi, BT 5 LE |
| Development transport | CH343 USB-UART bridge, `1A86:55D3`, serial `5CE6032515` |
| ESP32 MAC | `84:fc:e6:53:bf:94` |
| Flash JEDEC | Manufacturer `0x68`, device `0x4018` |
| Flash | 16 MB, Quad data lines, 3.3 V |
| PSRAM | 8 MB embedded PSRAM, 3.3 V |

The PlatformIO base board `esp32-s3-devkitc-1` defaults to an 8 MB/no-PSRAM variant, so the project configuration must explicitly override it to 16 MB Flash and `qio_opi` memory type. Runtime diagnostic firmware must still assert the observed capacities before the product firmware is accepted.

The active board passed a fresh diagnostic with exactly one `0x3C` device on each controller, all four I²C lines HIGH, zero bus errors, correct Flash/PSRAM, the six active button inputs plus then-reserved GPIO10 released, and GPIO4 unconfigured.

An early product build exposed loop-task stack pressure during maze generation. The accepted build stores BFS/candidate cell references as 16-bit indices, defers `Application` construction into `setup()`, and provisions a 48 KiB loop-task stack. Physical boot evidence reports `loop_stack_high_water_words=26188`, both displays present, and `ready=true` without rebooting.

## 2. Dual OLED Assignment and Wiring

Both displays are GME12864 128×64 white monochrome four-pin I²C OLEDs. Both validated modules respond at address `0x3C`, so they use the ESP32-S3's two independent hardware I²C controllers.

| Role | Content | Arduino bus | SDA | SCL | Address | Power |
|---|---|---|---:|---:|---:|---|
| Game screen / Map | Player's 9×5 local terrain and visible enemies; 12×12 square tiles; never projectile sprites | `Wire` / I²C controller 0 | GPIO8 | GPIO9 | `0x3C` | 3V3 + GND |
| Data screen / HUD | `TICK`, five heart slots, three ammo slots, `QUEUE`, and `POS` | `Wire2` / I²C controller 1 | GPIO18 | GPIO17 | `0x3C` | 3V3 + GND |

### Physical connections

Game screen:

| OLED pin | ESP32-S3 pin |
|---|---|
| `VCC` | `3V3` |
| `GND` | `GND` |
| `SDA` | `GPIO8` |
| `SCL` | `GPIO9` |

HUD screen:

| OLED pin | ESP32-S3 pin |
|---|---|
| `VCC` | `3V3` |
| `GND` | `GND` |
| `SDA` | `GPIO18` |
| `SCL` | `GPIO17` |

Do not connect OLED `VCC` to `GND`. An unpowered module can hold both I²C lines low and make the display appear dead. Before powering the system, verify all four labels on each module rather than relying on connector position or wire color.

Do not electrically join the two SDA/SCL pairs. The buses are independent even though both screens use address `0x3C`. The two displays may share the board's `3V3` and `GND` rails.

## 3. Validation Record

The final wiring above was tested on the physical ESP32-S3 and both physical OLED modules:

- Both buses idled high on SDA and SCL.
- Each bus exposed exactly one I²C device at `0x3C`.
- Both displays accepted the SSD1306/SSD1315-compatible initialization sequence.
- Both displays passed black, all-pixels-on, checkerboard, border/cross, and vertical-bar patterns.
- Each display completed approximately 1,081 I²C transactions with zero reported errors during the validation run.

Validation used a standalone Arduino diagnostic sketch named `Dual_GME12864_Test`. It is a hardware test artifact, not the production game renderer.

## 4. Six-button input

Six momentary push buttons provide the physical controls. Each button uses exactly two electrical connections: one button terminal goes directly to its assigned GPIO and the other goes directly to `GND`.

| Button | Game action | GPIO | Current hardware status |
|---|---|---:|---|
| ↑ | Move up | GPIO5 | Connected; press/release and debounce verified |
| ↓ | Move down | GPIO6 | Connected; press/release and debounce verified |
| ← | Move left | GPIO7 | Connected; idle HIGH verified; final press/release test pending |
| → | Move right | GPIO15 | Planned; not connected or tested |
| FIRE | Hold before pressing a direction to enqueue a directional shot; FIRE alone has no action | GPIO16 | Planned; not connected or tested |
| CLEAR | Short: back/clear queue; long 0.8 s: Home/pause menu | GPIO11 | Planned; not connected or tested |

GPIO17 and GPIO18 must not be used for buttons because they are the HUD display's SCL and SDA lines. Pressing a GND-connected button on either pin would short an active I²C signal to ground.

Configure every button input with its internal pull-up:

```cpp
constexpr int BUTTON_PINS[] = {5, 6, 7, 15, 16, 11};

void initButtons() {
  for (int pin : BUTTON_PINS) {
    pinMode(pin, INPUT_PULLUP);
  }
}
```

The electrical and logical contract is:

- Released: `HIGH`.
- Pressed: `LOW`.
- No external pull-down resistor is used. A GPIO-to-GND pull-down conflicts with `INPUT_PULLUP` and makes the button appear permanently pressed.
- On a four-pin tactile switch, connect GPIO and GND to different electrical contact groups. Verify continuity rather than relying only on the switch's physical orientation across the breadboard center channel.
- Debounce each button for 20 ms. Emit one press event only after the state remains LOW for the full debounce interval; do not enqueue another action until a debounced release occurs.
- Sample FIRE only when a debounced direction press event is emitted. FIRE must already be held to convert that direction into a shot; pressing FIRE afterward does not modify the queued movement.
- FIRE alone emits no game action. There is no physical WAIT button; empty queue produces Wait Action automatically.
- CLEAR short press clears pending actions only on release. CLEAR long press commits at 800 ms and suppresses the later short release event.
- GPIO10 is `UNASSIGNED_SPARE` and must not be initialized as a button.

The currently deployed/pre-Home ESP32 image contains the former seven-button mapping. The user approved migration on 2026-11-14; it remains historical evidence until a fresh six-button diagnostic and product boot pass. The new diagnostic and product images must both leave GPIO10 and GPIO4 unconfigured.

Current prototype scope: only GPIO5, GPIO6, and GPIO7 have buttons physically installed. GPIO5 and GPIO6 each passed a complete HIGH → LOW → HIGH test with exactly one debounced press count and no duplicate events during the observation period. GPIO7 is not yet fully validated.

- Prototyping: ELEGOO Upgraded Electronics Fun Kit (breadboard, jumper wires, buttons).
- Development power: USB-C. Both OLED modules are powered from the board's 3.3 V rail.

## 5. Optional Mac Audio and Released GPIO4

The production product has no physical buzzer. Remove or disconnect the buzzer, transistor, base resistors, and flyback diode from the game hardware.

- GPIO4 is `UNASSIGNED_SPARE` and has no production connection.
- Firmware must not call `pinMode`, `digitalWrite`, `analogWrite`, `tone`, or another peripheral allocator for GPIO4.
- Historical buzzer validation remains available in Git history but is not a current product requirement.
- Player-observable audio events are emitted best-effort over the existing 115,200-baud USB Serial connection.
- A Mac companion may play those events through the Mac speakers.
- Disconnecting the Mac makes the game silent without affecting gameplay.
- The wire protocol and non-blocking failure behavior are defined in `audio.md`.

## 6. Arduino Display Driver Method

### 6.1 Create two hardware I²C buses

Use controller 0 for the game screen and controller 1 for the HUD. Arduino's `begin()` argument order is `SDA, SCL, frequency`:

```cpp
#include <Wire.h>

TwoWire Wire2(1);

void initDisplayBuses() {
  Wire.begin(8, 9, 100000);       // Game screen: SDA8, SCL9
  Wire2.begin(18, 17, 100000);    // HUD screen: SDA18, SCL17
}
```

Never call the HUD bus as `Wire2.begin(17, 18, ...)`; the physical HUD wiring is explicitly **SDA18 / SCL17**.

### 6.2 Bind each renderer to its own bus

The display objects must retain separate `TwoWire` references. Sharing the same `0x3C` address is safe only because the screens are on different controllers. For example, with Adafruit SSD1306:

```cpp
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

Adafruit_SSD1306 mapDisplay(128, 64, &Wire, -1, 100000UL, 100000UL);
Adafruit_SSD1306 hudDisplay(128, 64, &Wire2, -1, 100000UL, 100000UL);

bool initDisplays() {
  initDisplayBuses();

  // periphBegin=false preserves the explicit GPIO assignments above.
  bool mapOK = mapDisplay.begin(SSD1306_SWITCHCAPVCC, 0x3C, true, false);
  bool hudOK = hudDisplay.begin(SSD1306_SWITCHCAPVCC, 0x3C, true, false);
  return mapOK && hudOK;
}
```

If another library is used, it must likewise accept a bus instance per display. Do not use a global singleton driver that silently routes both screens through `Wire`.

### 6.3 Direct SSD1306/SSD1315-compatible writes

The validated low-level driver uses these conventions:

- I²C address: `0x3C` on each bus.
- Control byte `0x00`: following bytes are commands.
- Control byte `0x40`: following bytes are display RAM data.
- Geometry: 128 columns × 8 pages, with 8 vertical pixels per page.
- Production column offset: `0`. Offset `2` was exercised only as an SH1106 compatibility diagnostic.
- Write the framebuffer in small chunks (16 bytes was validated) and check every `endTransmission()` result.
- Keep the bus at the validated 100 kHz until a separate 400 kHz electrical and stress test passes.

At startup, scan each bus independently and require exactly one device at `0x3C`. Treat any other scan result, or idle-low SDA/SCL, as a wiring or power fault; do not continue rendering.

## 7. Rendering Responsibilities

- The game-screen renderer owns only the player-observable 9×5 terrain and enemy view described in `gamerules.md`. It uses 12×12 square tiles with 10-pixel horizontal and 2-pixel vertical margins, never renders a projectile, and refreshes after every game tick.
- The HUD renderer owns only `TICK`, five filled/outline HP hearts, three filled/outline ammo cartridges, `QUEUE`, and `POS`. It refreshes after every tick and immediately when the input queue changes.
- Keep independent framebuffers and renderer objects. A render or bus failure on one screen must not redirect its content to the other or expose hidden game state.
