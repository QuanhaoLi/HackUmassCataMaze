// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:06 EST
// Last Modified by: Codex
// Verifies portable randomness, deterministic maze generation, and connectivity invariants.

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <cstdint>

#include "catamaze/core/map.hpp"
#include "catamaze/core/random.hpp"

namespace catamaze::core {
namespace {

TEST(Pcg32, RepeatsExactlyForTheSameSeedAndSequence) {
  Pcg32 first(0x123456789abcdef0ULL);
  Pcg32 second(0x123456789abcdef0ULL);
  Pcg32 different(0x123456789abcdef1ULL);

  bool saw_difference = false;
  for (int index = 0; index < 64; ++index) {
    const std::uint32_t expected = first.next();
    EXPECT_EQ(second.next(), expected);
    saw_difference = saw_difference || different.next() != expected;
  }
  EXPECT_TRUE(saw_difference);
  EXPECT_NE(first.state(), 0U);
  EXPECT_EQ(first.increment() & 1U, 1U);
}

TEST(Pcg32, BoundedValuesStayInsideTheRequestedRange) {
  Pcg32 random(42U);
  for (std::uint32_t bound = 1U; bound < 33U; ++bound) {
    for (int sample = 0; sample < 200; ++sample) {
      EXPECT_LT(random.bounded(bound), bound);
    }
  }
  EXPECT_EQ(random.bounded(0U), 0U);
}

TEST(MazeGenerator, SameSeedProducesIdenticalWorld) {
  const GeneratedWorld first = MazeGenerator::generate(0x134fd5aULL);
  const GeneratedWorld second = MazeGenerator::generate(0x134fd5aULL);

  EXPECT_EQ(first.map.cells(), second.map.cells());
  EXPECT_EQ(first.entrance, second.entrance);
  EXPECT_EQ(first.exit, second.exit);
  EXPECT_EQ(first.spawns, second.spawns);
}

TEST(MazeGenerator, EveryReviewedPresetIsDeterministicConnectedAndBounded) {
  for (const std::uint8_t map_size : kMapPresets) {
    const GeneratedWorld first = MazeGenerator::generate(0xc47aU, map_size);
    const GeneratedWorld second = MazeGenerator::generate(0xc47aU, map_size);
    const DistanceField distances = shortestDistances(first.map, first.entrance);

    ASSERT_EQ(first.map.activeSize(), map_size);
    EXPECT_EQ(first.map.cells(), second.map.cells());
    EXPECT_EQ(first.exit, second.exit);
    EXPECT_EQ(first.spawns, second.spawns);

    std::size_t entrance_count = 0U;
    std::size_t exit_count = 0U;
    for (std::int16_t y = 0; y < map_size; ++y) {
      for (std::int16_t x = 0; x < map_size; ++x) {
        const Position position{x, y};
        const Terrain terrain = first.map.at(position);
        entrance_count += terrain == Terrain::Entrance ? 1U : 0U;
        exit_count += terrain == Terrain::Exit ? 1U : 0U;
        if (first.map.isWalkable(position)) {
          const std::size_t index =
              static_cast<std::size_t>(y) * kMapSize + static_cast<std::size_t>(x);
          EXPECT_NE(distances[index], kUnreachableDistance)
              << "preset " << static_cast<unsigned>(map_size) << " at " << x << ',' << y;
        }
        const bool boundary = x == 0 || y == 0 || x == map_size - 1 || y == map_size - 1;
        if (boundary && position != first.exit) EXPECT_EQ(terrain, Terrain::Wall);
      }
    }
    EXPECT_EQ(entrance_count, 1U);
    EXPECT_EQ(exit_count, 1U);
    EXPECT_FALSE(first.map.inBounds(Position{map_size, 0}));
    EXPECT_FALSE(first.map.inBounds(Position{0, map_size}));

    for (std::size_t index = 0; index < first.spawns.size(); ++index) {
      EXPECT_TRUE(first.map.isWalkable(first.spawns[index]));
      EXPECT_NE(first.spawns[index], first.exit);
      for (std::size_t other = index + 1U; other < first.spawns.size(); ++other) {
        EXPECT_NE(first.spawns[index], first.spawns[other]);
      }
    }
  }
}

TEST(MazeGenerator, InvalidPresetFallsBackToOriginalSize) {
  const GeneratedWorld world = MazeGenerator::generate(7U, 13U);
  EXPECT_EQ(world.map.activeSize(), 50U);
  EXPECT_EQ(tickBudgetForMapSize(13U), kMaxTicks);
}

TEST(MazeGenerator, DifferentSeedsChangeTheTerrain) {
  const GeneratedWorld first = MazeGenerator::generate(1U);
  const GeneratedWorld second = MazeGenerator::generate(2U);
  EXPECT_NE(first.map.cells(), second.map.cells());
}

TEST(MazeGenerator, ProducesOneReachableExitAndDistinctSpawns) {
  const GeneratedWorld world = MazeGenerator::generate(20261114U);
  const DistanceField distances = shortestDistances(world.map, world.entrance);

  std::size_t entrance_count = 0U;
  std::size_t exit_count = 0U;
  for (std::int16_t y = 0; y < kMapSize; ++y) {
    for (std::int16_t x = 0; x < kMapSize; ++x) {
      const Position position{x, y};
      const Terrain terrain = world.map.at(position);
      entrance_count += terrain == Terrain::Entrance ? 1U : 0U;
      exit_count += terrain == Terrain::Exit ? 1U : 0U;
      if (world.map.isWalkable(position)) {
        const std::size_t index =
            static_cast<std::size_t>(y) * kMapSize + static_cast<std::size_t>(x);
        EXPECT_NE(distances[index], kUnreachableDistance)
            << "unreachable walkable cell at " << x << ',' << y;
      }
      const bool boundary = x == 0 || y == 0 || x == kMapSize - 1 || y == kMapSize - 1;
      if (boundary && position != world.exit) {
        EXPECT_EQ(terrain, Terrain::Wall);
      }
    }
  }
  EXPECT_EQ(entrance_count, 1U);
  EXPECT_EQ(exit_count, 1U);
  EXPECT_EQ(world.map.at(world.exit), Terrain::Exit);

  for (std::size_t index = 0; index < world.spawns.size(); ++index) {
    EXPECT_TRUE(world.map.isWalkable(world.spawns[index]));
    EXPECT_NE(world.spawns[index], world.exit);
    for (std::size_t other = index + 1U; other < world.spawns.size(); ++other) {
      EXPECT_NE(world.spawns[index], world.spawns[other]);
    }
  }
  EXPECT_EQ(world.spawns[entityIndex(EntityId::Player)], world.entrance);
}

}  // namespace
}  // namespace catamaze::core
