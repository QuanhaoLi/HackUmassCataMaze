// Created at: 2026-11-14 07:36 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:36 EST
// Last Modified by: Codex
// Implements allocation-free wrap-safe physical input interpretation shared by hardware adapters.

#include "catamaze/app/six_button_input.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace catamaze::app {
namespace {

constexpr std::size_t buttonIndex(PhysicalButton button) noexcept {
  return static_cast<std::size_t>(button);
}

constexpr std::array<SystemInput, 4> kDirectionInputs{SystemInput::Up, SystemInput::Down,
                                                      SystemInput::Left, SystemInput::Right};
constexpr std::array<SystemInput, 4> kShootingInputs{
    SystemInput::ShootUp, SystemInput::ShootDown, SystemInput::ShootLeft, SystemInput::ShootRight};

std::uint32_t elapsed(std::uint32_t now_ms, std::uint32_t since_ms) noexcept {
  return now_ms - since_ms;
}

}  // namespace

bool ButtonEvents::push(SystemInput input) noexcept {
  if (count >= values.size()) return false;
  values[count++] = input;
  return true;
}

void SixButtonInput::begin(std::uint32_t now_ms, const ButtonLevels& released) noexcept {
  for (std::size_t index = 0U; index < states_.size(); ++index) {
    states_[index] = State{released[index], released[index], now_ms, now_ms};
  }
  clear_long_committed_ = !released[buttonIndex(PhysicalButton::Clear)];
  initialized_ = true;
}

ButtonEvents SixButtonInput::poll(std::uint32_t now_ms, const ButtonLevels& released,
                                  bool game_playing) noexcept {
  ButtonEvents events{};
  if (!initialized_) {
    begin(now_ms, released);
    return events;
  }

  for (std::size_t index = 0U; index < states_.size(); ++index) {
    State& state = states_[index];
    if (released[index] != state.raw_released) {
      state.raw_released = released[index];
      state.raw_changed_ms = now_ms;
    }
    if (state.stable_released == state.raw_released ||
        elapsed(now_ms, state.raw_changed_ms) < kDebounceMs) {
      continue;
    }

    state.stable_released = state.raw_released;
    state.stable_changed_ms = now_ms;
    if (index == buttonIndex(PhysicalButton::Clear)) {
      if (state.stable_released) {
        if (!clear_long_committed_) events.push(SystemInput::ClearShort);
        clear_long_committed_ = false;
      } else {
        clear_long_committed_ = false;
      }
      continue;
    }
    if (state.stable_released) continue;

    if (index < kDirectionInputs.size()) {
      const State& fire = states_[buttonIndex(PhysicalButton::Fire)];
      const bool fire_was_held =
          !fire.stable_released && elapsed(now_ms, fire.stable_changed_ms) > 0U;
      events.push(game_playing && fire_was_held ? kShootingInputs[index] : kDirectionInputs[index]);
    } else if (index == buttonIndex(PhysicalButton::Fire)) {
      events.push(SystemInput::Fire);
    }
  }

  const State& clear = states_[buttonIndex(PhysicalButton::Clear)];
  if (!clear.stable_released && !clear.raw_released && !clear_long_committed_ &&
      elapsed(now_ms, clear.stable_changed_ms) >= kClearLongPressMs) {
    events.push(SystemInput::ClearLong);
    clear_long_committed_ = true;
  }
  return events;
}

}  // namespace catamaze::app
