// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-15 00:22 EST
// Last Modified by: Codex
// Implements deterministic simultaneous movement, combat, observations, and terminal rules.

#include "catamaze/core/engine.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>

namespace catamaze::core {
namespace {

constexpr std::array<EntityId, kEntityCount> kEntityIds{EntityId::Player, EntityId::Aggressive,
                                                        EntityId::Cautious, EntityId::Explorer};

constexpr std::array<Persona, kEntityCount> kPersonas{Persona::Player, Persona::Aggressive,
                                                      Persona::Cautious, Persona::Explorer};

std::int16_t absolute(std::int16_t value) noexcept {
  return value < 0 ? static_cast<std::int16_t>(-value) : value;
}

std::int8_t sign(std::int16_t value) noexcept { return value < 0 ? -1 : (value > 0 ? 1 : 0); }

struct Hit {
  EntityId shooter{EntityId::Player};
  EntityId target{EntityId::Player};
  Position position{};
};

class Fnv1a64 {
 public:
  void byte(std::uint8_t value) noexcept {
    hash_ ^= value;
    hash_ *= 1099511628211ULL;
  }

  template <typename Unsigned>
  void integer(Unsigned value) noexcept {
    for (std::size_t index = 0; index < sizeof(Unsigned); ++index) {
      byte(static_cast<std::uint8_t>((value >> (index * 8U)) & 0xffU));
    }
  }

  std::uint64_t value() const noexcept { return hash_; }

