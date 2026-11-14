// Created at: 2026-11-14 02:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 03:11 EST
// Last Modified by: Codex
// Implements exact 128x64 Map and HUD pixel layouts without driver-specific code.

#include "catamaze/render/renderer.hpp"

#include <array>
#include <cstddef>
#include <cstdio>

namespace catamaze::render {
namespace {

constexpr std::int16_t kGridX = 34;
constexpr std::int16_t kGridY = 2;
constexpr std::int16_t kCellSize = 12;

using IconRows = std::array<std::uint8_t, 7>;

constexpr IconRows kHeartFilled{0x36, 0x7f, 0x7f, 0x7f, 0x3e, 0x1c, 0x08};
constexpr IconRows kHeartOutline{0x36, 0x49, 0x41, 0x41, 0x22, 0x14, 0x08};
constexpr IconRows kAmmoFilled{0x1c, 0x3e, 0x3e, 0x3e, 0x3e, 0x3e, 0x3e};
constexpr IconRows kAmmoOutline{0x1c, 0x22, 0x22, 0x22, 0x22, 0x22, 0x3e};

void drawIcon(Framebuffer& frame, std::int16_t x, std::int16_t y, const IconRows& rows) noexcept {
  for (std::size_t row = 0; row < rows.size(); ++row) {
    for (std::uint8_t column = 0; column < 7U; ++column) {
      const std::uint8_t mask = static_cast<std::uint8_t>(1U << (6U - column));
      if ((rows[row] & mask) != 0U) {
        frame.setPixel(static_cast<std::int16_t>(x + column), static_cast<std::int16_t>(y + row));
      }
    }
  }
}

void drawPlayer(Framebuffer& frame, std::int16_t x, std::int16_t y) noexcept {
  constexpr std::array<std::array<std::int8_t, 2>, 18> kDiamond{{
      {{6, 1}},
      {{5, 2}},
      {{7, 2}},
      {{4, 3}},
      {{8, 3}},
      {{3, 4}},
      {{9, 4}},
      {{2, 5}},
      {{10, 5}},
      {{2, 6}},
      {{10, 6}},
      {{3, 7}},
      {{9, 7}},
      {{4, 8}},
      {{8, 8}},
      {{5, 9}},
      {{7, 9}},
      {{6, 10}},
  }};
  for (const auto& point : kDiamond) {
    frame.setPixel(static_cast<std::int16_t>(x + point[0]),
                   static_cast<std::int16_t>(y + point[1]));
  }
}

void drawMapCell(Framebuffer& frame, const core::ObservedCell& cell, std::size_t index) noexcept {
  const std::int16_t column = static_cast<std::int16_t>(index % 5U);
  const std::int16_t row = static_cast<std::int16_t>(index / 5U);
  const std::int16_t x = static_cast<std::int16_t>(kGridX + column * kCellSize);
  const std::int16_t y = static_cast<std::int16_t>(kGridY + row * kCellSize);

  if (!cell.visible) {
    for (std::int16_t offset = 0; offset < 7; ++offset) {
      frame.setPixel(static_cast<std::int16_t>(x + 3 + offset),
                     static_cast<std::int16_t>(y + 9 - offset));
    }
  } else if (cell.terrain == core::Terrain::Wall) {
    frame.fillRect(x, y, kCellSize, kCellSize);
  } else if (index != 12U && cell.entity < 0) {
    if (cell.terrain == core::Terrain::Entrance) {
      frame.drawChar(static_cast<std::int16_t>(x + 3), static_cast<std::int16_t>(y + 2), 'S');
    } else if (cell.terrain == core::Terrain::Exit) {
      frame.drawChar(static_cast<std::int16_t>(x + 3), static_cast<std::int16_t>(y + 2), 'E');
    }
  }

  if (index == 12U) {
    drawPlayer(frame, x, y);
  } else if (cell.entity >= 0) {
    frame.fillRect(static_cast<std::int16_t>(x + 3), static_cast<std::int16_t>(y + 3), 6, 6);
  }
}

}  // namespace

Framebuffer Renderer::mapScreen(const core::Observation& observation) noexcept {
  Framebuffer frame;
  frame.clear();
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
  frame.drawText(1, 20, "HP");
  for (std::uint8_t index = 0; index < core::kMaxHp; ++index) {
    drawIcon(frame, static_cast<std::int16_t>(32 + index * 9), 20,
             index < player.hp ? kHeartFilled : kHeartOutline);
  }
  frame.drawText(1, 30, "AMMO");
  for (std::uint8_t index = 0; index < core::kMaxAmmo; ++index) {
    drawIcon(frame, static_cast<std::int16_t>(32 + index * 10), 30,
             index < player.ammo ? kAmmoFilled : kAmmoOutline);
  }
  std::snprintf(line.data(), line.size(), "QUEUE  %02u/%02u",
                static_cast<unsigned>(state.player_queue.size()),
                static_cast<unsigned>(state.player_queue.capacity()));
  frame.drawText(1, 40, line.data());
  std::snprintf(line.data(), line.size(), "POS    %02d,%02d", player.position.x, player.position.y);
  frame.drawText(1, 50, line.data());
  return frame;
}

}  // namespace catamaze::render
