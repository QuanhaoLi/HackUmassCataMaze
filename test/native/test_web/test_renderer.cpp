// Created at: 2026-11-14 02:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:37 EST
// Last Modified by: Codex
// Verifies SSD1306 page order, clipping, deterministic screens, and player-visible rendering.

#include <gtest/gtest.h>

#include <algorithm>
#include <cstddef>
#include <cstdint>

#include "catamaze/app/application.hpp"
#include "catamaze/render/framebuffer.hpp"
#include "catamaze/render/renderer.hpp"

namespace catamaze::render {
namespace {

std::size_t litPixels(const Framebuffer& frame) {
  std::size_t count = 0U;
  for (std::int16_t y = 0; y < Framebuffer::kHeight; ++y) {
    for (std::int16_t x = 0; x < Framebuffer::kWidth; ++x) {
      count += frame.pixel(x, y) ? 1U : 0U;
    }
  }
  return count;
}

std::size_t litPixelsInCell(const Framebuffer& frame, std::size_t index) {
  constexpr std::int16_t kGridX = 34;
  constexpr std::int16_t kGridY = 2;
  constexpr std::int16_t kCellSize = 12;
  const auto cell_x = static_cast<std::int16_t>(kGridX + (index % 5U) * kCellSize);
  const auto cell_y = static_cast<std::int16_t>(kGridY + (index / 5U) * kCellSize);
  std::size_t count = 0U;
  for (std::int16_t y = cell_y; y < cell_y + kCellSize; ++y) {
    for (std::int16_t x = cell_x; x < cell_x + kCellSize; ++x) {
      count += frame.pixel(x, y) ? 1U : 0U;
    }
  }
  return count;
}

TEST(Framebuffer, UsesSsd1306PageOrderAndClipsSafely) {
  Framebuffer frame;
  frame.clear();
  frame.setPixel(0, 0);
  frame.setPixel(0, 7);
  frame.setPixel(0, 8);
  frame.setPixel(127, 63);
  frame.setPixel(-1, -1);
  frame.setPixel(128, 64);

  EXPECT_EQ(frame.bytes().size(), Framebuffer::kByteCount);
  EXPECT_EQ(frame.bytes()[0], 0x81U);
  EXPECT_EQ(frame.bytes()[128], 0x01U);
  EXPECT_EQ(frame.bytes()[1023], 0x80U);
  EXPECT_TRUE(frame.pixel(0, 0));
  EXPECT_FALSE(frame.pixel(-1, 0));
}

TEST(Renderer, ProducesDeterministicNonEmptyMapAndHudFrames) {
  app::Application application(0x134fd5aU);
  const Framebuffer first_map = Renderer::mapScreen(application.playerObservation());
  const Framebuffer second_map = Renderer::mapScreen(application.playerObservation());
  const Framebuffer hud = Renderer::hudScreen(application.state());

  EXPECT_EQ(first_map.bytes(), second_map.bytes());
  EXPECT_NE(first_map.bytes(), hud.bytes());
  EXPECT_GT(litPixels(first_map), 250U);
  EXPECT_GT(litPixels(hud), 250U);
  EXPECT_LT(litPixels(first_map), 4000U);
  EXPECT_LT(litPixels(hud), 4000U);
}

TEST(Renderer, HiddenCellPixelsDifferFromVisibleFloor) {
  core::Observation hidden{};
  hidden.self.position = core::Position{10, 10};
  hidden.cells[12].visible = true;
  hidden.cells[12].terrain = core::Terrain::Floor;
  const Framebuffer hidden_frame = Renderer::mapScreen(hidden);

  core::Observation visible = hidden;
  for (auto& cell : visible.cells) {
    cell.visible = true;
    cell.terrain = core::Terrain::Floor;
  }
  const Framebuffer visible_frame = Renderer::mapScreen(visible);

  EXPECT_NE(hidden_frame.bytes(), visible_frame.bytes());
}

TEST(Renderer, RoadIsBlankFogIsOneSlashAndWallIsSolid) {
  core::Observation observation{};
  for (auto& cell : observation.cells) {
    cell.visible = true;
    cell.terrain = core::Terrain::Floor;
  }
  const Framebuffer road = Renderer::mapScreen(observation);
  EXPECT_EQ(litPixelsInCell(road, 0U), 0U);

  observation.cells[0].visible = false;
  const Framebuffer fog = Renderer::mapScreen(observation);
  EXPECT_EQ(litPixelsInCell(fog, 0U), 7U);

  observation.cells[0].visible = true;
  observation.cells[0].terrain = core::Terrain::Wall;
  const Framebuffer wall = Renderer::mapScreen(observation);
  EXPECT_EQ(litPixelsInCell(wall, 0U), 144U);
}

TEST(Renderer, ProjectileStateNeverChangesThePlayerMapFramebuffer) {
  core::Observation observation{};
  for (auto& cell : observation.cells) {
    cell.visible = true;
    cell.terrain = core::Terrain::Floor;
  }
  const Framebuffer without_projectile = Renderer::mapScreen(observation);
  observation.cells[1].bullet = true;
  observation.cells[1].bullet_direction = core::Direction::Left;
  const Framebuffer with_projectile = Renderer::mapScreen(observation);
  EXPECT_EQ(without_projectile.bytes(), with_projectile.bytes());
}

TEST(Renderer, HudUsesFilledAndOutlineHeartAndAmmoSlots) {
  core::WorldState state{};
  auto& player = state.entities[core::entityIndex(core::EntityId::Player)];
  player.hp = 5U;
  player.ammo = 3U;
  const Framebuffer full = Renderer::hudScreen(state);

  player.hp = 4U;
  player.ammo = 2U;
  const Framebuffer depleted = Renderer::hudScreen(state);
  EXPECT_NE(full.bytes(), depleted.bytes());

  constexpr std::int16_t kLastHeartX = Renderer::kHudValueX + 4 * 9;
  EXPECT_TRUE(full.pixel(kLastHeartX + 3, Renderer::kHudRowY[1] + 2));
  EXPECT_FALSE(depleted.pixel(kLastHeartX + 3, Renderer::kHudRowY[1] + 2));
  EXPECT_TRUE(depleted.pixel(kLastHeartX, Renderer::kHudRowY[1] + 1));

  constexpr std::int16_t kLastAmmoX = Renderer::kHudValueX + 2 * 10;
  EXPECT_TRUE(full.pixel(kLastAmmoX + 3, Renderer::kHudRowY[2] + 3));
  EXPECT_FALSE(depleted.pixel(kLastAmmoX + 3, Renderer::kHudRowY[2] + 3));
  EXPECT_TRUE(depleted.pixel(kLastAmmoX + 1, Renderer::kHudRowY[2] + 3));
}

TEST(Renderer, HudHasNoTitleAndUsesOneRightColumn) {
  core::WorldState state{};
  state.tick = 761U;
  const Framebuffer hud = Renderer::hudScreen(state);

  EXPECT_EQ(Renderer::kHudLabelX, 1);
  EXPECT_EQ(Renderer::kHudValueX, 44);
  EXPECT_EQ(Renderer::kHudRowY, (std::array<std::int16_t, 5>{3, 15, 27, 39, 51}));
  for (std::int16_t y = 0; y < 3; ++y) {
    for (std::int16_t x = 0; x < Framebuffer::kWidth; ++x) {
      EXPECT_FALSE(hud.pixel(x, y));
    }
  }
  EXPECT_TRUE(hud.pixel(Renderer::kHudValueX, Renderer::kHudRowY[0] + 1));
  EXPECT_TRUE(hud.pixel(Renderer::kHudValueX, Renderer::kHudRowY[3] + 1));
  EXPECT_TRUE(hud.pixel(Renderer::kHudValueX, Renderer::kHudRowY[4] + 1));
}

TEST(Renderer, HudChangesWhenPublicFieldsChange) {
  app::Application application(7U);
  const Framebuffer before = Renderer::hudScreen(application.state());
  ASSERT_TRUE(application.enqueuePlayerAction(core::Action::Wait));
  application.tick();
  const Framebuffer after = Renderer::hudScreen(application.state());
  EXPECT_NE(before.bytes(), after.bytes());
}

}  // namespace
}  // namespace catamaze::render
