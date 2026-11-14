// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:50 EST
// Last Modified by: Codex
// Declares allocation-free debounced input translation into shared application commands.

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "catamaze/app/application.hpp"

namespace catamaze::esp32 {

class ButtonAdapter {
 public:
  void begin(std::uint32_t now_ms);
  bool poll(std::uint32_t now_ms, app::Application& application);

 private:
  struct State {
    bool raw_high{true};
    bool stable_high{true};
    std::uint32_t raw_changed_ms{0U};
    std::uint32_t stable_changed_ms{0U};
  };

  bool handlePress(std::size_t index, std::uint32_t now_ms, app::Application& application);
  std::array<State, 7> states_{};
};

}  // namespace catamaze::esp32
