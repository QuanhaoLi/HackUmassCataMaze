// Created at: 2026-11-14 02:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:37 EST
// Last Modified by: Codex
// Declares authoritative player Map and fixed-field HUD framebuffer rendering.

#pragma once

#include <array>

#include "catamaze/core/engine.hpp"
#include "catamaze/render/framebuffer.hpp"

namespace catamaze::render {

class Renderer {
 public:
  inline static constexpr std::int16_t kHudLabelX = 1;
  inline static constexpr std::int16_t kHudValueX = 44;
  inline static constexpr std::array<std::int16_t, 5> kHudRowY{3, 15, 27, 39, 51};

  static Framebuffer mapScreen(const core::Observation& observation) noexcept;
  static Framebuffer hudScreen(const core::WorldState& state) noexcept;
};

}  // namespace catamaze::render