 private:
  std::uint64_t hash_{14695981039346656037ULL};
};

}  // namespace

const ObservedCell& Observation::atOffset(std::int8_t dx, std::int8_t dy) const noexcept {
  static const ObservedCell kHidden{};
  if (dx < -2 || dx > 2 || dy < -2 || dy > 2) {
    return kHidden;
  }
  const auto index = static_cast<std::size_t>(dy + 2) * 5U + static_cast<std::size_t>(dx + 2);
  return cells[index];
}

const ObservedCell& PlayerObservation::atOffset(std::int8_t dx, std::int8_t dy) const noexcept {
  static const ObservedCell kHidden{};
  if (dx < -4 || dx > 4 || dy < -2 || dy > 2) {
    return kHidden;
  }
  const auto index = static_cast<std::size_t>(dy + 2) * 9U + static_cast<std::size_t>(dx + 4);
  return cells[index];
}

GameEngine::GameEngine(std::uint64_t seed) noexcept { reset(seed); }

GameEngine::GameEngine(GameConfig config) noexcept { reset(config); }

GameEngine::GameEngine(const GameSetup& setup) noexcept { initialize(setup); }

void GameEngine::reset(std::uint64_t seed) noexcept {
  reset(GameConfig{static_cast<std::uint8_t>(kMapSize), seed});
}

void GameEngine::reset(GameConfig config) noexcept {
  if (!isValidMapSize(config.map_size)) {
    config.map_size = static_cast<std::uint8_t>(kMapSize);
  }
  const GeneratedWorld generated = MazeGenerator::generate(config.seed, config.map_size);
  initialize(GameSetup{generated.map, generated.spawns, config.seed,
                       tickBudgetForMapSize(config.map_size)});
}

void GameEngine::restore(const WorldState& state) noexcept { state_ = state; }

void GameEngine::initialize(const GameSetup& setup) noexcept {
  state_ = WorldState{};
  state_.map = setup.map;
  state_.seed = setup.seed;
  state_.max_ticks = setup.max_ticks;
  for (std::size_t index = 0; index < kEntityCount; ++index) {
    auto& entity = state_.entities[index];
    entity.id = kEntityIds[index];
    entity.persona = kPersonas[index];
    entity.position = setup.spawns[index];
    entity.hp = kMaxHp;
    entity.ammo = kMaxAmmo;
    entity.recharge_progress = 0;
    entity.alive = true;
    entity.last_action = Action::Wait;
    entity.last_result = ActionResult::None;
  }
}

bool GameEngine::enqueuePlayerAction(Action action) noexcept {
  if (state_.status != GameStatus::Running) {
    return false;
  }
  return state_.player_queue.push(action);
}

void GameEngine::clearPlayerQueue() noexcept { state_.player_queue.clear(); }

void GameEngine::addEvent(const Event& event) noexcept {
  if (state_.event_count < state_.events.size()) {
    state_.events[state_.event_count++] = event;
  }
}

std::int8_t GameEngine::entityAt(Position position, EntityId ignored) const noexcept {
  for (std::size_t index = 0; index < state_.entities.size(); ++index) {
    const auto& entity = state_.entities[index];
    if (entity.alive && entity.id != ignored && entity.position == position) {
      return static_cast<std::int8_t>(index);
    }
  }
  return -1;
}

void GameEngine::step(const std::array<Action, kAiCount>& ai_actions) noexcept {
  if (state_.status != GameStatus::Running) {
    return;
  }
  state_.event_count = 0U;

  std::array<Action, kEntityCount> actions{};
  std::array<bool, kEntityCount> invalid_fallback{};
  actions[0] = state_.player_queue.popOrWait();
  for (std::size_t ai = 0; ai < kAiCount; ++ai) {
    actions[ai + 1U] = ai_actions[ai];
    const auto& entity = state_.entities[ai + 1U];
    if (entity.alive && isShootAction(actions[ai + 1U]) && entity.ammo == 0U) {
      actions[ai + 1U] = Action::Wait;
      invalid_fallback[ai + 1U] = true;
    }
  }

  const auto start_entities = state_.entities;
  std::array<Position, kEntityCount> targets{};
  std::array<bool, kEntityCount> move_candidate{};
  for (std::size_t index = 0; index < kEntityCount; ++index) {
    auto& entity = state_.entities[index];
    if (!entity.alive) {
      continue;
    }
    entity.last_action = actions[index];
    if (invalid_fallback[index]) {
      entity.last_result = ActionResult::InvalidFallback;
      continue;
    }
    if (actions[index] == Action::Wait) {
      entity.last_result = ActionResult::Waited;
      continue;
    }
    if (!isMoveAction(actions[index])) {
      entity.last_result = ActionResult::None;
      continue;
    }

    targets[index] = moved(entity.position, actionDirection(actions[index]));
    if (!state_.map.inBounds(targets[index])) {
      entity.last_result = ActionResult::BlockedBounds;
    } else if (!state_.map.isWalkable(targets[index])) {
      entity.last_result = ActionResult::BlockedWall;
    } else {
      bool occupied = false;
      for (const auto& other : start_entities) {
        if (other.alive && other.position == targets[index]) {
          occupied = true;
          break;
        }
      }
      if (occupied) {
        entity.last_result = ActionResult::BlockedEntity;
      } else {
        move_candidate[index] = true;
      }
    }
  }

  for (std::size_t first = 0; first < kEntityCount; ++first) {
    if (!move_candidate[first]) {
      continue;
    }
    for (std::size_t second = first + 1U; second < kEntityCount; ++second) {
      if (move_candidate[second] && targets[first] == targets[second]) {
        move_candidate[first] = false;
        move_candidate[second] = false;
        state_.entities[first].last_result = ActionResult::BlockedConflict;
        state_.entities[second].last_result = ActionResult::BlockedConflict;
      }
    }
  }

  for (std::size_t index = 0; index < kEntityCount; ++index) {
    auto& entity = state_.entities[index];
    if (move_candidate[index]) {
      entity.position = targets[index];
      entity.last_result = ActionResult::Moved;
      addEvent(Event{EventType::Moved, entity.id, entity.id, entity.position,
                     actionDirection(actions[index]), 0});
    } else if (entity.alive && isMoveAction(actions[index])) {
      addEvent(Event{EventType::MoveBlocked, entity.id, entity.id, entity.position,
                     actionDirection(actions[index]),
                     static_cast<std::uint8_t>(entity.last_result)});
    }
  }

  std::array<Hit, kMaxBullets + kEntityCount> hits{};
  std::size_t hit_count = 0U;
  std::array<Bullet, kMaxBullets> next_bullets{};
  std::size_t next_bullet_count = 0U;

  const auto resolve_bullet = [&](const Bullet& bullet) {
    const Position next = moved(bullet.position, bullet.direction);
    if (!state_.map.inBounds(next) || !state_.map.isWalkable(next)) {
      return;
    }
    const std::int8_t target_index = entityAt(next, bullet.shooter);
    if (target_index >= 0) {
      if (hit_count < hits.size()) {
        hits[hit_count++] =
            Hit{bullet.shooter, state_.entities[static_cast<std::size_t>(target_index)].id, next};
      }
      return;
    }
    if (next_bullet_count < next_bullets.size()) {
      next_bullets[next_bullet_count++] = Bullet{next, bullet.direction, bullet.shooter};
    }
  };

  for (std::size_t index = 0; index < state_.bullet_count; ++index) {
    resolve_bullet(state_.bullets[index]);
  }

  for (std::size_t index = 0; index < kEntityCount; ++index) {
    auto& entity = state_.entities[index];
    if (!entity.alive || !isShootAction(actions[index])) {
      continue;
    }
    if (entity.ammo == 0U) {
      entity.last_result = ActionResult::NoAmmo;
      continue;
    }
    --entity.ammo;
    entity.last_result = ActionResult::Shot;
    const Direction direction = actionDirection(actions[index]);
    addEvent(Event{EventType::Shot, entity.id, entity.id, entity.position, direction, 1});
    resolve_bullet(Bullet{entity.position, direction, entity.id});
  }

  state_.bullets = next_bullets;
  state_.bullet_count = next_bullet_count;

  std::array<std::uint8_t, kEntityCount> hit_totals{};
  std::array<std::array<std::uint8_t, kEntityCount>, kEntityCount> hit_credits{};
  for (std::size_t index = 0; index < hit_count; ++index) {
    const Hit& hit = hits[index];
    const std::size_t target_index = entityIndex(hit.target);
    ++hit_totals[target_index];
    ++hit_credits[target_index][entityIndex(hit.shooter)];
    addEvent(Event{EventType::BulletHit, hit.shooter, hit.target, hit.position, Direction::Up, 1});
  }

  for (std::size_t index = 0; index < kEntityCount; ++index) {
    auto& entity = state_.entities[index];
    if (!entity.alive || hit_totals[index] == 0U) {
      continue;
    }
    const std::uint8_t damage = std::min(entity.hp, hit_totals[index]);
    entity.hp = static_cast<std::uint8_t>(entity.hp - damage);
    addEvent(Event{EventType::DamageApplied, entity.id, entity.id, entity.position, Direction::Up,
                   damage});
    for (std::size_t shooter = 0; shooter < kEntityCount; ++shooter) {
      if (hit_credits[index][shooter] == 0U) {
        continue;
      }
      addEvent(Event{EventType::DamageCredit, kEntityIds[shooter], entity.id, entity.position,
                     Direction::Up, hit_credits[index][shooter]});
    }
    if (entity.hp == 0U) {
      entity.alive = false;
      addEvent(
          Event{EventType::EntityDied, entity.id, entity.id, entity.position, Direction::Up, 0});
    }
  }

  for (std::size_t index = 0U; index < state_.entities.size(); ++index) {
    auto& entity = state_.entities[index];
    if (!entity.alive) {
      continue;
    }
    if (start_entities[index].ammo >= kMaxAmmo || entity.ammo >= kMaxAmmo) {
      entity.recharge_progress = 0U;
      continue;
    }
    ++entity.recharge_progress;
    if (entity.recharge_progress >= 2U) {
      entity.recharge_progress = 0U;
      ++entity.ammo;
      addEvent(
          Event{EventType::AmmoRestored, entity.id, entity.id, entity.position, Direction::Up, 1});
    }
  }

  ++state_.tick;
  const auto& player = state_.entities[entityIndex(EntityId::Player)];
  if (!player.alive) {
    state_.status = GameStatus::Death;
  } else if (state_.map.at(player.position) == Terrain::Exit) {
    state_.status = GameStatus::Victory;
  } else if (state_.tick >= state_.max_ticks) {
    state_.status = GameStatus::Timeout;
  }
  if (state_.status != GameStatus::Running) {
    addEvent(Event{EventType::GameEnded, EntityId::Player, EntityId::Player, player.position,
                   Direction::Up, static_cast<std::uint8_t>(state_.status)});
  }
}

bool GameEngine::hasLineOfSight(Position from, Position to) const noexcept {
  if (from == to) {
    return true;
  }
  std::int16_t x = from.x;
  std::int16_t y = from.y;
  const std::int16_t dx = absolute(static_cast<std::int16_t>(to.x - from.x));
  const std::int16_t sx = from.x < to.x ? 1 : -1;
  const std::int16_t dy =
      static_cast<std::int16_t>(-absolute(static_cast<std::int16_t>(to.y - from.y)));
  const std::int16_t sy = from.y < to.y ? 1 : -1;
  std::int16_t error = static_cast<std::int16_t>(dx + dy);

  while (x != to.x || y != to.y) {
    const std::int16_t previous_x = x;
    const std::int16_t previous_y = y;
    const std::int16_t doubled = static_cast<std::int16_t>(2 * error);
    if (doubled >= dy) {
      error = static_cast<std::int16_t>(error + dy);
      x = static_cast<std::int16_t>(x + sx);
    }
    if (doubled <= dx) {
      error = static_cast<std::int16_t>(error + dx);
      y = static_cast<std::int16_t>(y + sy);
    }

    const bool diagonal = x != previous_x && y != previous_y;
    if (diagonal && (state_.map.at(Position{x, previous_y}) == Terrain::Wall ||
                     state_.map.at(Position{previous_x, y}) == Terrain::Wall)) {
      return false;
    }
    const Position current{x, y};
    if (current != to && state_.map.at(current) == Terrain::Wall) {
      return false;
    }
  }
  return true;
}

Observation GameEngine::observe(EntityId observer) const noexcept {
  Observation observation{};
  const auto& self = state_.entities[entityIndex(observer)];
  observation.self = self;

  for (std::int8_t dy = -2; dy <= 2; ++dy) {
    for (std::int8_t dx = -2; dx <= 2; ++dx) {
      const std::size_t observed_index =
          static_cast<std::size_t>(dy + 2) * 5U + static_cast<std::size_t>(dx + 2);
      auto& cell = observation.cells[observed_index];
      const Position position{static_cast<std::int16_t>(self.position.x + dx),
                              static_cast<std::int16_t>(self.position.y + dy)};
      if (!state_.map.inBounds(position)) {
        cell.visible = true;
        cell.terrain = Terrain::Wall;
        continue;
      }
      cell.visible = hasLineOfSight(self.position, position);
      if (!cell.visible) {
        continue;
      }
      cell.terrain = state_.map.at(position);
      cell.entity = entityAt(position, observer);
      if (position == self.position) {
        cell.entity = static_cast<std::int8_t>(entityIndex(observer));
      }
      for (std::size_t bullet = 0; bullet < state_.bullet_count; ++bullet) {
        if (state_.bullets[bullet].position == position) {
          cell.bullet = true;
          cell.bullet_direction = state_.bullets[bullet].direction;
          break;
        }
      }
    }
  }

  observation.sound = soundAt(self.position);
  return observation;
}

PlayerObservation GameEngine::observePlayer() const noexcept {
  PlayerObservation observation{};
  const auto& self = state_.entities[entityIndex(EntityId::Player)];
  observation.self = self;

  for (std::int8_t dy = -2; dy <= 2; ++dy) {
    for (std::int8_t dx = -4; dx <= 4; ++dx) {
      const std::size_t observed_index =
          static_cast<std::size_t>(dy + 2) * 9U + static_cast<std::size_t>(dx + 4);
      auto& cell = observation.cells[observed_index];
      const Position position{static_cast<std::int16_t>(self.position.x + dx),
                              static_cast<std::int16_t>(self.position.y + dy)};
      if (!state_.map.inBounds(position)) {
        cell.visible = true;
        cell.terrain = Terrain::Wall;
        continue;
      }
      cell.visible = hasLineOfSight(self.position, position);
      if (!cell.visible) continue;
      cell.terrain = state_.map.at(position);
      cell.entity = entityAt(position, EntityId::Player);
      if (position == self.position) {
        cell.entity = static_cast<std::int8_t>(entityIndex(EntityId::Player));
      }
      for (std::size_t bullet = 0; bullet < state_.bullet_count; ++bullet) {
        if (state_.bullets[bullet].position == position) {
          cell.bullet = true;
          cell.bullet_direction = state_.bullets[bullet].direction;
          break;
        }
      }
    }
  }
  observation.sound = soundAt(self.position);
  return observation;
}

SoundObservation GameEngine::soundAt(Position observer) const noexcept {
  SoundObservation sound{};
  std::uint8_t nearest = 255U;
  for (std::size_t index = 0; index < state_.event_count; ++index) {
    const Event& event = state_.events[index];
    if (event.type != EventType::Shot) {
      continue;
    }
    const std::int16_t dx = static_cast<std::int16_t>(event.position.x - observer.x);
    const std::int16_t dy = static_cast<std::int16_t>(event.position.y - observer.y);
    const auto distance = static_cast<std::uint8_t>(std::max(absolute(dx), absolute(dy)));
    if (distance <= 3U && distance < nearest) {
      nearest = distance;
      sound.heard = true;
      sound.direction_x = sign(dx);
      sound.direction_y = sign(dy);
      sound.distance = distance;
    }
  }
  return sound;
}

std::uint64_t GameEngine::stateHash() const noexcept {
  Fnv1a64 hash{};
  hash.integer(state_.seed);
  hash.integer(state_.tick);
  hash.integer(state_.max_ticks);
  hash.byte(state_.map.activeSize());
  hash.byte(static_cast<std::uint8_t>(state_.status));
  for (Terrain terrain : state_.map.cells()) {
    hash.byte(static_cast<std::uint8_t>(terrain));
  }
  for (const auto& entity : state_.entities) {
    hash.byte(static_cast<std::uint8_t>(entity.id));
    hash.byte(static_cast<std::uint8_t>(entity.persona));
    hash.integer(static_cast<std::uint16_t>(entity.position.x));
    hash.integer(static_cast<std::uint16_t>(entity.position.y));
    hash.byte(entity.hp);
    hash.byte(entity.ammo);
    hash.byte(entity.recharge_progress);
    hash.byte(entity.alive ? 1U : 0U);
    hash.byte(static_cast<std::uint8_t>(entity.last_action));
    hash.byte(static_cast<std::uint8_t>(entity.last_result));
  }
  hash.integer(static_cast<std::uint16_t>(state_.bullet_count));
  for (std::size_t index = 0; index < state_.bullet_count; ++index) {
    const Bullet& bullet = state_.bullets[index];
    hash.integer(static_cast<std::uint16_t>(bullet.position.x));
    hash.integer(static_cast<std::uint16_t>(bullet.position.y));
    hash.byte(static_cast<std::uint8_t>(bullet.direction));
    hash.byte(static_cast<std::uint8_t>(bullet.shooter));
  }
  hash.byte(static_cast<std::uint8_t>(state_.player_queue.size()));
  for (std::size_t index = 0; index < state_.player_queue.size(); ++index) {
    hash.byte(static_cast<std::uint8_t>(state_.player_queue.at(index)));
  }
  hash.integer(static_cast<std::uint16_t>(state_.event_count));
  for (std::size_t index = 0; index < state_.event_count; ++index) {
    const Event& event = state_.events[index];
    hash.byte(static_cast<std::uint8_t>(event.type));
    hash.byte(static_cast<std::uint8_t>(event.actor));
    hash.byte(static_cast<std::uint8_t>(event.target));
    hash.integer(static_cast<std::uint16_t>(event.position.x));
    hash.integer(static_cast<std::uint16_t>(event.position.y));
    hash.byte(static_cast<std::uint8_t>(event.direction));
    hash.byte(event.value);
  }
  return hash.value();
}

}  // namespace catamaze::core
