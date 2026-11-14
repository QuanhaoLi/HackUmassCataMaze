// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:42 EST
// Last Modified by: Codex
// Declares GPIO sampling around the portable six-button input interpreter.

#pragma once

#include <cstdint>

#include "catamaze/app/six_button_input.hpp"
#include "catamaze/app/system_controller.hpp"

namespace catamaze::esp32 {

class ButtonAdapter {
 public:
  void begin(std::uint32_t now_ms);
  bool poll(std::uint32_t now_ms, app::SystemController& system);

 private:
  static app::ButtonLevels readReleasedLevels();
  app::SixButtonInput input_{};
};

}  // namespace catamaze::esp32
