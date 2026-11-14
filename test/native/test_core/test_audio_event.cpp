// Created at: 2026-11-14 04:37 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:50 EST
// Last Modified by: Codex
// Verifies canonical event names, hearing bounds, terminal mapping, and priority arbitration.

#include <gtest/gtest.h>

#include <array>
#include <string_view>

#include "catamaze/app/audio_event.hpp"

namespace catamaze::app {
namespace {

core::WorldState baseState() {
  core::WorldState state{};
  state.entities[core::entityIndex(core::EntityId::Player)].position = {10, 10};
  return state;
}

void addEvent(core::WorldState& state, core::Event event) {
  ASSERT_LT(state.event_count, state.events.size());
  state.events[state.event_count++] = event;
}

TEST(AudioEvent, NamesAndPrioritiesAreFrozen) {
  EXPECT_EQ(audioEventName(AudioEvent::None), "NONE");
  EXPECT_EQ(audioEventName(AudioEvent::PlayerShot), "PLAYER_SHOT");
  EXPECT_EQ(audioEventName(AudioEvent::EnemyShotHeard), "ENEMY_SHOT_HEARD");
  EXPECT_EQ(audioEventName(AudioEvent::PlayerDamage), "PLAYER_DAMAGE");
  EXPECT_EQ(audioEventName(AudioEvent::PlayerDeath), "PLAYER_DEATH");
  EXPECT_EQ(audioEventName(AudioEvent::PlayerVictory), "PLAYER_VICTORY");
  EXPECT_LT(audioEventPriority(AudioEvent::PlayerShot),
            audioEventPriority(AudioEvent::EnemyShotHeard));
  EXPECT_LT(audioEventPriority(AudioEvent::EnemyShotHeard),
            audioEventPriority(AudioEvent::PlayerDamage));
  EXPECT_LT(audioEventPriority(AudioEvent::PlayerDamage),
            audioEventPriority(AudioEvent::PlayerDeath));
  EXPECT_EQ(audioEventPriority(AudioEvent::PlayerDeath),
            audioEventPriority(AudioEvent::PlayerVictory));
}

TEST(AudioEvent, PlayerShotAndEnemyHearingArePlayerObservable) {
  auto player_shot = baseState();
  addEvent(player_shot, {core::EventType::Shot,
                         core::EntityId::Player,
                         core::EntityId::Player,
                         {10, 10},
                         core::Direction::Right,
                         1});
  EXPECT_EQ(selectAudioEvent(player_shot), AudioEvent::PlayerShot);

  auto nearby_enemy = baseState();
  addEvent(nearby_enemy, {core::EventType::Shot,
                          core::EntityId::Aggressive,
                          core::EntityId::Aggressive,
                          {13, 7},
                          core::Direction::Left,
                          1});
  EXPECT_EQ(selectAudioEvent(nearby_enemy), AudioEvent::EnemyShotHeard);

  auto distant_enemy = baseState();
  addEvent(distant_enemy, {core::EventType::Shot,
                           core::EntityId::Aggressive,
                           core::EntityId::Aggressive,
                           {14, 10},
                           core::Direction::Left,
                           1});
  EXPECT_EQ(selectAudioEvent(distant_enemy), AudioEvent::None);
}

TEST(AudioEvent, HighestPriorityWinsWithinOneTick) {
  auto state = baseState();
  addEvent(state, {core::EventType::Shot,
                   core::EntityId::Player,
                   core::EntityId::Player,
                   {10, 10},
                   core::Direction::Right,
                   1});
  addEvent(state, {core::EventType::Shot,
                   core::EntityId::Aggressive,
                   core::EntityId::Aggressive,
                   {11, 10},
                   core::Direction::Left,
                   1});
  addEvent(state, {core::EventType::DamageApplied,
                   core::EntityId::Aggressive,
                   core::EntityId::Player,
                   {10, 10},
                   core::Direction::Left,
                   1});
  EXPECT_EQ(selectAudioEvent(state), AudioEvent::PlayerDamage);

  state.status = core::GameStatus::Death;
  addEvent(state, {core::EventType::GameEnded,
                   core::EntityId::Player,
                   core::EntityId::Player,
                   {10, 10},
                   core::Direction::Up,
                   0});
  EXPECT_EQ(selectAudioEvent(state), AudioEvent::PlayerDeath);
}

TEST(AudioEvent, VictoryMapsAndTimeoutRemainsSilent) {
  auto victory = baseState();
  victory.status = core::GameStatus::Victory;
  addEvent(victory, {core::EventType::GameEnded,
                     core::EntityId::Player,
                     core::EntityId::Player,
                     {10, 10},
                     core::Direction::Up,
                     0});
  EXPECT_EQ(selectAudioEvent(victory), AudioEvent::PlayerVictory);

  auto timeout = baseState();
  timeout.status = core::GameStatus::Timeout;
  addEvent(timeout, {core::EventType::GameEnded,
                     core::EntityId::Player,
                     core::EntityId::Player,
                     {10, 10},
                     core::Direction::Up,
                     0});
  EXPECT_EQ(selectAudioEvent(timeout), AudioEvent::None);
}

TEST(AudioEvent, SerialLineIsBoundedStableAndContainsNoHiddenState) {
  std::array<char, 128> output{};
  const std::size_t size =
      formatAudioSerialLine(AudioEvent::PlayerDamage, 42U, 125U, output.data(), output.size());
  constexpr std::string_view expected =
      "CATAMAZE_AUDIO {\"schema\":\"catamaze.audio.v1\",\"seq\":42,"
      "\"tick\":125,\"event\":\"PLAYER_DAMAGE\"}\n";
  EXPECT_EQ(std::string_view(output.data(), size), expected);
  EXPECT_LT(size, output.size());
  EXPECT_EQ(std::string_view(output.data(), size).find("position"), std::string_view::npos);
  EXPECT_EQ(std::string_view(output.data(), size).find("direction"), std::string_view::npos);

  std::array<char, 16> too_small{};
  EXPECT_EQ(
      formatAudioSerialLine(AudioEvent::PlayerShot, 1U, 1U, too_small.data(), too_small.size()),
      0U);
  EXPECT_EQ(too_small[0], '\0');
  EXPECT_EQ(formatAudioSerialLine(AudioEvent::None, 1U, 1U, output.data(), output.size()), 0U);
}

}  // namespace
}  // namespace catamaze::app
