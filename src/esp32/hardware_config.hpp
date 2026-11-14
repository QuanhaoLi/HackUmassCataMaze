// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:50 EST
// Last Modified by: Codex
// Freezes verified ESP32-S3 pins, bus settings, debounce, and timing without assigning GPIO4.

#pragma once

#include <array>
#include <cstdint>

namespace catamaze::esp32 {

inline constexpr std::uint8_t kMapSdaPin = 8U;
inline constexpr std::uint8_t kMapSclPin = 9U;
inline constexpr std::uint8_t kHudSdaPin = 18U;
inline constexpr std::uint8_t kHudSclPin = 17U;
inline constexpr std::uint8_t kDisplayAddress = 0x3cU;
inline constexpr std::uint32_t kI2cFrequency = 100000U;

inline constexpr std::uint8_t kUpPin = 5U;
inline constexpr std::uint8_t kDownPin = 6U;
inline constexpr std::uint8_t kLeftPin = 7U;
inline constexpr std::uint8_t kRightPin = 15U;
inline constexpr std::uint8_t kFirePin = 16U;
inline constexpr std::uint8_t kWaitPin = 10U;
inline constexpr std::uint8_t kClearPin = 11U;
inline constexpr std::uint8_t kReleasedSpareGpio = 4U;

inline constexpr std::array<std::uint8_t, 7> kButtonPins{kUpPin,   kDownPin, kLeftPin, kRightPin,
                                                         kFirePin, kWaitPin, kClearPin};

inline constexpr std::uint32_t kDebounceMs = 20U;
inline constexpr std::uint32_t kTickIntervalMs = 1000U;
inline constexpr std::uint32_t kSerialBaud = 115200U;
inline constexpr std::uint64_t kDefaultSeed = 0x000000000134fd5aULL;

constexpr bool buttonPinsExcludeReleasedSpare() noexcept {
  for (std::uint8_t pin : kButtonPins) {
    if (pin == kReleasedSpareGpio) return false;
  }
  return true;
}

static_assert(buttonPinsExcludeReleasedSpare(), "GPIO4 must remain an unassigned spare");

}  // namespace catamaze::esp32
