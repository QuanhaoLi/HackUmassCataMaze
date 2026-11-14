// Created at: 2026-11-14 07:36 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:36 EST
// Last Modified by: Codex
// Declares deterministic six-button debounce, FIRE sampling, and CLEAR gesture interpretation.

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "catamaze/app/system_controller.hpp"

namespace catamaze::app {

enum class PhysicalButton : std::uint8_t {
  Up = 0,
  Down = 1,
  Left = 2,
  Right = 3,
  Fire = 4,
  Clear = 5,
};

inline constexpr std::size_t kPhysicalButtonCount = 6U;
using ButtonLevels = std::array<bool, kPhysicalButtonCount>;

struct ButtonEvents {
  std::array<SystemInput, kPhysicalButtonCount> values{};
  std::size_t count{0U};

  bool push(SystemInput input) noexcept;
};

class SixButtonInput {
 public:
  inline static constexpr std::uint32_t kDebounceMs = 20U;
  inline static constexpr std::uint32_t kClearLongPressMs = 800U;

  void begin(std::uint32_t now_ms, const ButtonLevels& released) noexcept;
  ButtonEvents poll(std::uint32_t now_ms, const ButtonLevels& released, bool game_playing) noexcept;

 private:
  struct State {
    bool raw_released{true};
    bool stable_released{true};
    std::uint32_t raw_changed_ms{0U};
    std::uint32_t stable_changed_ms{0U};
  };

  std::array<State, kPhysicalButtonCount> states_{};
  bool initialized_{false};
  bool clear_long_committed_{false};
};

}  // namespace catamaze::app
