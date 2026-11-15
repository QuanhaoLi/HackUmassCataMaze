// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-15 02:30 EST
// Last Modified by: Codex
// Freezes verified ESP32-S3 pins, bus settings, debounce, and timing without GPIO4 or GPIO10.

#pragma once

#include <array>
#include <cstddef>
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
inline constexpr std::uint8_t kClearPin = 11U;
inline constexpr std::uint8_t kSpareGpio4 = 4U;
inline constexpr std::uint8_t kSpareGpio10 = 10U;

inline constexpr std::array<std::uint8_t, 6> kButtonPins{kUpPin,    kDownPin, kLeftPin,
                                                         kRightPin, kFirePin, kClearPin};

inline constexpr std::uint32_t kDebounceMs = 20U;
inline constexpr std::uint32_t kTickIntervalMs = 600U;
inline constexpr std::uint32_t kSerialBaud = 115200U;
inline constexpr std::uint64_t kDefaultSeed = 0x000000000134fd5aULL;

constexpr bool buttonPinsAreUnique() noexcept {
  for (std::size_t first = 0U; first < kButtonPins.size(); ++first) {
    for (std::size_t second = first + 1U; second < kButtonPins.size(); ++second) {
      if (kButtonPins[first] == kButtonPins[second]) return false;
    }
  }
  return true;
}

constexpr bool buttonPinsExcludeSpareAndDisplayPins() noexcept {
  for (std::uint8_t pin : kButtonPins) {
    if (pin == kSpareGpio4 || pin == kSpareGpio10 || pin == kMapSdaPin || pin == kMapSclPin ||
        pin == kHudSdaPin || pin == kHudSclPin) {
      return false;
    }
  }
  return true;
}

static_assert(buttonPinsAreUnique(), "button GPIO assignments must be unique");
static_assert(buttonPinsExcludeSpareAndDisplayPins(),
              "button GPIOs must exclude GPIO4, GPIO10, and both I2C buses");

}  // namespace catamaze::esp32
