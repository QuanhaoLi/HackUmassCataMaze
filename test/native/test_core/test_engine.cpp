// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 03:33 EST
// Last Modified by: Codex
// Verifies deterministic movement, combat, visibility, terminal conditions, and replay hashing.

#include <gtest/gtest.h>

#include <array>
#include <cstddef>

#include "catamaze/core/engine.hpp"

namespace catamaze::core {
namespace {

constexpr std::array<Action, kAiCount> kAiWaits{Action::Wait, Action::Wait, Action::Wait};

GameSetup openSetup() {
  GameSetup setup{};
  setup.seed = 0xabcU;
  setup.map.fill(Terrain::Wall);
  for (std::int16_t y = 1; y <= 8; ++y) {
    for (std::int16_t x = 1; x <= 8; ++x) {
      setup.map.set(Position{x, y}, Terrain::Floor);
    }
  }
  setup.map.set(Position{1, 1}, Terrain::Entrance);
  setup.map.set(Position{0, 1}, Terrain::Exit);
  setup.spawns = {Position{2, 2}, Position{6, 2}, Position{2, 6}, Position{6, 6}};
  return setup;
}

TEST(GameEngine, ConsumesOneQueuedPlayerActionPerTick) {
  GameEngine engine(openSetup());
  ASSERT_TRUE(engine.enqueuePlayerAction(Action::MoveRight));
  ASSERT_TRUE(engine.enqueuePlayerAction(Action::MoveDown));

  engine.step(kAiWaits);
  EXPECT_EQ(engine.state().entities[0].position, (Position{3, 2}));
  EXPECT_EQ(engine.state().player_queue.size(), 1U);
  engine.step(kAiWaits);
  EXPECT_EQ(engine.state().entities[0].position, (Position{3, 3}));
  EXPECT_EQ(engine.state().player_queue.size(), 0U);
}

TEST(GameEngine, StartOccupiedCellsAndSharedTargetsBlockMovement) {
  GameSetup occupied = openSetup();
  occupied.spawns[1] = Position{3, 2};
  GameEngine occupied_engine(occupied);
  ASSERT_TRUE(occupied_engine.enqueuePlayerAction(Action::MoveRight));
  occupied_engine.step(kAiWaits);
  EXPECT_EQ(occupied_engine.state().entities[0].position, (Position{2, 2}));
  EXPECT_EQ(occupied_engine.state().entities[0].last_result, ActionResult::BlockedEntity);

  GameSetup conflict = openSetup();
  conflict.spawns[1] = Position{4, 2};
  GameEngine conflict_engine(conflict);
  ASSERT_TRUE(conflict_engine.enqueuePlayerAction(Action::MoveRight));
  conflict_engine.step({Action::MoveLeft, Action::Wait, Action::Wait});
  EXPECT_EQ(conflict_engine.state().entities[0].position, (Position{2, 2}));
  EXPECT_EQ(conflict_engine.state().entities[1].position, (Position{4, 2}));
  EXPECT_EQ(conflict_engine.state().entities[0].last_result, ActionResult::BlockedConflict);
  EXPECT_EQ(conflict_engine.state().entities[1].last_result, ActionResult::BlockedConflict);
}

TEST(GameEngine, AdjacentShotDamagesImmediatelyAndAmmoRecoversOnPhase) {
  GameSetup setup = openSetup();
  setup.spawns[1] = Position{3, 2};
  GameEngine engine(setup);
  ASSERT_TRUE(engine.enqueuePlayerAction(Action::ShootRight));

  engine.step(kAiWaits);
  EXPECT_EQ(engine.state().entities[1].hp, 4U);
  EXPECT_EQ(engine.state().entities[0].ammo, 2U);
  EXPECT_EQ(engine.state().entities[0].recharge_progress, 1U);
  EXPECT_EQ(engine.state().bullet_count, 0U);

  engine.step(kAiWaits);
  EXPECT_EQ(engine.state().entities[0].ammo, 3U);
  EXPECT_EQ(engine.state().entities[0].recharge_progress, 0U);
}

TEST(GameEngine, SimultaneousLethalHitsPreserveActualDamageAndEveryShooterCredit) {
  GameSetup setup = openSetup();
  setup.spawns[1] = Position{1, 2};
  setup.spawns[2] = Position{3, 2};
  GameEngine engine(setup);
  const std::array<Action, kAiCount> crossfire{Action::ShootRight, Action::ShootLeft,
                                               Action::Wait};

  engine.step(crossfire);
  engine.step(kAiWaits);
  engine.step(crossfire);
  engine.step(kAiWaits);
  ASSERT_EQ(engine.state().entities[0].hp, 1U);

  engine.step(crossfire);

  EXPECT_EQ(engine.state().entities[0].hp, 0U);
  EXPECT_EQ(engine.state().status, GameStatus::Death);
  std::uint8_t applied_damage = 0U;
  std::array<std::uint8_t, kEntityCount> credited_hits{};
  std::size_t damage_events = 0U;
  std::size_t credit_events = 0U;
  std::size_t death_events = 0U;
  for (std::size_t index = 0; index < engine.state().event_count; ++index) {
    const Event& event = engine.state().events[index];
    if (event.type == EventType::DamageApplied && event.target == EntityId::Player) {
      ++damage_events;
      applied_damage = event.value;
    } else if (event.type == EventType::DamageCredit && event.target == EntityId::Player) {
      ++credit_events;
      credited_hits[entityIndex(event.actor)] = event.value;
    } else if (event.type == EventType::EntityDied && event.target == EntityId::Player) {
      ++death_events;
    }
  }
  EXPECT_EQ(damage_events, 1U);
  EXPECT_EQ(applied_damage, 1U);
  EXPECT_EQ(credit_events, 2U);
  EXPECT_EQ(credited_hits[entityIndex(EntityId::Aggressive)], 1U);
  EXPECT_EQ(credited_hits[entityIndex(EntityId::Cautious)], 1U);
  EXPECT_EQ(death_events, 1U);
}

TEST(GameEngine, BulletMovesOneCellPerTickUntilItHits) {
  GameSetup setup = openSetup();
  setup.spawns[1] = Position{5, 2};
  GameEngine engine(setup);
  ASSERT_TRUE(engine.enqueuePlayerAction(Action::ShootRight));

  engine.step(kAiWaits);
  ASSERT_EQ(engine.state().bullet_count, 1U);
  EXPECT_EQ(engine.state().bullets[0].position, (Position{3, 2}));
  engine.step(kAiWaits);
  ASSERT_EQ(engine.state().bullet_count, 1U);
  EXPECT_EQ(engine.state().bullets[0].position, (Position{4, 2}));
  engine.step(kAiWaits);
  EXPECT_EQ(engine.state().bullet_count, 0U);
  EXPECT_EQ(engine.state().entities[1].hp, 4U);
}

TEST(GameEngine, MovingOntoExitWinsAndTicksStopAdvancing) {
  GameSetup setup = openSetup();
  setup.map.set(Position{3, 2}, Terrain::Exit);
  setup.map.set(Position{0, 1}, Terrain::Wall);
  GameEngine engine(setup);
  ASSERT_TRUE(engine.enqueuePlayerAction(Action::MoveRight));
  engine.step(kAiWaits);

  EXPECT_EQ(engine.state().status, GameStatus::Victory);
  EXPECT_EQ(engine.state().tick, 1U);
  engine.step(kAiWaits);
  EXPECT_EQ(engine.state().tick, 1U);
}

TEST(GameEngine, DeathOverridesReachingExitOnTheSameTick) {
  GameSetup setup = openSetup();
  setup.map.set(Position{3, 2}, Terrain::Exit);
  setup.map.set(Position{0, 1}, Terrain::Wall);
  setup.spawns[1] = Position{5, 2};
  setup.spawns[2] = Position{2, 4};
  GameEngine engine(setup);

  for (int hit = 0; hit < 4; ++hit) {
    engine.step({Action::Wait, Action::ShootUp, Action::Wait});
    engine.step(kAiWaits);
  }
  ASSERT_EQ(engine.state().entities[0].hp, 1U);
  engine.step({Action::ShootLeft, Action::Wait, Action::Wait});
  ASSERT_EQ(engine.state().bullet_count, 1U);
  ASSERT_TRUE(engine.enqueuePlayerAction(Action::MoveRight));
  engine.step(kAiWaits);

  EXPECT_EQ(engine.state().entities[0].position, (Position{3, 2}));
  EXPECT_EQ(engine.state().entities[0].hp, 0U);
  EXPECT_EQ(engine.state().status, GameStatus::Death);
}

TEST(GameEngine, TimesOutExactlyAtTwoThousandTicks) {
  GameEngine engine(openSetup());
  for (std::uint16_t tick = 0; tick < kMaxTicks - 1U; ++tick) {
    engine.step(kAiWaits);
    ASSERT_EQ(engine.state().status, GameStatus::Running) << tick;
  }
  engine.step(kAiWaits);
  EXPECT_EQ(engine.state().tick, kMaxTicks);
  EXPECT_EQ(engine.state().status, GameStatus::Timeout);
}

TEST(GameEngine, ObservationHidesCellsBehindWallsAndReportsNearbyShots) {
  GameSetup setup = openSetup();
  setup.map.set(Position{3, 2}, Terrain::Wall);
  setup.spawns[1] = Position{4, 2};
  GameEngine engine(setup);

  Observation before = engine.observe(EntityId::Player);
  EXPECT_TRUE(before.atOffset(1, 0).visible);
  EXPECT_EQ(before.atOffset(1, 0).terrain, Terrain::Wall);
  EXPECT_FALSE(before.atOffset(2, 0).visible);

  engine.step({Action::ShootLeft, Action::Wait, Action::Wait});
  Observation after = engine.observe(EntityId::Player);
  EXPECT_TRUE(after.sound.heard);
  EXPECT_EQ(after.sound.direction_x, 1);
  EXPECT_EQ(after.sound.direction_y, 0);
  EXPECT_EQ(after.sound.distance, 2U);
}

TEST(GameEngine, SameSeedAndCommandsProduceTheSameHash) {
  GameEngine first(0xdeadbeefU);
  GameEngine second(0xdeadbeefU);
  constexpr std::array<Action, 8> actions{Action::MoveUp,   Action::MoveRight, Action::ShootDown,
                                          Action::Wait,     Action::MoveLeft,  Action::ShootUp,
                                          Action::MoveDown, Action::Wait};

  for (std::size_t tick = 0; tick < 128U; ++tick) {
    ASSERT_TRUE(first.enqueuePlayerAction(actions[tick % actions.size()]));
    ASSERT_TRUE(second.enqueuePlayerAction(actions[tick % actions.size()]));
    const std::array<Action, kAiCount> ai{actions[(tick + 1U) % actions.size()],
                                          actions[(tick + 3U) % actions.size()],
                                          actions[(tick + 5U) % actions.size()]};
    first.step(ai);
    second.step(ai);
    ASSERT_EQ(first.stateHash(), second.stateHash()) << tick;
  }
}

}  // namespace
}  // namespace catamaze::core
