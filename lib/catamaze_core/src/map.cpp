// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:32 EST
// Last Modified by: Codex
// Implements the fixed 50x50 terrain map and versioned dfs-grid-v1 generator.

#include "catamaze/core/map.hpp"

#include <algorithm>
#include <array>
#include <cstddef>

#include "catamaze/core/random.hpp"

namespace catamaze::core {
namespace {

constexpr std::int16_t kLogicalSide = 24;
constexpr std::size_t kLogicalCellCount =
    static_cast<std::size_t>(kLogicalSide) * kLogicalSide;

std::size_t mapIndex(Position position) noexcept {
  return static_cast<std::size_t>(position.y) * kMapSize +
         static_cast<std::size_t>(position.x);
}

std::size_t logicalIndex(Position position) noexcept {
  const auto logical_x = static_cast<std::size_t>((position.x - 1) / 2);
  const auto logical_y = static_cast<std::size_t>((position.y - 1) / 2);
  return logical_y * kLogicalSide + logical_x;
}

bool isLogicalCell(Position position) noexcept {
  return position.x >= 1 && position.x <= 47 && position.y >= 1 &&
         position.y <= 47 && (position.x % 2) == 1 &&
         (position.y % 2) == 1;
}

bool isPerimeterLogicalCell(Position position) noexcept {
  return position.x == 1 || position.x == 47 || position.y == 1 ||
         position.y == 47;
}

void shuffleDirections(std::array<Direction, 4>& directions,
                       Pcg32& random) noexcept {
  for (std::size_t remaining = directions.size(); remaining > 1U;
       --remaining) {
    const std::size_t selected = random.bounded(
        static_cast<std::uint32_t>(remaining));
    std::swap(directions[remaining - 1U], directions[selected]);
  }
}

}  // namespace

Map::Map() noexcept { fill(Terrain::Wall); }

bool Map::inBounds(Position position) const noexcept {
  return position.x >= 0 && position.x < kMapSize && position.y >= 0 &&
         position.y < kMapSize;
}

std::size_t Map::index(Position position) noexcept { return mapIndex(position); }

Terrain Map::at(Position position) const noexcept {
  return inBounds(position) ? cells_[index(position)] : Terrain::Wall;
}

bool Map::isWalkable(Position position) const noexcept {
  if (!inBounds(position)) {
    return false;
  }
  return at(position) != Terrain::Wall;
}

void Map::fill(Terrain terrain) noexcept { cells_.fill(terrain); }

bool Map::set(Position position, Terrain terrain) noexcept {
  if (!inBounds(position)) {
    return false;
  }
  cells_[index(position)] = terrain;
  return true;
}

DistanceField shortestDistances(const Map& map, Position start) noexcept {
  DistanceField distances{};
  distances.fill(kUnreachableDistance);
  if (!map.isWalkable(start)) {
    return distances;
  }

  std::array<Position, kMapCellCount> queue{};
  std::size_t head = 0U;
  std::size_t tail = 0U;
  queue[tail++] = start;
  distances[mapIndex(start)] = 0;

  constexpr std::array<Direction, 4> kDirections{
      Direction::Up, Direction::Right, Direction::Down, Direction::Left};
  while (head < tail) {
    const Position current = queue[head++];
    const std::int16_t next_distance =
        static_cast<std::int16_t>(distances[mapIndex(current)] + 1);
    for (Direction direction : kDirections) {
      const Position next = moved(current, direction);
      if (!map.isWalkable(next) ||
          distances[mapIndex(next)] != kUnreachableDistance) {
        continue;
      }
      distances[mapIndex(next)] = next_distance;
      queue[tail++] = next;
    }
  }
  return distances;
}

GeneratedWorld MazeGenerator::generate(std::uint64_t seed) noexcept {
  GeneratedWorld world{};
  world.seed = seed;
  world.map.fill(Terrain::Wall);
  world.entrance = Position{1, 1};

  Pcg32 random(seed);
  std::array<bool, kLogicalCellCount> visited{};
  std::array<Position, kLogicalCellCount> stack{};
  std::size_t stack_size = 0U;

  visited[logicalIndex(world.entrance)] = true;
  world.map.set(world.entrance, Terrain::Floor);
  stack[stack_size++] = world.entrance;

  while (stack_size > 0U) {
    const Position current = stack[stack_size - 1U];
    std::array<Direction, 4> directions{
        Direction::Up, Direction::Right, Direction::Down, Direction::Left};
    shuffleDirections(directions, random);

    bool advanced = false;
    for (Direction direction : directions) {
      const Position one_step = moved(current, direction);
      const Position next = moved(one_step, direction);
      if (!isLogicalCell(next) || visited[logicalIndex(next)]) {
        continue;
      }
      visited[logicalIndex(next)] = true;
      world.map.set(one_step, Terrain::Floor);
      world.map.set(next, Terrain::Floor);
      stack[stack_size++] = next;
      advanced = true;
      break;
    }
    if (!advanced) {
      --stack_size;
    }
  }

  world.map.set(world.entrance, Terrain::Entrance);
  const DistanceField distances = shortestDistances(world.map, world.entrance);

  Position exit_neighbor = world.entrance;
  std::int16_t greatest_distance = kUnreachableDistance;
  for (std::int16_t y = 1; y <= 47; y += 2) {
    for (std::int16_t x = 1; x <= 47; x += 2) {
      const Position candidate{x, y};
      if (candidate == world.entrance || !isPerimeterLogicalCell(candidate)) {
        continue;
      }
      const std::int16_t distance = distances[mapIndex(candidate)];
      if (distance > greatest_distance) {
        greatest_distance = distance;
        exit_neighbor = candidate;
      }
    }
  }

  if (exit_neighbor.x == 47) {
    world.exit = Position{49, exit_neighbor.y};
    world.map.set(Position{48, exit_neighbor.y}, Terrain::Floor);
  } else if (exit_neighbor.y == 47) {
    world.exit = Position{exit_neighbor.x, 49};
    world.map.set(Position{exit_neighbor.x, 48}, Terrain::Floor);
  } else if (exit_neighbor.x == 1) {
    world.exit = Position{0, exit_neighbor.y};
  } else {
    world.exit = Position{exit_neighbor.x, 0};
  }
  world.map.set(world.exit, Terrain::Exit);

  world.spawns[entityIndex(EntityId::Player)] = world.entrance;
  std::array<Position, kMapCellCount> candidates{};
  std::size_t candidate_count = 0U;
  for (std::int16_t y = 0; y < kMapSize; ++y) {
    for (std::int16_t x = 0; x < kMapSize; ++x) {
      const Position candidate{x, y};
      if (candidate != world.entrance && candidate != world.exit &&
          world.map.isWalkable(candidate)) {
        candidates[candidate_count++] = candidate;
      }
    }
  }
  std::sort(candidates.begin(), candidates.begin() +
                static_cast<std::ptrdiff_t>(candidate_count),
            [&distances](Position lhs, Position rhs) {
              const auto left_distance = distances[mapIndex(lhs)];
              const auto right_distance = distances[mapIndex(rhs)];
              if (left_distance != right_distance) {
                return left_distance > right_distance;
              }
              if (lhs.y != rhs.y) {
                return lhs.y < rhs.y;
              }
              return lhs.x < rhs.x;
            });

  for (std::size_t ai = 0U; ai < kAiCount; ++ai) {
    world.spawns[ai + 1U] = candidates[ai];
  }
  return world;
}

}  // namespace catamaze::core
