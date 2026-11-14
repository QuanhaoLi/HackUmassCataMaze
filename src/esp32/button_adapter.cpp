// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 11:43 EST
// Last Modified by: Codex
// Samples six active-low GPIOs and forwards portable system intents without touching spare pins.

#include "button_adapter.hpp"

#include <Arduino.h>

#include <cstddef>
#include <cstdint>

#include "hardware_config.hpp"

namespace catamaze::esp32 {

app::ButtonLevels ButtonAdapter::readReleasedLevels() {
  app::ButtonLevels released{};
  for (std::size_t index = 0U; index < kButtonPins.size(); ++index) {
    released[index] = digitalRead(kButtonPins[index]) == HIGH;
  }
  return released;
}

void ButtonAdapter::begin(std::uint32_t now_ms) {
  for (std::uint8_t pin : kButtonPins) pinMode(pin, INPUT_PULLUP);
  input_.begin(now_ms, readReleasedLevels());
}

bool ButtonAdapter::poll(std::uint32_t now_ms, app::ProductShell& product) {
  bool changed = false;
  const bool game_playing = product.snapshot().mode == app::ProductMode::Active &&
                            product.snapshot().system.mode == app::SystemMode::Playing;
  const app::ButtonEvents events = input_.poll(now_ms, readReleasedLevels(), game_playing);
  for (std::size_t index = 0U; index < events.count; ++index) {
    changed = product.handle(events.values[index], now_ms) || changed;
  }
  return changed;
}

}  // namespace catamaze::esp32
