// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 11:43 EST
// Last Modified by: Codex
// Declares GPIO sampling around the portable six-button input interpreter.

#pragma once

#include <cstdint>

#include "catamaze/app/product_shell.hpp"
#include "catamaze/app/six_button_input.hpp"

namespace catamaze::esp32 {

class ButtonAdapter {
 public:
  void begin(std::uint32_t now_ms);
  bool poll(std::uint32_t now_ms, app::ProductShell& product);

 private:
  static app::ButtonLevels readReleasedLevels();
  app::SixButtonInput input_{};
};

}  // namespace catamaze::esp32
