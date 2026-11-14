// Created at: 2026-11-14 07:11 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:11 EST
// Last Modified by: Codex
// Verifies deterministic, mode-specific dual-screen system framebuffers and frozen-map pause
// output.

#include <gtest/gtest.h>

#include <cstddef>
#include <cstdint>

#include "catamaze/app/system_controller.hpp"
#include "catamaze/render/renderer.hpp"
#include "catamaze/render/system_renderer.hpp"

namespace catamaze::render {
namespace {

std::size_t countLit(const Framebuffer& frame) {
  std::size_t count = 0U;
  for (std::int16_t y = 0; y < Framebuffer::kHeight; ++y) {
    for (std::int16_t x = 0; x < Framebuffer::kWidth; ++x) {
      count += frame.pixel(x, y) ? 1U : 0U;
    }
  }
  return count;
}

TEST(SystemRenderer, HomeIsDeterministicAndUsesInverseFocusRows) {
  app::SystemController system(0x134fd5aU);
  const DualFrames first = SystemRenderer::screens(system.snapshot(), system.playerObservation(),
                                                   system.application().state());
  const DualFrames second = SystemRenderer::screens(system.snapshot(), system.playerObservation(),
                                                    system.application().state());

  EXPECT_EQ(first.left.bytes(), second.left.bytes());
  EXPECT_EQ(first.right.bytes(), second.right.bytes());
  EXPECT_GT(countLit(first.left), 400U);
  EXPECT_GT(countLit(first.right), 150U);
  EXPECT_TRUE(first.left.pixel(2, 17));
  EXPECT_FALSE(first.left.pixel(2, 28));

  ASSERT_TRUE(system.handle(app::SystemInput::Down));
  const DualFrames focused = SystemRenderer::screens(system.snapshot(), system.playerObservation(),
                                                     system.application().state());
  EXPECT_NE(focused.left.bytes(), first.left.bytes());
  EXPECT_NE(focused.right.bytes(), first.right.bytes());
  EXPECT_FALSE(focused.left.pixel(2, 17));
  EXPECT_TRUE(focused.left.pixel(2, 28));
}

TEST(SystemRenderer, SetupPreviewChangesWithPreset) {
  app::SystemController system(3U);
  ASSERT_TRUE(system.handle(app::SystemInput::Down));
  ASSERT_TRUE(system.handle(app::SystemInput::Fire));
  const DualFrames medium = SystemRenderer::screens(system.snapshot(), system.playerObservation(),
                                                    system.application().state());

  ASSERT_TRUE(system.handle(app::SystemInput::Right));
  const DualFrames original = SystemRenderer::screens(system.snapshot(), system.playerObservation(),
                                                      system.application().state());
  EXPECT_NE(medium.left.bytes(), original.left.bytes());
  EXPECT_NE(medium.right.bytes(), original.right.bytes());
  EXPECT_GT(countLit(original.left), 200U);
  EXPECT_GT(countLit(original.right), 200U);
}

TEST(SystemRenderer, PlayingMatchesGameScreensAndPauseFreezesLeftMap) {
  app::SystemController system(5U);
  ASSERT_TRUE(system.handle(app::SystemInput::Fire));
  const DualFrames playing = SystemRenderer::screens(system.snapshot(), system.playerObservation(),
                                                     system.application().state());
  EXPECT_EQ(playing.left.bytes(), Renderer::mapScreen(system.playerObservation()).bytes());
  EXPECT_EQ(playing.right.bytes(), Renderer::hudScreen(system.application().state()).bytes());

  ASSERT_TRUE(system.handle(app::SystemInput::ClearLong));
  const DualFrames paused = SystemRenderer::screens(system.snapshot(), system.playerObservation(),
                                                    system.application().state());
  EXPECT_EQ(paused.left.bytes(), playing.left.bytes());
  EXPECT_NE(paused.right.bytes(), playing.right.bytes());
  EXPECT_GT(countLit(paused.right), 300U);
}

TEST(SystemRenderer, EveryNonGameModeProducesTwoBoundedNonEmptyScreens) {
  app::Application game(core::GameConfig{12U, 11U});
  app::SystemSnapshot snapshot{};
  snapshot.pending_map_size = 12U;
  snapshot.confirmed_map_size = 12U;
  snapshot.tick_budget = 480U;

  constexpr app::SystemMode kModes[] = {
      app::SystemMode::Home,   app::SystemMode::Setup,  app::SystemMode::System,
      app::SystemMode::About,  app::SystemMode::Paused, app::SystemMode::ConfirmHome,
      app::SystemMode::Result,
  };
  for (const app::SystemMode mode : kModes) {
    snapshot.mode = mode;
    snapshot.focus = 0U;
    snapshot.game_status = core::GameStatus::Timeout;
    const DualFrames frames =
        SystemRenderer::screens(snapshot, game.playerObservation(), game.state());
    EXPECT_EQ(frames.left.bytes().size(), Framebuffer::kByteCount);
    EXPECT_EQ(frames.right.bytes().size(), Framebuffer::kByteCount);
    EXPECT_GT(countLit(frames.left), 20U) << static_cast<unsigned>(mode);
    EXPECT_GT(countLit(frames.right), 20U) << static_cast<unsigned>(mode);
    EXPECT_LT(countLit(frames.left), 7000U) << static_cast<unsigned>(mode);
    EXPECT_LT(countLit(frames.right), 7000U) << static_cast<unsigned>(mode);
  }
}

}  // namespace
}  // namespace catamaze::render
