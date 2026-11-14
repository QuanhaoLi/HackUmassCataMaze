// Created at: 2026-11-14 07:06 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:20 EST
// Last Modified by: Codex
// Verifies the portable six-button launcher, setup, pause, result, and session lifecycle.

#include <gtest/gtest.h>

#include <cstdint>

#include "catamaze/app/system_controller.hpp"

namespace catamaze::app {
namespace {

TEST(SystemController, BootsHomeWithRecommendedPresetAndFrozenWorld) {
  SystemController system(0x134fd5aU);
  const std::uint64_t hash = system.application().stateHash();

  EXPECT_EQ(system.snapshot().mode, SystemMode::Home);
  EXPECT_EQ(system.snapshot().confirmed_map_size, 30U);
  EXPECT_EQ(system.snapshot().pending_map_size, 30U);
  EXPECT_EQ(system.snapshot().tick_budget, 1200U);
  EXPECT_FALSE(system.snapshot().has_active_session);
  system.tick();
  EXPECT_EQ(system.application().state().tick, 0U);
  EXPECT_EQ(system.application().stateHash(), hash);
}

TEST(SystemController, SetupCyclesOnlyReviewedPresetsAndStartsConfiguredRun) {
  SystemController system(7U);
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  ASSERT_EQ(system.snapshot().mode, SystemMode::Setup);

  ASSERT_TRUE(system.handle(SystemInput::Right));
  EXPECT_EQ(system.snapshot().pending_map_size, 50U);
  EXPECT_EQ(system.snapshot().tick_budget, 2000U);
  ASSERT_TRUE(system.handle(SystemInput::Right));
  EXPECT_EQ(system.snapshot().pending_map_size, 12U);
  EXPECT_EQ(system.snapshot().tick_budget, 480U);
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Fire));

  EXPECT_EQ(system.snapshot().mode, SystemMode::Playing);
  EXPECT_TRUE(system.snapshot().has_active_session);
  EXPECT_EQ(system.snapshot().confirmed_map_size, 12U);
  EXPECT_EQ(system.application().state().map.activeSize(), 12U);
  EXPECT_EQ(system.application().state().max_ticks, 480U);
}

TEST(SystemController, SetupCancelPreservesConfirmedPreset) {
  SystemController system(8U);
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  ASSERT_TRUE(system.handle(SystemInput::Left));
  EXPECT_EQ(system.snapshot().pending_map_size, 20U);
  ASSERT_TRUE(system.handle(SystemInput::ClearShort));
  EXPECT_EQ(system.snapshot().mode, SystemMode::Home);
  EXPECT_EQ(system.snapshot().confirmed_map_size, 30U);
  EXPECT_EQ(system.snapshot().pending_map_size, 30U);
}

TEST(SystemController, SystemAndAboutAreReadOnlyAndClearReturnsHome) {
  SystemController system(9U);
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  ASSERT_EQ(system.snapshot().mode, SystemMode::System);
  EXPECT_FALSE(system.handle(SystemInput::Up));
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Down));
  EXPECT_FALSE(system.handle(SystemInput::Fire));
  EXPECT_EQ(system.snapshot().mode, SystemMode::System);
  ASSERT_TRUE(system.handle(SystemInput::ClearLong));
  EXPECT_EQ(system.snapshot().mode, SystemMode::Home);

  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  ASSERT_EQ(system.snapshot().mode, SystemMode::About);
  EXPECT_FALSE(system.handle(SystemInput::Fire));
  EXPECT_EQ(system.snapshot().mode, SystemMode::About);
  ASSERT_TRUE(system.handle(SystemInput::ClearShort));
  EXPECT_EQ(system.snapshot().mode, SystemMode::Home);
}

TEST(SystemController, FireAloneDoesNothingAndGameplayUsesOnlySixButtonIntents) {
  SystemController system(19U);
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  ASSERT_EQ(system.snapshot().mode, SystemMode::Playing);
  EXPECT_FALSE(system.handle(SystemInput::Fire));
  EXPECT_EQ(system.application().state().player_queue.size(), 0U);

  EXPECT_TRUE(system.handle(SystemInput::Up));
  EXPECT_TRUE(system.handle(SystemInput::ShootRight));
  ASSERT_EQ(system.application().state().player_queue.size(), 2U);
  EXPECT_EQ(system.application().state().player_queue.at(0U), core::Action::MoveUp);
  EXPECT_EQ(system.application().state().player_queue.at(1U), core::Action::ShootRight);
}

