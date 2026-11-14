// Created at: 2026-11-14 07:09 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:09 EST
// Last Modified by: Codex
// Declares exact dual-OLED rendering for launcher, setup, gameplay, pause, and result modes.

#pragma once

#include "catamaze/app/system_controller.hpp"
#include "catamaze/render/framebuffer.hpp"

namespace catamaze::render {

struct DualFrames {
  Framebuffer left{};
  Framebuffer right{};
};

class SystemRenderer {
 public:
  static DualFrames screens(const app::SystemSnapshot& system,
                            const core::PlayerObservation& observation,
                            const core::WorldState& world) noexcept;
};

}  // namespace catamaze::render
