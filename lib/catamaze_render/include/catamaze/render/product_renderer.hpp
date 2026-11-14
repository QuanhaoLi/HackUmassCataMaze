// Created at: 2026-11-14 11:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 11:34 EST
// Last Modified by: Codex
// Declares exact dual-eye Companion Idle, active system, and inactivity-prompt framebuffers.

#pragma once

#include "catamaze/app/product_shell.hpp"
#include "catamaze/render/system_renderer.hpp"

namespace catamaze::render {

class ProductRenderer {
 public:
  static DualFrames screens(const app::ProductSnapshot& product,
                            const core::PlayerObservation& observation,
                            const core::WorldState& world) noexcept;
};

}  // namespace catamaze::render
