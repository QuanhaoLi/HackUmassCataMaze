// Created at: 2026-11-14 02:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:34 EST
// Last Modified by: Codex
// Declares authoritative player Map and fixed-field HUD framebuffer rendering.

#pragma once

#include "catamaze/core/engine.hpp"
#include "catamaze/render/framebuffer.hpp"

namespace catamaze::render {

class Renderer {
 public:
  static Framebuffer mapScreen(const core::Observation& observation) noexcept;
  static Framebuffer hudScreen(const core::WorldState& state) noexcept;
};

}  // namespace catamaze::render
