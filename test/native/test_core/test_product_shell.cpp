// Created at: 2026-11-14 11:30 EST
// Created by: Codex
// Last Modified at: 2026-11-14 11:42 EST
// Last Modified by: Codex
// Verifies companion frames, consumed Wake, wrap-safe inactivity, and guarded session Sleep.

#include <gtest/gtest.h>

#include <array>
#include <cstdint>
#include <limits>

#include "catamaze/app/product_shell.hpp"

namespace catamaze::app {
namespace {

TEST(ProductShell, BootsIdleAndConsumesEveryWakeIntent) {
  constexpr std::array<SystemInput, 7> kWakeInputs{
      SystemInput::Up,   SystemInput::Down,       SystemInput::Left,      SystemInput::Right,
      SystemInput::Fire, SystemInput::ClearShort, SystemInput::ClearLong,
  };
  for (SystemInput input : kWakeInputs) {
    ProductShell shell(7U);
    shell.begin(100U);
    ASSERT_EQ(shell.snapshot().mode, ProductMode::CompanionIdle);
    ASSERT_TRUE(shell.handle(input, 101U));
    EXPECT_EQ(shell.snapshot().mode, ProductMode::Active);
    EXPECT_EQ(shell.snapshot().system.mode, SystemMode::Home);
    EXPECT_EQ(shell.snapshot().system.focus, 0U);
    EXPECT_EQ(shell.application().state().player_queue.size(), 0U);
  }
}

TEST(ProductShell, SecondFireAfterWakeStartsConfiguredGame) {
  ProductShell shell(11U);
  shell.begin(0U);
  ASSERT_TRUE(shell.handle(SystemInput::Fire, 1U));
  ASSERT_EQ(shell.snapshot().system.mode, SystemMode::Home);
  ASSERT_TRUE(shell.handle(SystemInput::Fire, 2U));
  EXPECT_EQ(shell.snapshot().mode, ProductMode::Active);
  EXPECT_EQ(shell.snapshot().system.mode, SystemMode::Playing);
  EXPECT_TRUE(shell.snapshot().system.has_active_session);
}

TEST(ProductShell, CompanionFrameScheduleIsExactAndRepeats) {
  EXPECT_EQ(companionFrameAt(0U), CompanionFrame::Neutral);
  EXPECT_EQ(companionFrameAt(3000U), CompanionFrame::LookLeft);
  EXPECT_EQ(companionFrameAt(5000U), CompanionFrame::BlinkHalf);
  EXPECT_EQ(companionFrameAt(5100U), CompanionFrame::BlinkClosed);
  EXPECT_EQ(companionFrameAt(5300U), CompanionFrame::BlinkHalf);
  EXPECT_EQ(companionFrameAt(5400U), CompanionFrame::LookRight);
  EXPECT_EQ(companionFrameAt(7500U), CompanionFrame::Happy);
  EXPECT_EQ(companionFrameAt(10000U), CompanionFrame::Curious);
  EXPECT_EQ(companionFrameAt(12500U), CompanionFrame::Curious);
  EXPECT_EQ(companionFrameAt(13500U), CompanionFrame::Neutral);
  EXPECT_EQ(companionFrameAt(15000U), CompanionFrame::Sleepy);
  EXPECT_EQ(companionFrameAt(17500U), CompanionFrame::Surprised);
  EXPECT_EQ(companionFrameAt(19500U), CompanionFrame::Neutral);
  EXPECT_EQ(companionFrameAt(ProductShell::kCompanionCycleMs), CompanionFrame::Neutral);
}

TEST(ProductShell, MenuInactivitySleepsAtExactlyThirtySeconds) {
  ProductShell shell(13U);
  shell.begin(1000U);
  ASSERT_TRUE(shell.handle(SystemInput::Up, 1001U));
  EXPECT_FALSE(shell.update(31000U));
  EXPECT_EQ(shell.snapshot().mode, ProductMode::Active);
  EXPECT_TRUE(shell.update(31001U));
  EXPECT_EQ(shell.snapshot().mode, ProductMode::CompanionIdle);
  EXPECT_EQ(shell.snapshot().system.mode, SystemMode::Home);
}

TEST(ProductShell, PlayingInactivityFreezesAndContinueRestoresExactSession) {
  ProductShell shell(17U);
  shell.begin(0U);
  shell.handle(SystemInput::Fire, 1U);
  shell.handle(SystemInput::Fire, 2U);
  ASSERT_TRUE(shell.handle(SystemInput::Right, 3U));
  const std::uint64_t hash = shell.application().stateHash();
  const std::size_t queue = shell.application().state().player_queue.size();

  EXPECT_FALSE(shell.update(30002U));
  ASSERT_TRUE(shell.update(30003U));
  EXPECT_EQ(shell.snapshot().mode, ProductMode::InactivityPrompt);
  EXPECT_EQ(shell.snapshot().system.mode, SystemMode::Paused);
  EXPECT_EQ(shell.snapshot().prompt_focus, 0U);
  EXPECT_EQ(shell.application().stateHash(), hash);
  EXPECT_EQ(shell.application().state().player_queue.size(), queue);
  shell.tick();
  EXPECT_EQ(shell.application().stateHash(), hash);

  ASSERT_TRUE(shell.handle(SystemInput::Fire, 30004U));
  EXPECT_EQ(shell.snapshot().mode, ProductMode::Active);
  EXPECT_EQ(shell.snapshot().system.mode, SystemMode::Playing);
  EXPECT_EQ(shell.application().stateHash(), hash);
  EXPECT_EQ(shell.application().state().player_queue.size(), queue);
}

TEST(ProductShell, SleepExplicitlyAbandonsPromptedSession) {
  ProductShell shell(19U);
  shell.begin(0U);
  shell.handle(SystemInput::Fire, 1U);
  shell.handle(SystemInput::Fire, 2U);
  ASSERT_TRUE(shell.update(30002U));
  ASSERT_TRUE(shell.handle(SystemInput::Down, 30003U));
  ASSERT_EQ(shell.snapshot().prompt_focus, 1U);
  ASSERT_TRUE(shell.handle(SystemInput::Fire, 30004U));
  EXPECT_EQ(shell.snapshot().mode, ProductMode::CompanionIdle);
  EXPECT_EQ(shell.snapshot().system.mode, SystemMode::Home);
  EXPECT_FALSE(shell.snapshot().system.has_active_session);
}

TEST(ProductShell, ExistingPauseRemainsPausedAfterPromptContinue) {
  ProductShell shell(23U);
  shell.begin(0U);
  shell.handle(SystemInput::Fire, 1U);
  shell.handle(SystemInput::Fire, 2U);
  shell.handle(SystemInput::ClearLong, 3U);
  ASSERT_EQ(shell.snapshot().system.mode, SystemMode::Paused);
  ASSERT_TRUE(shell.update(30003U));
  ASSERT_TRUE(shell.handle(SystemInput::ClearShort, 30004U));
  EXPECT_EQ(shell.snapshot().mode, ProductMode::Active);
  EXPECT_EQ(shell.snapshot().system.mode, SystemMode::Paused);
}

TEST(ProductShell, HomeLongClearSleepsAndTimersSurviveMillisWrap) {
  ProductShell shell(29U);
  constexpr std::uint32_t kStart = std::numeric_limits<std::uint32_t>::max() - 100U;
  shell.begin(kStart);
  shell.handle(SystemInput::Down, static_cast<std::uint32_t>(kStart + 1U));
  EXPECT_FALSE(shell.update(29899U));
  EXPECT_TRUE(shell.update(29900U));
  EXPECT_EQ(shell.snapshot().mode, ProductMode::CompanionIdle);
  shell.handle(SystemInput::Up, 29901U);
  ASSERT_EQ(shell.snapshot().mode, ProductMode::Active);
  EXPECT_TRUE(shell.handle(SystemInput::ClearLong, 29902U));
  EXPECT_EQ(shell.snapshot().mode, ProductMode::CompanionIdle);
}

TEST(ProductShell, PublicNamesCoverEveryFrameAndMode) {
  EXPECT_EQ(productModeName(ProductMode::CompanionIdle), "IDLE");
  EXPECT_EQ(productModeName(ProductMode::Active), "ACTIVE");
  EXPECT_EQ(productModeName(ProductMode::InactivityPrompt), "INACTIVITY_PROMPT");
  EXPECT_EQ(companionFrameName(CompanionFrame::Neutral), "NEUTRAL");
  EXPECT_EQ(companionFrameName(CompanionFrame::LookLeft), "LOOK_LEFT");
  EXPECT_EQ(companionFrameName(CompanionFrame::BlinkHalf), "BLINK_HALF");
  EXPECT_EQ(companionFrameName(CompanionFrame::BlinkClosed), "BLINK_CLOSED");
  EXPECT_EQ(companionFrameName(CompanionFrame::LookRight), "LOOK_RIGHT");
  EXPECT_EQ(companionFrameName(CompanionFrame::Happy), "HAPPY");
  EXPECT_EQ(companionFrameName(CompanionFrame::Curious), "CURIOUS");
  EXPECT_EQ(companionFrameName(CompanionFrame::Sleepy), "SLEEPY");
  EXPECT_EQ(companionFrameName(CompanionFrame::Surprised), "SURPRISED");
}

}  // namespace
}  // namespace catamaze::app
