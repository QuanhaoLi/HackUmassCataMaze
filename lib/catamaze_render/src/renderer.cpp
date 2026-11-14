// Created at: 2026-11-14 02:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Implements exact 128x64 Map and HUD pixel layouts without driver-specific code.

#include "catamaze/render/renderer.hpp"

#include <array>
#include <cstddef>
#include <cstdio>

namespace catamaze::render {
namespace {

constexpr std::int16_t kGridX = 70;
constexpr std::int16_t kGridY = 4;
constexpr std::int16_t kCellSize = 11;

void drawMapCell(Framebuffer& frame, const core::ObservedCell& cell, std::size_t index) noexcept {
  const std::int16_t column = static_cast<std::int16_t>(index % 5U);
  const std::int16_t row = static_cast<std::int16_t>(index / 5U);
  const std::int16_t x = static_cast<std::int16_t>(kGridX + column * kCellSize);
  const std::int16_t y = static_cast<std::int16_t>(kGridY + row * kCellSize);

  if (!cell.visible) {
    for (std::int16_t offset = 2; offset < kCellSize - 1; offset += 3) {
      frame.setPixel(static_cast<std::int16_t>(x + offset), static_cast<std::int16_t>(y + offset));
      frame.setPixel(static_cast<std::int16_t>(x + kCellSize - 1 - offset),
                     static_cast<std::int16_t>(y + offset));
    }
  } else if (cell.terrain == core::Terrain::Wall) {
    for (std::int16_t inner_y = 2; inner_y < kCellSize - 1; inner_y += 2) {
      for (std::int16_t inner_x = 2; inner_x < kCellSize - 1; inner_x += 2) {
        frame.setPixel(static_cast<std::int16_t>(x + inner_x),
                       static_cast<std::int16_t>(y + inner_y));
      }
    }
  } else {
    frame.setPixel(static_cast<std::int16_t>(x + 5), static_cast<std::int16_t>(y + 5));
    if (cell.terrain == core::Terrain::Entrance) {
      frame.drawChar(static_cast<std::int16_t>(x + 3), static_cast<std::int16_t>(y + 2), 'S');
    } else if (cell.terrain == core::Terrain::Exit) {
      frame.drawChar(static_cast<std::int16_t>(x + 3), static_cast<std::int16_t>(y + 2), 'E');
    }
  }

  if (index == 12U) {
    frame.drawRect(static_cast<std::int16_t>(x + 2), static_cast<std::int16_t>(y + 2), 7, 7);
    frame.fillRect(static_cast<std::int16_t>(x + 5), static_cast<std::int16_t>(y + 1), 1, 9);
    frame.fillRect(static_cast<std::int16_t>(x + 1), static_cast<std::int16_t>(y + 5), 9, 1);
  } else if (cell.entity >= 0) {
    frame.fillRect(static_cast<std::int16_t>(x + 3), static_cast<std::int16_t>(y + 3), 5, 5);
  }
  if (cell.bullet) {
    frame.fillRect(static_cast<std::int16_t>(x + 4), static_cast<std::int16_t>(y + 4), 3, 3);
  }
  frame.drawRect(x, y, kCellSize, kCellSize);
}

}  // namespace

Framebuffer Renderer::mapScreen(const core::Observation& observation) noexcept {
  Framebuffer frame;
  frame.clear();
  frame.drawText(3, 2, "MAP");
  frame.drawText(3, 14, "5X5");
  frame.drawText(3, 50, "LOCAL");
  frame.drawRect(0, 0, Framebuffer::kWidth, Framebuffer::kHeight);
  for (std::size_t index = 0; index < observation.cells.size(); ++index) {
    drawMapCell(frame, observation.cells[index], index);
  }
  return frame;
}

Framebuffer Renderer::hudScreen(const core::WorldState& state) noexcept {
  Framebuffer frame;
  frame.clear();
  const auto& player = state.entities[core::entityIndex(core::EntityId::Player)];
  std::array<char, 24> line{};

  frame.drawText(1, 0, "CATAMAZE");
  std::snprintf(line.data(), line.size(), "TICK   %05u", static_cast<unsigned>(state.tick));
  frame.drawText(1, 10, line.data());
  std::snprintf(line.data(), line.size(), "HP     %u/%u", static_cast<unsigned>(player.hp),
                static_cast<unsigned>(core::kMaxHp));
  frame.drawText(1, 20, line.data());
  std::snprintf(line.data(), line.size(), "AMMO   %u/%u", static_cast<unsigned>(player.ammo),
                static_cast<unsigned>(core::kMaxAmmo));
  frame.drawText(1, 30, line.data());
  std::snprintf(line.data(), line.size(), "QUEUE  %02u/%02u",
                static_cast<unsigned>(state.player_queue.size()),
                static_cast<unsigned>(state.player_queue.capacity()));
  frame.drawText(1, 40, line.data());
  std::snprintf(line.data(), line.size(), "POS    %02d,%02d", player.position.x, player.position.y);
  frame.drawText(1, 50, line.data());
  return frame;
}

}  // namespace catamaze::render
