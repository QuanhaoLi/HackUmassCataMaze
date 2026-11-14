// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:50 EST
// Last Modified by: Codex
// Implements 20 ms debounce, strict FIRE-before-direction sampling, no repeat, WAIT, and CLEAR.

#include "button_adapter.hpp"

#include <Arduino.h>

#include <array>
#include <cstddef>
#include <cstdint>

#include "catamaze/core/types.hpp"
#include "hardware_config.hpp"

namespace catamaze::esp32 {
namespace {

constexpr std::size_t kFireIndex = 4U;
constexpr std::size_t kWaitIndex = 5U;
constexpr std::size_t kClearIndex = 6U;
constexpr std::array<core::Direction, 4> kDirectionByIndex{
    core::Direction::Up, core::Direction::Down, core::Direction::Left, core::Direction::Right};

}  // namespace

void ButtonAdapter::begin(std::uint32_t now_ms) {
  for (std::size_t index = 0; index < kButtonPins.size(); ++index) {
    pinMode(kButtonPins[index], INPUT_PULLUP);
    const bool high = digitalRead(kButtonPins[index]) == HIGH;
    states_[index] = State{high, high, now_ms, now_ms};
  }
}

bool ButtonAdapter::handlePress(std::size_t index, std::uint32_t now_ms,
                                app::Application& application) {
  if (index < kDirectionByIndex.size()) {
    const bool fire_was_held =
        !states_[kFireIndex].stable_high && states_[kFireIndex].stable_changed_ms < now_ms;
    const core::Action action = fire_was_held ? core::shootAction(kDirectionByIndex[index])
                                              : core::moveAction(kDirectionByIndex[index]);
    return application.enqueuePlayerAction(action);
  }
  if (index == kWaitIndex) return application.enqueuePlayerAction(core::Action::Wait);
  if (index == kClearIndex) {
    application.clearPlayerQueue();
    return true;
  }
  return false;
}

bool ButtonAdapter::poll(std::uint32_t now_ms, app::Application& application) {
  bool changed = false;
  for (std::size_t index = 0; index < kButtonPins.size(); ++index) {
    State& state = states_[index];
    const bool raw_high = digitalRead(kButtonPins[index]) == HIGH;
    if (raw_high != state.raw_high) {
      state.raw_high = raw_high;
      state.raw_changed_ms = now_ms;
    }
    if (state.stable_high != state.raw_high && now_ms - state.raw_changed_ms >= kDebounceMs) {
      state.stable_high = state.raw_high;
      state.stable_changed_ms = now_ms;
      if (!state.stable_high) changed = handlePress(index, now_ms, application) || changed;
    }
  }
  return changed;
}

}  // namespace catamaze::esp32
