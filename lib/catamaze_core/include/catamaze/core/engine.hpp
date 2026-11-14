// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Declares deterministic state, observations, and one-tick world transitions.

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "catamaze/core/action_queue.hpp"
#include "catamaze/core/map.hpp"
#include "catamaze/core/types.hpp"

namespace catamaze::core {

struct ObservedCell {
  bool visible{false};
  Terrain terrain{Terrain::Wall};
  std::int8_t entity{-1};
  bool bullet{false};
  Direction bullet_direction{Direction::Up};
};

struct SoundObservation {
  bool heard{false};
  std::int8_t direction_x{0};
  std::int8_t direction_y{0};
  std::uint8_t distance{0};
};

struct Observation {
  std::array<ObservedCell, 25> cells{};
  EntityState self{};
  SoundObservation sound{};

  const ObservedCell& atOffset(std::int8_t dx, std::int8_t dy) const noexcept;
};

struct GameSetup {
  Map map{};
  std::array<Position, kEntityCount> spawns{};
  std::uint64_t seed{0};
};

struct WorldState {
  Map map{};
  std::array<EntityState, kEntityCount> entities{};
  std::array<Bullet, kMaxBullets> bullets{};
  std::size_t bullet_count{0};
  ActionQueue player_queue{};
  std::array<Event, kMaxEvents> events{};
  std::size_t event_count{0};
  std::uint16_t tick{0};
  GameStatus status{GameStatus::Running};
  std::uint64_t seed{0};
};

class GameEngine {
 public:
  explicit GameEngine(std::uint64_t seed) noexcept;
  explicit GameEngine(const GameSetup& setup) noexcept;

  void reset(std::uint64_t seed) noexcept;
  bool enqueuePlayerAction(Action action) noexcept;
  void clearPlayerQueue() noexcept;
  void step(const std::array<Action, kAiCount>& ai_actions) noexcept;

  Observation observe(EntityId observer) const noexcept;
  std::uint64_t stateHash() const noexcept;

  const WorldState& state() const noexcept { return state_; }

 private:
  void initialize(const GameSetup& setup) noexcept;
  void addEvent(const Event& event) noexcept;
  bool hasLineOfSight(Position from, Position to) const noexcept;
  std::int8_t entityAt(Position position, EntityId ignored) const noexcept;

  WorldState state_{};
};

}  // namespace catamaze::core
