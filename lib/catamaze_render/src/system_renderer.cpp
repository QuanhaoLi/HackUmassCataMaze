// Created at: 2026-11-14 07:09 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:18 EST
// Last Modified by: Codex
// Implements the restrained one-bit dual-screen system visual language.

#include "catamaze/render/system_renderer.hpp"

#include <array>
#include <cstdint>
#include <cstdio>
#include <string_view>

#include "catamaze/core/version.hpp"
#include "catamaze/render/renderer.hpp"

namespace catamaze::render {
namespace {

constexpr std::int16_t kTitleX = 4;
constexpr std::int16_t kTitleY = 2;
constexpr std::array<std::int16_t, 4> kMenuRows{18, 29, 40, 51};

void title(Framebuffer& frame, std::string_view text) noexcept {
  frame.drawText(kTitleX, kTitleY, text);
  frame.fillRect(3, 11, 122, 1);
}

void selectedRow(Framebuffer& frame, std::int16_t y, std::string_view text,
                 bool selected) noexcept {
  if (selected) {
    frame.fillRect(2, static_cast<std::int16_t>(y - 1), 124, 9);
    frame.drawText(7, y, text, false);
  } else {
    frame.drawText(7, y, text);
  }
}

void menu(Framebuffer& frame, const std::array<std::string_view, 4>& rows, std::uint8_t count,
          std::uint8_t focus) noexcept {
  for (std::uint8_t index = 0U; index < count; ++index) {
    selectedRow(frame, kMenuRows[index], rows[index], index == focus);
  }
}

void valueLine(Framebuffer& frame, std::int16_t y, std::string_view label,
               std::string_view value) noexcept {
  frame.drawText(4, y, label);
  frame.drawText(64, y, value);
}

void formatMapSize(std::array<char, 12>& text, std::uint8_t size) noexcept {
  std::snprintf(text.data(), text.size(), "%uX%u", static_cast<unsigned>(size),
                static_cast<unsigned>(size));
}

void formatUnsigned(std::array<char, 12>& text, std::uint16_t value) noexcept {
  std::snprintf(text.data(), text.size(), "%u", static_cast<unsigned>(value));
}

void drawMapPreview(Framebuffer& frame, std::uint8_t map_size) noexcept {
  const std::int16_t side = static_cast<std::int16_t>(10 + map_size / 2U);
  const std::int16_t x = static_cast<std::int16_t>(124 - side);
  const std::int16_t y = static_cast<std::int16_t>(60 - side);
  frame.drawRect(x, y, side, side);
  frame.setPixel(static_cast<std::int16_t>(x + 2), static_cast<std::int16_t>(y + 2));
  frame.setPixel(static_cast<std::int16_t>(x + side - 3), static_cast<std::int16_t>(y + side - 3));
  for (std::int16_t offset = 5; offset < side - 3; offset += 6) {
    frame.setPixel(static_cast<std::int16_t>(x + offset), static_cast<std::int16_t>(y + side / 2));
  }
}

Framebuffer homeLeft(const app::SystemSnapshot& system) noexcept {
  Framebuffer frame;
  frame.clear();
  title(frame, "CATAMAZE");
  menu(frame, {"PLAY", "MAP SETUP", "SYSTEM", "ABOUT"}, 4U, system.focus);
  return frame;
}

Framebuffer homeRight(const app::SystemSnapshot& system) noexcept {
  Framebuffer frame;
  frame.clear();
  std::array<char, 12> size{};
  std::array<char, 12> limit{};
  formatMapSize(size, system.confirmed_map_size);
  formatUnsigned(limit, core::tickBudgetForMapSize(system.confirmed_map_size));
  if (system.focus == 0U) {
    title(frame, "NEW RUN");
    valueLine(frame, 18, "MAP", size.data());
    valueLine(frame, 29, "LIMIT", limit.data());
    valueLine(frame, 40, "PLAYER", "9X5");
    valueLine(frame, 51, "AI", "5X5");
  } else if (system.focus == 1U) {
    title(frame, "MAP PRESET");
    frame.drawText(4, 19, "4 SQUARE SIZES");
    frame.drawText(4, 32, "FIRE TO EDIT");
    drawMapPreview(frame, system.confirmed_map_size);
  } else if (system.focus == 2U) {
    title(frame, "SYSTEM");
    frame.drawText(4, 19, "MAC NATIVE READY");
    frame.drawText(4, 32, "ESP32 PENDING");
    frame.drawText(4, 45, "SIX BUTTON INPUT");
  } else {
    title(frame, "ABOUT");
    frame.drawText(4, 19, "DETERMINISTIC");
    frame.drawText(4, 32, "DUAL OLED MAZE");
    frame.drawText(4, 45, "C PLUS PLUS 17");
  }
  return frame;
}

Framebuffer setupLeft(const app::SystemSnapshot& system) noexcept {
  Framebuffer frame;
  frame.clear();
  title(frame, "MAP SETUP");
  std::array<char, 20> row{};
  std::array<char, 12> size{};
  formatMapSize(size, system.pending_map_size);
  std::snprintf(row.data(), row.size(), "SIZE  %s", size.data());
  selectedRow(frame, 22, row.data(), system.focus == 0U);
  selectedRow(frame, 42, "START GAME", system.focus == 1U);
  frame.drawText(4, 55, "LEFT RIGHT CHANGE");
  return frame;
}

Framebuffer setupRight(const app::SystemSnapshot& system) noexcept {
  Framebuffer frame;
  frame.clear();
  title(frame, app::mapPresetName(system.pending_map_size));
  std::array<char, 12> size{};
  std::array<char, 12> limit{};
  formatMapSize(size, system.pending_map_size);
  formatUnsigned(limit, system.tick_budget);
  valueLine(frame, 18, "SIZE", size.data());
  valueLine(frame, 29, "LIMIT", limit.data());
  valueLine(frame, 40, "ENEMY", "3");
  valueLine(frame, 51, "AI FOV", "5X5");
  drawMapPreview(frame, system.pending_map_size);
  return frame;
}

Framebuffer systemLeft(const app::SystemSnapshot& system) noexcept {
  Framebuffer frame;
  frame.clear();
  title(frame, "SYSTEM");
  menu(frame, {"HARDWARE", "SOFTWARE", "CONTROLS", ""}, 3U, system.focus);
  return frame;
}

Framebuffer systemRight(const app::SystemSnapshot& system) noexcept {
  Framebuffer frame;
  frame.clear();
  if (system.focus == 0U) {
    title(frame, "HARDWARE");
    frame.drawText(4, 19, "DISPLAY  2 X OLED");
    frame.drawText(4, 32, "NATIVE   READY");
    frame.drawText(4, 45, "ESP32    PENDING");
  } else if (system.focus == 1U) {
    title(frame, "SOFTWARE");
    frame.drawText(4, 19, "CORE");
    frame.drawText(46, 19, core::kCoreVersion);
    frame.drawText(4, 32, "RULES");
    frame.drawText(46, 32, "V1");
    frame.drawText(4, 45, "C PLUS PLUS 17");
  } else {
    title(frame, "CONTROLS");
    frame.drawText(4, 17, "ARROWS  MOVE MENU");
    frame.drawText(4, 29, "FIRE    OK SHOOT");
    frame.drawText(4, 41, "CLEAR   BACK");
    frame.drawText(4, 53, "HOLD    PAUSE");
  }
  return frame;
}

DualFrames aboutFrames() noexcept {
  DualFrames frames;
  frames.left.clear();
  frames.right.clear();
  title(frames.left, "CATAMAZE");
  frames.left.drawRect(42, 21, 44, 31);
  frames.left.drawText(55, 29, "CM");
  frames.left.drawText(34, 56, core::kCoreVersion);
  title(frames.right, "PLAYER EDGE");
  frames.right.drawText(4, 19, "PLAYER VIEW  9X5");
  frames.right.drawText(4, 32, "AI VIEW      5X5");
  frames.right.drawText(4, 45, "CLEAR TO RETURN");
  return frames;
}

Framebuffer pauseRight(const app::SystemSnapshot& system) noexcept {
  Framebuffer frame;
  frame.clear();
  title(frame, "PAUSED");
  menu(frame, {"RESUME", "RESTART", "HOME", ""}, 3U, system.focus);
  return frame;
}

Framebuffer confirmRight(const app::SystemSnapshot& system) noexcept {
  Framebuffer frame;
  frame.clear();
  title(frame, "LEAVE RUN");
  frame.drawText(4, 18, "QUEUE WILL BE LOST");
  selectedRow(frame, 35, "CANCEL", system.focus == 0U);
  selectedRow(frame, 49, "LEAVE", system.focus == 1U);
  return frame;
}

Framebuffer resultRight(const app::SystemSnapshot& system, const core::WorldState& world) noexcept {
  Framebuffer frame;
  frame.clear();
  title(frame, core::toString(system.game_status));
  std::array<char, 18> tick{};
  std::snprintf(tick.data(), tick.size(), "TICK  %05u", static_cast<unsigned>(world.tick));
  frame.drawText(4, 15, tick.data());
  selectedRow(frame, 29, "REPLAY", system.focus == 0U);
  selectedRow(frame, 40, "NEW RUN", system.focus == 1U);
  selectedRow(frame, 51, "HOME", system.focus == 2U);
  return frame;
}

}  // namespace

DualFrames SystemRenderer::screens(const app::SystemSnapshot& system,
                                   const core::PlayerObservation& observation,
                                   const core::WorldState& world) noexcept {
  switch (system.mode) {
    case app::SystemMode::Home:
      return DualFrames{homeLeft(system), homeRight(system)};
    case app::SystemMode::Setup:
      return DualFrames{setupLeft(system), setupRight(system)};
    case app::SystemMode::System:
      return DualFrames{systemLeft(system), systemRight(system)};
    case app::SystemMode::About:
      return aboutFrames();
    case app::SystemMode::Playing:
      return DualFrames{Renderer::mapScreen(observation), Renderer::hudScreen(world)};
    case app::SystemMode::Paused:
      return DualFrames{Renderer::mapScreen(observation), pauseRight(system)};
    case app::SystemMode::ConfirmHome:
      return DualFrames{Renderer::mapScreen(observation), confirmRight(system)};
    case app::SystemMode::Result:
      return DualFrames{Renderer::mapScreen(observation), resultRight(system, world)};
  }
  return DualFrames{};
}

}  // namespace catamaze::render
