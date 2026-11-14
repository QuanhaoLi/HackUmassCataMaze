<!--
Created at: 2026-11-13 23:50 EST
Created by: CataDragon
Last Modified at: 2026-11-14 00:16 EST
Last Modified by: Codex

本文档记录 CataMaze v1 当前硬件清单、显示与输入设备，以及尚待验证的接线约束。
-->

# CataMaze v1 — Hardware

- Controller: ESP32-S3 development board (dual USB-C).
- Displays: Two GME12864 128×64 white monochrome OLEDs (4-pin I²C).
  - Map screen: Local maze view, player, enemies, projectiles.
  - HUD screen: TICK, HP, AMMO, QUEUE, POS.
- Input: Push buttons for movement and shooting.
- Audio: Active buzzer for short on/off game sound effects; GPIO, trigger polarity, and voltage requirements not yet verified.
- Prototyping: ELEGOO Upgraded Electronics Fun Kit (breadboard, jumper wires, buttons).
- Power: USB-C during development; OLEDs powered from 3.3 V.
Wiring: Each display needs VCC, GND, SDA, and SCL. If both OLEDs have the same I²C address, use separate I²C buses. GPIO assignments and final wiring are not yet verified.
