// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:02 EST
// Last Modified by: Codex
// Declares stable, platform-independent CataMaze domain values and limits.

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string_view>

namespace catamaze::core {

inline constexpr std::int16_t kMapSize = 50;
inline constexpr std::size_t kMapCellCount =
    static_cast<std::size_t>(kMapSize) * static_cast<std::size_t>(kMapSize);
inline constexpr std::size_t kEntityCount = 4;
inline constexpr std::size_t kAiCount = 3;
inline constexpr std::size_t kPlayerQueueCapacity = 32;
inline constexpr std::size_t kMaxBullets = 128;
inline constexpr std::size_t kMaxEvents = 192;
inline constexpr std::uint16_t kMaxTicks = 2000;
inline constexpr std::uint8_t kMaxHp = 5;
inline constexpr std::uint8_t kMaxAmmo = 3;
inline constexpr std::array<std::uint8_t, 4> kMapPresets{12U, 20U, 30U, 50U};

constexpr bool isValidMapSize(std::uint8_t size) noexcept {
  for (std::uint8_t preset : kMapPresets) {
    if (size == preset) return true;
  }
  return false;
}

constexpr std::uint16_t tickBudgetForMapSize(std::uint8_t size) noexcept {
  return isValidMapSize(size) ? static_cast<std::uint16_t>(size * 40U) : kMaxTicks;
}

struct GameConfig {
  std::uint8_t map_size{50U};
  std::uint64_t seed{0U};
};

struct Position {
  std::int16_t x{0};
  std::int16_t y{0};
};

constexpr bool operator==(Position lhs, Position rhs) noexcept {
  return lhs.x == rhs.x && lhs.y == rhs.y;
}

constexpr bool operator!=(Position lhs, Position rhs) noexcept { return !(lhs == rhs); }

enum class Direction : std::uint8_t { Up = 0, Right = 1, Down = 2, Left = 3 };

enum class Action : std::uint8_t {
  MoveUp = 0,
  MoveDown = 1,
  MoveLeft = 2,
  MoveRight = 3,
  ShootUp = 4,
  ShootDown = 5,
  ShootLeft = 6,
  ShootRight = 7,
  Wait = 8,
};

enum class Terrain : std::uint8_t {
  Wall = 0,
  Floor = 1,
  Entrance = 2,
  Exit = 3,
};

enum class EntityId : std::uint8_t {
  Player = 0,
  Aggressive = 1,
  Cautious = 2,
  Explorer = 3,
};

enum class Persona : std::uint8_t {
  Player = 0,
  Aggressive = 1,
  Cautious = 2,
  Explorer = 3,
};

enum class GameStatus : std::uint8_t {
  Running = 0,
  Victory = 1,
  Death = 2,
  Timeout = 3,
};

enum class ActionResult : std::uint8_t {
  None = 0,
  Moved = 1,
  BlockedWall = 2,
  BlockedEntity = 3,
  BlockedConflict = 4,
  BlockedBounds = 5,
  Shot = 6,
  NoAmmo = 7,
  Waited = 8,
  InvalidFallback = 9,
};

enum class EventType : std::uint8_t {
  Moved = 0,
  MoveBlocked = 1,
  Shot = 2,
  BulletHit = 3,
  DamageApplied = 4,
  EntityDied = 5,
  AmmoRestored = 6,
  GameEnded = 7,
  DamageCredit = 8,
};

struct EntityState {
  EntityId id{EntityId::Player};
  Persona persona{Persona::Player};
  Position position{};
  std::uint8_t hp{kMaxHp};
  std::uint8_t ammo{kMaxAmmo};
  std::uint8_t recharge_progress{0};
  bool alive{true};
  Action last_action{Action::Wait};
  ActionResult last_result{ActionResult::None};
};

struct Bullet {
  Position position{};
  Direction direction{Direction::Up};
  EntityId shooter{EntityId::Player};
};

struct Event {
  EventType type{EventType::Moved};
  EntityId actor{EntityId::Player};
  EntityId target{EntityId::Player};
  Position position{};
  Direction direction{Direction::Up};
  std::uint8_t value{0};
};

constexpr std::size_t entityIndex(EntityId id) noexcept { return static_cast<std::size_t>(id); }

Position moved(Position origin, Direction direction) noexcept;
bool isMoveAction(Action action) noexcept;
bool isShootAction(Action action) noexcept;
Direction actionDirection(Action action) noexcept;
Action moveAction(Direction direction) noexcept;
Action shootAction(Direction direction) noexcept;
std::string_view toString(Action action) noexcept;
std::string_view toString(GameStatus status) noexcept;

}  // namespace catamaze::core