TEST(SystemController, LongClearPausesWithoutTickingOrClearingAndShortClearResumes) {
  SystemController system(23U);
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  ASSERT_TRUE(system.handle(SystemInput::Right));
  ASSERT_TRUE(system.handle(SystemInput::Down));
  const std::uint64_t hash = system.application().stateHash();
  const std::size_t queue_size = system.application().state().player_queue.size();

  ASSERT_TRUE(system.handle(SystemInput::ClearLong));
  EXPECT_EQ(system.snapshot().mode, SystemMode::Paused);
  EXPECT_EQ(system.application().state().player_queue.size(), queue_size);
  system.tick();
  EXPECT_EQ(system.application().state().tick, 0U);
  EXPECT_EQ(system.application().stateHash(), hash);

  ASSERT_TRUE(system.handle(SystemInput::ClearShort));
  EXPECT_EQ(system.snapshot().mode, SystemMode::Playing);
  EXPECT_EQ(system.application().state().player_queue.size(), queue_size);
  ASSERT_TRUE(system.handle(SystemInput::ClearShort));
  EXPECT_EQ(system.application().state().player_queue.size(), 0U);
}

TEST(SystemController, RestartKeepsPresetAndSeedButResetsState) {
  SystemController system(29U);
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  const std::uint64_t seed = system.snapshot().active_seed;
  const std::uint8_t map_size = system.snapshot().confirmed_map_size;
  system.tick();
  ASSERT_EQ(system.application().state().tick, 1U);

  ASSERT_TRUE(system.handle(SystemInput::ClearLong));
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Fire));

  EXPECT_EQ(system.snapshot().mode, SystemMode::Playing);
  EXPECT_EQ(system.snapshot().active_seed, seed);
  EXPECT_EQ(system.snapshot().confirmed_map_size, map_size);
  EXPECT_EQ(system.application().state().seed, seed);
  EXPECT_EQ(system.application().state().tick, 0U);
}

TEST(SystemController, LeavingRunRequiresExplicitConfirmation) {
  SystemController system(31U);
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  ASSERT_TRUE(system.handle(SystemInput::ClearLong));
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  ASSERT_EQ(system.snapshot().mode, SystemMode::ConfirmHome);
  EXPECT_EQ(system.snapshot().focus, 0U);

  ASSERT_TRUE(system.handle(SystemInput::Fire));
  EXPECT_EQ(system.snapshot().mode, SystemMode::Paused);
  EXPECT_TRUE(system.snapshot().has_active_session);
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  EXPECT_EQ(system.snapshot().mode, SystemMode::Home);
  EXPECT_FALSE(system.snapshot().has_active_session);
}

TEST(SystemController, OnlyPlayingAdvancesAndAnyTerminalStateOpensResult) {
  SystemController system(37U);
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  ASSERT_TRUE(system.handle(SystemInput::Left));
  ASSERT_EQ(system.snapshot().pending_map_size, 20U);
  ASSERT_TRUE(system.handle(SystemInput::Left));
  ASSERT_EQ(system.snapshot().pending_map_size, 12U);
  ASSERT_TRUE(system.handle(SystemInput::Down));
  ASSERT_TRUE(system.handle(SystemInput::Fire));

  for (std::uint16_t tick = 0U; tick < 480U && system.snapshot().mode == SystemMode::Playing;
       ++tick) {
    system.tick();
  }
  EXPECT_NE(system.application().state().status, core::GameStatus::Running);
  EXPECT_EQ(system.snapshot().mode, SystemMode::Result);
  EXPECT_LE(system.application().state().tick, 480U);
  const std::uint64_t final_hash = system.application().stateHash();
  system.tick();
  EXPECT_EQ(system.application().stateHash(), final_hash);

  const std::uint64_t replay_seed = system.snapshot().active_seed;
  ASSERT_TRUE(system.handle(SystemInput::Fire));
  EXPECT_EQ(system.snapshot().mode, SystemMode::Playing);
  EXPECT_EQ(system.snapshot().active_seed, replay_seed);
  EXPECT_EQ(system.application().state().tick, 0U);
}

TEST(SystemController, StableModeAndPresetLabelsCoverEveryPublicValue) {
  EXPECT_EQ(systemModeName(SystemMode::Home), "HOME");
  EXPECT_EQ(systemModeName(SystemMode::Setup), "SETUP");
  EXPECT_EQ(systemModeName(SystemMode::System), "SYSTEM");
  EXPECT_EQ(systemModeName(SystemMode::About), "ABOUT");
  EXPECT_EQ(systemModeName(SystemMode::Playing), "PLAYING");
  EXPECT_EQ(systemModeName(SystemMode::Paused), "PAUSED");
  EXPECT_EQ(systemModeName(SystemMode::ConfirmHome), "CONFIRM_HOME");
  EXPECT_EQ(systemModeName(SystemMode::Result), "RESULT");
  EXPECT_EQ(mapPresetName(12U), "TINY");
  EXPECT_EQ(mapPresetName(20U), "SMALL");
  EXPECT_EQ(mapPresetName(30U), "MEDIUM");
  EXPECT_EQ(mapPresetName(50U), "ORIGINAL");
  EXPECT_EQ(mapPresetName(13U), "ORIGINAL");
}

}  // namespace
}  // namespace catamaze::app
