// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:32 EST
// Last Modified by: Codex
// Declares fixed terrain storage, path distances, and deterministic maze generation.

#pragma once

#include <array>
#include <cstdint>

#include "catamaze/core/types.hpp"

namespace catamaze::core {

class Map {
 public:
  Map() noexcept;

  bool inBounds(Position position) const noexcept;
  Terrain at(Position position) const noexcept;
  bool isWalkable(Position position) const noexcept;
  void fill(Terrain terrain) noexcept;
  bool set(Position position, Terrain terrain) noexcept;
  const std::array<Terrain, kMapCellCount>& cells() const noexcept {
    return cells_;
  }

 private:
  static std::size_t index(Position position) noexcept;
  std::array<Terrain, kMapCellCount> cells_{};
};

inline constexpr std::int16_t kUnreachableDistance = -1;
using DistanceField = std::array<std::int16_t, kMapCellCount>;

DistanceField shortestDistances(const Map& map, Position start) noexcept;

struct GeneratedWorld {
  Map map{};
  Position entrance{};
  Position exit{};
  std::array<Position, kEntityCount> spawns{};
  std::uint64_t seed{0};
};

class MazeGenerator {
 public:
  static GeneratedWorld generate(std::uint64_t seed) noexcept;
};

}  // namespace catamaze::core
