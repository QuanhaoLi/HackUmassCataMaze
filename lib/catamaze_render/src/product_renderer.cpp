// Created at: 2026-11-14 11:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 11:34 EST
// Last Modified by: Codex
// Implements expressive one-bit eyes and a session-preserving inactivity confirmation screen.

#include "catamaze/render/product_renderer.hpp"

#include <cstdint>

#include "catamaze/render/renderer.hpp"

namespace catamaze::render {
namespace {

std::int16_t absolute(std::int16_t value) noexcept {
  return value < 0 ? static_cast<std::int16_t>(-value) : value;
}

void fillCircle(Framebuffer& frame, std::int16_t center_x, std::int16_t center_y,
                std::int16_t radius, bool on) noexcept {
  const std::int32_t squared_radius = static_cast<std::int32_t>(radius) * radius;
  for (std::int16_t y = static_cast<std::int16_t>(-radius); y <= radius; ++y) {
    for (std::int16_t x = static_cast<std::int16_t>(-radius); x <= radius; ++x) {
      if (static_cast<std::int32_t>(x) * x + static_cast<std::int32_t>(y) * y <= squared_radius) {
        frame.setPixel(static_cast<std::int16_t>(center_x + x),
                       static_cast<std::int16_t>(center_y + y), on);
      }
    }
  }
}

void drawHighlight(Framebuffer& frame, std::int16_t pupil_x, std::int16_t pupil_y) noexcept {
  fillCircle(frame, static_cast<std::int16_t>(pupil_x - 4), static_cast<std::int16_t>(pupil_y - 4),
             3, true);
}

void drawOpenEye(Framebuffer& frame, std::int16_t gaze_x, std::int16_t vertical_cover,
                 bool wide) noexcept {
  const std::int16_t radius_y = wide ? 25 : 21;
  const std::int16_t maximum_half_width = wide ? 53 : 57;
  for (std::int16_t y = static_cast<std::int16_t>(-radius_y); y <= radius_y; ++y) {
    const std::int32_t squared = static_cast<std::int32_t>(absolute(y)) * absolute(y);
    const std::int16_t half_width = static_cast<std::int16_t>(
        maximum_half_width - squared * maximum_half_width / (radius_y * radius_y));
    if (half_width > 0) {
      frame.fillRect(static_cast<std::int16_t>(64 - half_width), static_cast<std::int16_t>(32 + y),
                     static_cast<std::int16_t>(half_width * 2 + 1), 1);
    }
  }
  const std::int16_t pupil_x = static_cast<std::int16_t>(64 + gaze_x);
  fillCircle(frame, pupil_x, 32, wide ? 15 : 13, false);
  drawHighlight(frame, pupil_x, 32);
  if (vertical_cover > 0) {
    frame.fillRect(0, 0, Framebuffer::kWidth, static_cast<std::int16_t>(32 + vertical_cover),
                   false);
    frame.fillRect(12, static_cast<std::int16_t>(31 + vertical_cover), 104, 2);
  }
}

void drawClosedCurve(Framebuffer& frame, bool happy) noexcept {
  for (std::int16_t x = -45; x <= 45; ++x) {
    const std::int32_t squared = static_cast<std::int32_t>(x) * x;
    const std::int16_t y = happy ? static_cast<std::int16_t>(42 - (2025 - squared) / 180)
                                 : static_cast<std::int16_t>(31 + (2025 - squared) / 420);
    frame.setPixel(static_cast<std::int16_t>(64 + x), y);
    frame.setPixel(static_cast<std::int16_t>(64 + x), static_cast<std::int16_t>(y + 1));
    frame.setPixel(static_cast<std::int16_t>(64 + x), static_cast<std::int16_t>(y + 2));
  }
}

void drawSurprised(Framebuffer& frame) noexcept {
  fillCircle(frame, 64, 32, 27, true);
  fillCircle(frame, 64, 32, 14, false);
  drawHighlight(frame, 64, 32);
}

Framebuffer eyeFrame(app::CompanionFrame companion, bool right_eye) noexcept {
  Framebuffer frame;
  frame.clear();
  switch (companion) {
    case app::CompanionFrame::Neutral:
      drawOpenEye(frame, 0, 0, false);
      break;
    case app::CompanionFrame::LookLeft:
      drawOpenEye(frame, -13, 0, false);
      break;
    case app::CompanionFrame::BlinkHalf:
      drawOpenEye(frame, 0, 7, false);
      break;
    case app::CompanionFrame::BlinkClosed:
      drawClosedCurve(frame, false);
      break;
    case app::CompanionFrame::LookRight:
      drawOpenEye(frame, 13, 0, false);
      break;
    case app::CompanionFrame::Happy:
      drawClosedCurve(frame, true);
      break;
    case app::CompanionFrame::Curious:
      drawOpenEye(frame, right_eye ? -3 : 3, right_eye ? 0 : 8, right_eye);
      break;
    case app::CompanionFrame::Sleepy:
      drawOpenEye(frame, right_eye ? -5 : 5, 10, false);
      break;
    case app::CompanionFrame::Surprised:
      drawSurprised(frame);
      break;
  }
  return frame;
}

void selectedRow(Framebuffer& frame, std::int16_t y, const char* text, bool selected) noexcept {
  if (selected) {
    frame.fillRect(2, static_cast<std::int16_t>(y - 1), 124, 9);
    frame.drawText(7, y, text, false);
  } else {
    frame.drawText(7, y, text);
  }
}

Framebuffer inactivityPrompt(const app::ProductSnapshot& product) noexcept {
  Framebuffer frame;
  frame.clear();
  frame.drawText(4, 2, "STILL THERE");
  frame.fillRect(3, 11, 122, 1);
  frame.drawText(4, 18, "NO INPUT 30S");
  selectedRow(frame, 35, "CONTINUE", product.prompt_focus == 0U);
  selectedRow(frame, 50, "SLEEP", product.prompt_focus == 1U);
  return frame;
}

}  // namespace

DualFrames ProductRenderer::screens(const app::ProductSnapshot& product,
                                    const core::PlayerObservation& observation,
                                    const core::WorldState& world) noexcept {
  switch (product.mode) {
    case app::ProductMode::CompanionIdle:
      return DualFrames{eyeFrame(product.companion_frame, false),
                        eyeFrame(product.companion_frame, true)};
    case app::ProductMode::Active:
      return SystemRenderer::screens(product.system, observation, world);
    case app::ProductMode::InactivityPrompt:
      return DualFrames{Renderer::mapScreen(observation), inactivityPrompt(product)};
  }
  return DualFrames{};
}

}  // namespace catamaze::render
