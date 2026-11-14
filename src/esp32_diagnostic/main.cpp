// Created at: 2026-11-14 04:44 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:58 EST
// Last Modified by: Codex
// Reports bounded ESP32-S3, PSRAM, dual-I2C, and idle-button evidence before product upload.

#include <Arduino.h>
#include <Wire.h>

#include <array>
#include <cstddef>
#include <cstdint>

namespace {

constexpr std::uint32_t kSerialBaud = 115200U;
constexpr std::uint32_t kI2cFrequency = 100000U;
constexpr std::uint8_t kExpectedDisplayAddress = 0x3cU;
constexpr std::uint32_t kExpectedFlashBytes = 16U * 1024U * 1024U;
constexpr std::uint32_t kExpectedPsramBytes = 8U * 1024U * 1024U;
constexpr std::array<std::uint8_t, 7> kButtonPins{5U, 6U, 7U, 15U, 16U, 10U, 11U};

TwoWire hud_wire(1U);

struct I2cScan {
  std::uint8_t count{0U};
  std::uint8_t first_address{0U};
  std::uint8_t errors{0U};
};

I2cScan scanBus(TwoWire& bus) {
  I2cScan scan{};
  for (std::uint8_t address = 1U; address < 127U; ++address) {
    bus.beginTransmission(address);
    const std::uint8_t result = bus.endTransmission();
    if (result == 0U) {
      if (scan.count == 0U) scan.first_address = address;
      ++scan.count;
    } else if (result != 2U) {
      ++scan.errors;
    }
  }
  return scan;
}

std::uint8_t releasedButtonMask() {
  std::uint8_t mask = 0U;
  for (std::size_t index = 0; index < kButtonPins.size(); ++index) {
    if (digitalRead(kButtonPins[index]) == HIGH) {
      mask = static_cast<std::uint8_t>(mask | (1U << index));
    }
  }
  return mask;
}

void printButtons(std::uint8_t mask) {
  Serial.printf(
      "CATAMAZE_BUTTONS {\"schema\":\"catamaze.buttons.v1\","
      "\"released_mask\":%u,\"all_released\":%s}\n",
      static_cast<unsigned>(mask), mask == 0x7fU ? "true" : "false");
}

}  // namespace

void setup() {
  Serial.begin(kSerialBaud);
  const std::uint32_t serial_deadline = millis() + 2000U;
  while (!Serial && static_cast<std::int32_t>(serial_deadline - millis()) > 0) {
    delay(10U);
  }

  for (std::uint8_t pin : kButtonPins) pinMode(pin, INPUT_PULLUP);

  const bool map_bus_started = Wire.begin(8, 9, kI2cFrequency);
  const bool hud_bus_started = hud_wire.begin(18, 17, kI2cFrequency);
  const bool map_sda_high = digitalRead(8) == HIGH;
  const bool map_scl_high = digitalRead(9) == HIGH;
  const bool hud_sda_high = digitalRead(18) == HIGH;
  const bool hud_scl_high = digitalRead(17) == HIGH;
  const I2cScan map_scan = scanBus(Wire);
  const I2cScan hud_scan = scanBus(hud_wire);

  const std::uint32_t flash_bytes = ESP.getFlashChipSize();
  const bool psram_found = psramFound();
  const std::uint32_t psram_bytes = ESP.getPsramSize();
  const bool pass = flash_bytes == kExpectedFlashBytes && psram_found &&
                    psram_bytes == kExpectedPsramBytes && map_bus_started && hud_bus_started &&
                    map_scan.count == 1U && map_scan.first_address == kExpectedDisplayAddress &&
                    hud_scan.count == 1U && hud_scan.first_address == kExpectedDisplayAddress;

  Serial.printf(
      "CATAMAZE_DIAG {\"schema\":\"catamaze.diag.v1\","
      "\"chip\":\"%s\",\"revision\":%u,\"cpu_mhz\":%u,"
      "\"flash_bytes\":%lu,\"psram_found\":%s,\"psram_bytes\":%lu,"
      "\"map_bus_started\":%s,\"map_i2c_count\":%u,"
      "\"map_i2c_address\":%u,\"map_i2c_errors\":%u,"
      "\"map_sda_high\":%s,\"map_scl_high\":%s,"
      "\"hud_bus_started\":%s,\"hud_i2c_count\":%u,"
      "\"hud_i2c_address\":%u,\"hud_i2c_errors\":%u,"
      "\"hud_sda_high\":%s,\"hud_scl_high\":%s,"
      "\"gpio4_configured\":false,\"pass\":%s}\n",
      ESP.getChipModel(), static_cast<unsigned>(ESP.getChipRevision()),
      static_cast<unsigned>(ESP.getCpuFreqMHz()), static_cast<unsigned long>(flash_bytes),
      psram_found ? "true" : "false", static_cast<unsigned long>(psram_bytes),
      map_bus_started ? "true" : "false", static_cast<unsigned>(map_scan.count),
      static_cast<unsigned>(map_scan.first_address), static_cast<unsigned>(map_scan.errors),
      map_sda_high ? "true" : "false", map_scl_high ? "true" : "false",
      hud_bus_started ? "true" : "false", static_cast<unsigned>(hud_scan.count),
      static_cast<unsigned>(hud_scan.first_address), static_cast<unsigned>(hud_scan.errors),
      hud_sda_high ? "true" : "false", hud_scl_high ? "true" : "false", pass ? "true" : "false");
  printButtons(releasedButtonMask());
}

void loop() {
  static std::uint8_t previous_mask = releasedButtonMask();
  static std::uint32_t last_heartbeat_ms = 0U;
  const std::uint8_t current_mask = releasedButtonMask();
  const std::uint32_t now = millis();
  if (current_mask != previous_mask || now - last_heartbeat_ms >= 1000U) {
    previous_mask = current_mask;
    last_heartbeat_ms = now;
    printButtons(current_mask);
  }
}
