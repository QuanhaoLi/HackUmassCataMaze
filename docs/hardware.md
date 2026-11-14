<!--
Created at: 2026-11-13 23:50 EST
Created by: CataDragon
Last Modified at: 2026-11-14 04:33 EST
Last Modified by: Codex

本文档记录 CataMaze v1 当前硬件清单、已验证的双屏接线、显示职责与驱动约束。
-->

# CataMaze v1 — Hardware

## 1. Verified Controller

- Controller: ESP32-S3 development board with 16 MB flash and 8 MB OPI PSRAM (N16R8-class configuration).
- Development connection: USB-C through the board's USB-to-UART bridge; serial console runs at 115,200 baud.
- Framework used for hardware validation: Arduino ESP32 Core 3.3.12.
- Both displays run at 3.3 V and use 100 kHz I²C.
- GPIO33–GPIO37 are reserved by the board's OPI PSRAM and must not be assigned to displays or other peripherals.
- Avoid GPIO19/GPIO20 for project peripherals because they are the ESP32-S3 native USB pair; GPIO43/GPIO44 are the console UART. The current generic ESP32-S3 Arduino board profile assigns GPIO48 to its built-in RGB LED, so do not reuse it without first verifying the exact development-board schematic.

## 2. Dual OLED Assignment and Wiring

Both displays are GME12864 128×64 white monochrome four-pin I²C OLEDs. Both validated modules respond at address `0x3C`, so they use the ESP32-S3's two independent hardware I²C controllers.

| Role | Content | Arduino bus | SDA | SCL | Address | Power |
|---|---|---|---:|---:|---:|---|
| Game screen / Map | Player's 5×5 local terrain and visible enemies; never projectile sprites | `Wire` / I²C controller 0 | GPIO8 | GPIO9 | `0x3C` | 3V3 + GND |
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

## 4. Button Inputs and Remaining Hardware

Seven momentary push buttons provide the physical game controls. Each button uses exactly two electrical connections: one button terminal goes directly to its assigned GPIO and the other goes directly to `GND`.

| Button | Game action | GPIO | Current hardware status |
|---|---|---:|---|
| ↑ | Move up | GPIO5 | Connected; press/release and debounce verified |
| ↓ | Move down | GPIO6 | Connected; press/release and debounce verified |
| ← | Move left | GPIO7 | Connected; idle HIGH verified; final press/release test pending |
| → | Move right | GPIO15 | Planned; not connected or tested |
| FIRE | Hold before pressing a direction to enqueue a directional shot; FIRE alone has no action | GPIO16 | Planned; not connected or tested |
| WAIT | Enqueue wait | GPIO10 | Planned; not connected or tested |
| CLEAR | Clear pending input queue | GPIO11 | Planned; not connected or tested |

GPIO17 and GPIO18 must not be used for buttons because they are the HUD display's SCL and SDA lines. Pressing a GND-connected button on either pin would short an active I²C signal to ground.

Configure every button input with its internal pull-up:

```cpp
constexpr int BUTTON_PINS[] = {5, 6, 7, 15, 16, 10, 11};

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
- FIRE alone emits no game action. WAIT emits one wait action. CLEAR bypasses the FIFO and immediately clears actions that have not begun execution.

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

- The game-screen renderer owns only the player-observable 5×5 terrain and enemy view described in `gamerules.md`. It never renders a projectile, muzzle flash, trajectory, or direction indicator and refreshes after every game tick.
- The HUD renderer owns only `TICK`, five filled/outline HP hearts, three filled/outline ammo cartridges, `QUEUE`, and `POS`. It refreshes after every tick and immediately when the input queue changes.
- Keep independent framebuffers and renderer objects. A render or bus failure on one screen must not redirect its content to the other or expose hidden game state.
