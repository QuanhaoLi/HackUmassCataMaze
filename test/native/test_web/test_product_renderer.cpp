// Created at: 2026-11-14 11:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 19:00 EST
// Last Modified by: Codex
// Verifies reviewed eye expressions, active delegation, and inactivity prompt framebuffers.

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <cstdint>

#include "catamaze/app/product_shell.hpp"
#include "catamaze/render/product_renderer.hpp"
#include "catamaze/render/renderer.hpp"
#include "catamaze/render/system_renderer.hpp"

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

TEST(ProductRenderer, EveryReviewedCompanionFrameIsBoundedAndVisiblyDistinct) {
  app::ProductShell shell(7U);
  shell.begin(0U);
  constexpr std::array<std::uint32_t, 9> kFrameTimes{0U,    3000U,  5000U,  5100U, 5400U,
                                                     7500U, 10000U, 15000U, 17500U};
  std::array<Framebuffer, kFrameTimes.size()> left_frames{};
  for (std::size_t index = 0U; index < kFrameTimes.size(); ++index) {
    shell.update(kFrameTimes[index]);
    const DualFrames frames = ProductRenderer::screens(shell.snapshot(), shell.playerObservation(),
                                                       shell.application().state());
    left_frames[index] = frames.left;
    EXPECT_GT(litPixels(frames.left), 100U) << index;
    EXPECT_GT(litPixels(frames.right), 100U) << index;
    EXPECT_LT(litPixels(frames.left), 7000U) << index;
    EXPECT_LT(litPixels(frames.right), 7000U) << index;
  }
  for (std::size_t index = 1U; index < left_frames.size(); ++index) {
    EXPECT_NE(left_frames[index].bytes(), left_frames[index - 1U].bytes()) << index;
  }
}

TEST(ProductRenderer, SymmetricFramesMatchAndCuriousEyesDiffer) {
  app::ProductShell shell(9U);
  shell.begin(0U);
  DualFrames neutral = ProductRenderer::screens(shell.snapshot(), shell.playerObservation(),
                                                shell.application().state());
  EXPECT_EQ(neutral.left.bytes(), neutral.right.bytes());

  shell.update(10000U);
  DualFrames curious = ProductRenderer::screens(shell.snapshot(), shell.playerObservation(),
                                                shell.application().state());
  EXPECT_NE(curious.left.bytes(), curious.right.bytes());
}

TEST(ProductRenderer, ActiveModeDelegatesExactSystemFrames) {
  app::ProductShell shell(11U);
  shell.begin(0U);
  shell.handle(app::SystemInput::Up, 1U);
  const DualFrames product = ProductRenderer::screens(shell.snapshot(), shell.playerObservation(),
                                                      shell.application().state());
  const DualFrames system = SystemRenderer::screens(
      shell.snapshot().system, shell.playerObservation(), shell.application().state());
  EXPECT_EQ(product.left.bytes(), system.left.bytes());
  EXPECT_EQ(product.right.bytes(), system.right.bytes());
}

TEST(ProductRenderer, InactivityPromptFreezesMapAndOwnsRightScreen) {
  app::ProductShell shell(13U);
  shell.begin(0U);
  shell.handle(app::SystemInput::Fire, 1U);
  shell.handle(app::SystemInput::Fire, 2U);
  shell.update(30002U);
  ASSERT_EQ(shell.snapshot().mode, app::ProductMode::InactivityPrompt);
  const DualFrames frames = ProductRenderer::screens(shell.snapshot(), shell.playerObservation(),
                                                     shell.application().state());
  EXPECT_EQ(frames.left.bytes(), Renderer::mapScreen(shell.playerObservation()).bytes());
  EXPECT_GT(litPixels(frames.right), 300U);
  EXPECT_NE(frames.right.bytes(), Renderer::hudScreen(shell.application().state()).bytes());

  shell.handle(app::SystemInput::Down, 30003U);
  const DualFrames sleep = ProductRenderer::screens(shell.snapshot(), shell.playerObservation(),
                                                    shell.application().state());
  EXPECT_NE(frames.right.bytes(), sleep.right.bytes());
}

TEST(ProductRenderer, SystemSoftwareFocusShowsBoundedPolicyHealth) {
  app::ProductShell shell(17U);
  shell.begin(0U);
  shell.handle(app::SystemInput::Up, 1U);
  app::ProductSnapshot snapshot = shell.snapshot();
  snapshot.mode = app::ProductMode::Active;
  snapshot.system.mode = app::SystemMode::System;
  snapshot.system.focus = 1U;
  snapshot.policy_health.mode = app::PolicyMode::FallbackLatched;
  snapshot.policy_health.failure = app::PolicyFailure::LatencyBudget;
  snapshot.policy_health.inference_calls = 123U;
  snapshot.policy_health.inference_failures = 1U;
  snapshot.policy_health.last_tick_inference_us = 900001U;
  snapshot.policy_health.max_tick_inference_us = 900001U;

  const DualFrames health =
      ProductRenderer::screens(snapshot, shell.playerObservation(), shell.application().state());
  snapshot.policy_health.failure = app::PolicyFailure::None;
  const DualFrames healthy =
      ProductRenderer::screens(snapshot, shell.playerObservation(), shell.application().state());
  EXPECT_GT(litPixels(health.right), 200U);
  EXPECT_NE(health.right.bytes(), healthy.right.bytes());
}

}  // namespace
}  // namespace catamaze::render
