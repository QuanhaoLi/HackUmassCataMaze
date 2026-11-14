// Created at: 2026-11-14 02:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
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
