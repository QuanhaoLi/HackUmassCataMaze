// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:18 EST
// Last Modified by: Codex
// Implements fixed 50x50 storage and the preset-aware versioned dfs-grid-v2 generator.

#include "catamaze/core/map.hpp"

#include <algorithm>
#include <array>
#include <cstddef>

#include "catamaze/core/random.hpp"

namespace catamaze::core {
namespace {

constexpr std::int16_t kMaxLogicalSide = 24;
constexpr std::size_t kLogicalCellCount =
    static_cast<std::size_t>(kMaxLogicalSide) * kMaxLogicalSide;

std::size_t mapIndex(Position position) noexcept {
  return static_cast<std::size_t>(position.y) * kMapSize + static_cast<std::size_t>(position.x);
}

Position positionFromMapIndex(std::uint16_t index) noexcept {
  return Position{static_cast<std::int16_t>(index % kMapSize),
                  static_cast<std::int16_t>(index / kMapSize)};
}

std::size_t logicalIndex(Position position, std::int16_t logical_side) noexcept {
  const auto logical_x = static_cast<std::size_t>((position.x - 1) / 2);
  const auto logical_y = static_cast<std::size_t>((position.y - 1) / 2);
  return logical_y * static_cast<std::size_t>(logical_side) + logical_x;
}

bool isLogicalCell(Position position, std::int16_t last_logical) noexcept {
  return position.x >= 1 && position.x <= last_logical && position.y >= 1 &&
         position.y <= last_logical && (position.x % 2) == 1 && (position.y % 2) == 1;
}

bool isPerimeterLogicalCell(Position position, std::int16_t last_logical) noexcept {
  return position.x == 1 || position.x == last_logical || position.y == 1 ||
         position.y == last_logical;
}

void shuffleDirections(std::array<Direction, 4>& directions, Pcg32& random) noexcept {
  for (std::size_t remaining = directions.size(); remaining > 1U; --remaining) {
    const std::size_t selected = random.bounded(static_cast<std::uint32_t>(remaining));
    std::swap(directions[remaining - 1U], directions[selected]);
  }
}

}  // namespace

Map::Map() noexcept { fill(Terrain::Wall); }

bool Map::inBounds(Position position) const noexcept {
  return position.x >= 0 && position.x < active_size_ && position.y >= 0 &&
         position.y < active_size_;
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

bool Map::setActiveSize(std::uint8_t active_size) noexcept {
  if (!isValidMapSize(active_size)) return false;
  active_size_ = active_size;
  return true;
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

  std::array<std::uint16_t, kMapCellCount> queue{};
  std::size_t head = 0U;
  std::size_t tail = 0U;
  queue[tail++] = static_cast<std::uint16_t>(mapIndex(start));
  distances[mapIndex(start)] = 0;

  constexpr std::array<Direction, 4> kDirections{Direction::Up, Direction::Right, Direction::Down,
                                                 Direction::Left};
  while (head < tail) {
    const Position current = positionFromMapIndex(queue[head++]);
    const std::int16_t next_distance = static_cast<std::int16_t>(distances[mapIndex(current)] + 1);
    for (Direction direction : kDirections) {
      const Position next = moved(current, direction);
      if (!map.isWalkable(next) || distances[mapIndex(next)] != kUnreachableDistance) {
        continue;
      }
      distances[mapIndex(next)] = next_distance;
      queue[tail++] = static_cast<std::uint16_t>(mapIndex(next));
    }
  }
  return distances;
}

GeneratedWorld MazeGenerator::generate(std::uint64_t seed, std::uint8_t map_size) noexcept {
  if (!isValidMapSize(map_size)) map_size = static_cast<std::uint8_t>(kMapSize);
  GeneratedWorld world{};
  world.seed = seed;
  world.map.setActiveSize(map_size);
  world.map.fill(Terrain::Wall);
  world.entrance = Position{1, 1};
  const std::int16_t logical_side = static_cast<std::int16_t>((map_size - 2U) / 2U);
  const std::int16_t last_logical = static_cast<std::int16_t>(map_size - 3U);

  Pcg32 random(seed);
  std::array<bool, kLogicalCellCount> visited{};
  std::array<std::uint16_t, kLogicalCellCount> stack{};
  std::size_t stack_size = 0U;

  visited[logicalIndex(world.entrance, logical_side)] = true;
  world.map.set(world.entrance, Terrain::Floor);
  stack[stack_size++] = static_cast<std::uint16_t>(mapIndex(world.entrance));

  while (stack_size > 0U) {
    const Position current = positionFromMapIndex(stack[stack_size - 1U]);
    std::array<Direction, 4> directions{Direction::Up, Direction::Right, Direction::Down,
                                        Direction::Left};
    shuffleDirections(directions, random);

    bool advanced = false;
    for (Direction direction : directions) {
      const Position one_step = moved(current, direction);
      const Position next = moved(one_step, direction);
      if (!isLogicalCell(next, last_logical) || visited[logicalIndex(next, logical_side)]) {
        continue;
      }
      visited[logicalIndex(next, logical_side)] = true;
      world.map.set(one_step, Terrain::Floor);
      world.map.set(next, Terrain::Floor);
      stack[stack_size++] = static_cast<std::uint16_t>(mapIndex(next));
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
  for (std::int16_t y = 1; y <= last_logical; y += 2) {
    for (std::int16_t x = 1; x <= last_logical; x += 2) {
      const Position candidate{x, y};
      if (candidate == world.entrance || !isPerimeterLogicalCell(candidate, last_logical)) {
        continue;
      }
      const std::int16_t distance = distances[mapIndex(candidate)];
      if (distance > greatest_distance) {
        greatest_distance = distance;
        exit_neighbor = candidate;
      }
    }
  }

  const std::int16_t boundary = static_cast<std::int16_t>(map_size - 1U);
  const std::int16_t connector = static_cast<std::int16_t>(map_size - 2U);
  if (exit_neighbor.x == last_logical) {
    world.exit = Position{boundary, exit_neighbor.y};
    world.map.set(Position{connector, exit_neighbor.y}, Terrain::Floor);
  } else if (exit_neighbor.y == last_logical) {
    world.exit = Position{exit_neighbor.x, boundary};
    world.map.set(Position{exit_neighbor.x, connector}, Terrain::Floor);
  } else if (exit_neighbor.x == 1) {
    world.exit = Position{0, exit_neighbor.y};
  } else {
    world.exit = Position{exit_neighbor.x, 0};
  }
  world.map.set(world.exit, Terrain::Exit);

  world.spawns[entityIndex(EntityId::Player)] = world.entrance;
  std::array<std::uint16_t, kMapCellCount> candidates{};
  std::size_t candidate_count = 0U;
  for (std::int16_t y = 0; y < map_size; ++y) {
    for (std::int16_t x = 0; x < map_size; ++x) {
      const Position candidate{x, y};
      if (candidate != world.entrance && candidate != world.exit &&
          world.map.isWalkable(candidate)) {
        candidates[candidate_count++] = static_cast<std::uint16_t>(mapIndex(candidate));
      }
    }
  }
  std::sort(candidates.begin(), candidates.begin() + static_cast<std::ptrdiff_t>(candidate_count),
            [&distances](std::uint16_t lhs_index, std::uint16_t rhs_index) {
              const Position lhs = positionFromMapIndex(lhs_index);
              const Position rhs = positionFromMapIndex(rhs_index);
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
    world.spawns[ai + 1U] = positionFromMapIndex(candidates[ai]);
  }
  return world;
}

}  // namespace catamaze::core
