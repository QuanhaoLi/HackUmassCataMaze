// Created at: 2026-11-14 07:36 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:36 EST
// Last Modified by: Codex
// Verifies wrap-safe physical debounce, FIRE ordering, no repeat, and CLEAR gesture suppression.

#include <gtest/gtest.h>

#include <cstdint>
#include <limits>

#include "catamaze/app/six_button_input.hpp"

namespace catamaze::app {
namespace {

ButtonLevels releasedButtons() { return ButtonLevels{true, true, true, true, true, true}; }

void expectOne(const ButtonEvents& events, SystemInput input) {
  ASSERT_EQ(events.count, 1U);
  EXPECT_EQ(events.values[0], input);
}

TEST(SixButtonInput, FirstPollAdoptsPhysicalLevelsWithoutGeneratingAnEvent) {
  SixButtonInput input;
  ButtonLevels levels = releasedButtons();
  levels[static_cast<std::size_t>(PhysicalButton::Up)] = false;
  EXPECT_EQ(input.poll(100U, levels, false).count, 0U);
  EXPECT_EQ(input.poll(1000U, levels, false).count, 0U);
}

TEST(SixButtonInput, DebouncesPressesAndNeverRepeatsWhileHeld) {
  SixButtonInput input;
  ButtonLevels levels = releasedButtons();
  input.begin(0U, levels);
  levels[static_cast<std::size_t>(PhysicalButton::Up)] = false;
  EXPECT_EQ(input.poll(1U, levels, false).count, 0U);
  EXPECT_EQ(input.poll(20U, levels, false).count, 0U);
  expectOne(input.poll(21U, levels, false), SystemInput::Up);
  EXPECT_EQ(input.poll(500U, levels, false).count, 0U);

  levels[static_cast<std::size_t>(PhysicalButton::Up)] = true;
  EXPECT_EQ(input.poll(501U, levels, false).count, 0U);
  EXPECT_EQ(input.poll(521U, levels, false).count, 0U);
  levels[static_cast<std::size_t>(PhysicalButton::Up)] = false;
  EXPECT_EQ(input.poll(522U, levels, false).count, 0U);
  expectOne(input.poll(542U, levels, false), SystemInput::Up);
}

TEST(SixButtonInput, FireMustBeStableBeforeDirectionAndOnlyModifiesGameplay) {
  SixButtonInput input;
  ButtonLevels levels = releasedButtons();
  input.begin(0U, levels);
  levels[static_cast<std::size_t>(PhysicalButton::Right)] = false;
  levels[static_cast<std::size_t>(PhysicalButton::Fire)] = false;
  input.poll(1U, levels, true);
  const ButtonEvents simultaneous = input.poll(21U, levels, true);
  ASSERT_EQ(simultaneous.count, 2U);
  EXPECT_EQ(simultaneous.values[0], SystemInput::Right);
  EXPECT_EQ(simultaneous.values[1], SystemInput::Fire);

  levels = releasedButtons();
  input.poll(22U, levels, true);
  input.poll(42U, levels, true);
  levels[static_cast<std::size_t>(PhysicalButton::Fire)] = false;
  input.poll(50U, levels, true);
  expectOne(input.poll(70U, levels, true), SystemInput::Fire);
  levels[static_cast<std::size_t>(PhysicalButton::Right)] = false;
  input.poll(71U, levels, true);
  expectOne(input.poll(91U, levels, true), SystemInput::ShootRight);

  levels[static_cast<std::size_t>(PhysicalButton::Right)] = true;
  input.poll(92U, levels, false);
  input.poll(112U, levels, false);
  levels[static_cast<std::size_t>(PhysicalButton::Right)] = false;
  input.poll(113U, levels, false);
  expectOne(input.poll(133U, levels, false), SystemInput::Right);
}

TEST(SixButtonInput, ClearShortCommitsOnlyAfterDebouncedRelease) {
  SixButtonInput input;
  ButtonLevels levels = releasedButtons();
  input.begin(0U, levels);
  levels[static_cast<std::size_t>(PhysicalButton::Clear)] = false;
  input.poll(1U, levels, true);
  EXPECT_EQ(input.poll(21U, levels, true).count, 0U);
  levels[static_cast<std::size_t>(PhysicalButton::Clear)] = true;
  EXPECT_EQ(input.poll(100U, levels, true).count, 0U);
  expectOne(input.poll(120U, levels, true), SystemInput::ClearShort);
}

TEST(SixButtonInput, ClearLongCommitsOnceAndSuppressesReleaseShort) {
  SixButtonInput input;
  ButtonLevels levels = releasedButtons();
  input.begin(0U, levels);
  levels[static_cast<std::size_t>(PhysicalButton::Clear)] = false;
  input.poll(1U, levels, true);
  input.poll(21U, levels, true);
  EXPECT_EQ(input.poll(820U, levels, true).count, 0U);
  expectOne(input.poll(821U, levels, true), SystemInput::ClearLong);
  EXPECT_EQ(input.poll(900U, levels, true).count, 0U);
  levels[static_cast<std::size_t>(PhysicalButton::Clear)] = true;
  input.poll(901U, levels, true);
  EXPECT_EQ(input.poll(921U, levels, true).count, 0U);
}

TEST(SixButtonInput, RawReleaseBeforeThresholdRemainsAShortPress) {
  SixButtonInput input;
  ButtonLevels levels = releasedButtons();
  input.begin(0U, levels);
  levels[static_cast<std::size_t>(PhysicalButton::Clear)] = false;
  input.poll(1U, levels, true);
  input.poll(21U, levels, true);
  levels[static_cast<std::size_t>(PhysicalButton::Clear)] = true;
  EXPECT_EQ(input.poll(820U, levels, true).count, 0U);
  EXPECT_EQ(input.poll(821U, levels, true).count, 0U);
  expectOne(input.poll(840U, levels, true), SystemInput::ClearShort);
}

TEST(SixButtonInput, ClearHeldDuringBootIsIgnoredUntilACompleteNewGesture) {
  SixButtonInput input;
  ButtonLevels levels = releasedButtons();
  levels[static_cast<std::size_t>(PhysicalButton::Clear)] = false;
  input.begin(0U, levels);
  EXPECT_EQ(input.poll(1000U, levels, true).count, 0U);
  levels[static_cast<std::size_t>(PhysicalButton::Clear)] = true;
  input.poll(1001U, levels, true);
  EXPECT_EQ(input.poll(1021U, levels, true).count, 0U);
  levels[static_cast<std::size_t>(PhysicalButton::Clear)] = false;
  input.poll(1022U, levels, true);
  input.poll(1042U, levels, true);
  levels[static_cast<std::size_t>(PhysicalButton::Clear)] = true;
  input.poll(1100U, levels, true);
  expectOne(input.poll(1120U, levels, true), SystemInput::ClearShort);
}

TEST(SixButtonInput, DebounceTimeRemainsCorrectAcrossMillisWraparound) {
  SixButtonInput input;
  ButtonLevels levels = releasedButtons();
  constexpr std::uint32_t kNearWrap = std::numeric_limits<std::uint32_t>::max() - 10U;
  input.begin(kNearWrap, levels);
  levels[static_cast<std::size_t>(PhysicalButton::Down)] = false;
  input.poll(static_cast<std::uint32_t>(kNearWrap + 1U), levels, false);
  EXPECT_EQ(input.poll(9U, levels, false).count, 0U);
  expectOne(input.poll(10U, levels, false), SystemInput::Down);
}

}  // namespace
}  // namespace catamaze::app
