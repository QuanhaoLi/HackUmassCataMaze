// Created at: 2026-11-14 02:26 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:32 EST
// Last Modified by: Codex
// Implements deterministic legal-observation AI policies and application tick ownership.

#include "catamaze/app/application.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>

#include "catamaze/core/random.hpp"

namespace catamaze::app {
namespace {

using core::Action;
using core::Direction;
using core::EntityId;
using core::Observation;
using core::Persona;

constexpr std::array<Direction, 4> kDirections{
    Direction::Up, Direction::Right, Direction::Down, Direction::Left};

std::size_t directionIndex(Direction direction) noexcept {
  return static_cast<std::size_t>(direction);
}

Direction rotated(Direction direction, int clockwise_steps) noexcept {
  const int index = static_cast<int>(directionIndex(direction));
  return kDirections[static_cast<std::size_t>((index + clockwise_steps + 8) % 4)];
}

std::int16_t absolute(std::int16_t value) noexcept {
  return value < 0 ? static_cast<std::int16_t>(-value) : value;
}

struct VisiblePlayer {
  bool seen{false};
  std::int8_t dx{0};
  std::int8_t dy{0};
};

VisiblePlayer findVisiblePlayer(const Observation& observation) noexcept {
  for (std::int8_t dy = -2; dy <= 2; ++dy) {
    for (std::int8_t dx = -2; dx <= 2; ++dx) {
      const auto& cell = observation.atOffset(dx, dy);
      if (cell.visible &&
          cell.entity == static_cast<std::int8_t>(
                             core::entityIndex(EntityId::Player))) {
        return VisiblePlayer{true, dx, dy};
      }
    }
  }
  return VisiblePlayer{};
}

bool cardinalLine(const VisiblePlayer& player, Direction& direction) noexcept {
  if (!player.seen || (player.dx != 0 && player.dy != 0)) {
    return false;
  }
  if (player.dx > 0) {
    direction = Direction::Right;
  } else if (player.dx < 0) {
    direction = Direction::Left;
  } else if (player.dy > 0) {
    direction = Direction::Down;
  } else if (player.dy < 0) {
    direction = Direction::Up;
  } else {
    return false;
  }
  return true;
}

Direction directionToward(std::int8_t dx, std::int8_t dy) noexcept {
  if (absolute(dx) >= absolute(dy) && dx != 0) {
    return dx > 0 ? Direction::Right : Direction::Left;
  }
  return dy > 0 ? Direction::Down : Direction::Up;
}

}  // namespace

Application::Application(std::uint64_t seed) noexcept : engine_(seed) {
  initializeAiMemory(seed);
}

void Application::reset(std::uint64_t seed) noexcept {
  engine_.reset(seed);
  initializeAiMemory(seed);
}

bool Application::enqueuePlayerAction(core::Action action) noexcept {
  return engine_.enqueuePlayerAction(action);
}

void Application::clearPlayerQueue() noexcept { engine_.clearPlayerQueue(); }

std::size_t Application::positionIndex(core::Position position) noexcept {
  return static_cast<std::size_t>(position.y) * core::kMapSize +
         static_cast<std::size_t>(position.x);
}

void Application::initializeAiMemory(std::uint64_t seed) noexcept {
  core::Pcg32 random(seed, 0x434154414d415a45ULL);
  for (std::size_t ai = 0; ai < ai_memory_.size(); ++ai) {
    ai_memory_[ai] = AiMemory{};
    ai_memory_[ai].heading =
        kDirections[random.bounded(static_cast<std::uint32_t>(kDirections.size()))];
    const auto& entity = engine_.state().entities[ai + 1U];
    ai_memory_[ai].visits[positionIndex(entity.position)] = 1U;
  }
}

bool Application::legalMove(const Observation& observation,
                            Direction direction) noexcept {
  std::int8_t dx = 0;
  std::int8_t dy = 0;
  switch (direction) {
    case Direction::Up:
      dy = -1;
      break;
    case Direction::Right:
      dx = 1;
      break;
    case Direction::Down:
      dy = 1;
      break;
    case Direction::Left:
      dx = -1;
      break;
  }
  const auto& cell = observation.atOffset(dx, dy);
  return cell.visible && cell.terrain != core::Terrain::Wall && cell.entity < 0;
}

Action Application::chooseAction(std::size_t ai_index) noexcept {
  const EntityId id = static_cast<EntityId>(ai_index + 1U);
  const Observation observation = engine_.observe(id);
  if (!observation.self.alive) {
    return Action::Wait;
  }
  AiMemory& memory = ai_memory_[ai_index];
  const VisiblePlayer player = findVisiblePlayer(observation);
  Direction line_direction = Direction::Up;
  const bool player_on_line = cardinalLine(player, line_direction);

  if (observation.self.persona == Persona::Aggressive && player_on_line &&
      observation.self.ammo > 0U) {
    return core::shootAction(line_direction);
  }
  if (observation.self.persona == Persona::Cautious && player_on_line &&
      observation.self.ammo >= 2U) {
    return core::shootAction(line_direction);
  }
  if (observation.self.persona == Persona::Explorer && player_on_line &&
      observation.self.ammo > 0U &&
      (absolute(player.dx) + absolute(player.dy)) <= 2) {
    return core::shootAction(line_direction);
  }

  if (observation.self.persona == Persona::Aggressive && player.seen) {
    const Direction primary = directionToward(player.dx, player.dy);
    if (legalMove(observation, primary)) {
      memory.heading = primary;
      return core::moveAction(primary);
    }
    const Direction secondary =
        primary == Direction::Left || primary == Direction::Right
            ? (player.dy > 0 ? Direction::Down : Direction::Up)
            : (player.dx > 0 ? Direction::Right : Direction::Left);
    if ((player.dx != 0 || player.dy != 0) && legalMove(observation, secondary)) {
      memory.heading = secondary;
      return core::moveAction(secondary);
    }
  }

  if (observation.self.persona == Persona::Cautious && player.seen) {
    Direction best = Direction::Up;
    int best_distance = -1;
    bool found = false;
    for (Direction candidate : kDirections) {
      if (!legalMove(observation, candidate)) {
        continue;
      }
      std::int8_t step_x = 0;
      std::int8_t step_y = 0;
      if (candidate == Direction::Left) {
        step_x = -1;
      } else if (candidate == Direction::Right) {
        step_x = 1;
      } else if (candidate == Direction::Up) {
        step_y = -1;
      } else {
        step_y = 1;
      }
      const int distance =
          absolute(static_cast<std::int16_t>(player.dx - step_x)) +
          absolute(static_cast<std::int16_t>(player.dy - step_y));
      if (!found || distance > best_distance) {
        found = true;
        best = candidate;
        best_distance = distance;
      }
    }
    if (found) {
      memory.heading = best;
      return core::moveAction(best);
    }
  }

  if (observation.self.persona == Persona::Explorer) {
    Direction best = Direction::Up;
    std::uint16_t least_visits = 0xffffU;
    bool found = false;
    const std::size_t rotation = directionIndex(memory.heading);
    for (std::size_t offset = 0; offset < kDirections.size(); ++offset) {
      const Direction candidate = kDirections[(rotation + offset) % 4U];
      if (!legalMove(observation, candidate)) {
        continue;
      }
      const core::Position next = core::moved(observation.self.position, candidate);
      const std::uint16_t visits = memory.visits[positionIndex(next)];
      if (!found || visits < least_visits) {
        found = true;
        best = candidate;
        least_visits = visits;
      }
    }
    if (found) {
      memory.heading = best;
      return core::moveAction(best);
    }
  }

  if (observation.self.persona == Persona::Aggressive &&
      observation.sound.heard) {
    const Direction toward_sound = directionToward(
        observation.sound.direction_x, observation.sound.direction_y);
    if (legalMove(observation, toward_sound)) {
      memory.heading = toward_sound;
      return core::moveAction(toward_sound);
    }
  }

  const bool left_hand = observation.self.persona == Persona::Aggressive;
  const std::array<int, 4> turn_order =
      left_hand ? std::array<int, 4>{-1, 0, 1, 2}
                : std::array<int, 4>{1, 0, -1, 2};
  for (int turn : turn_order) {
    const Direction candidate = rotated(memory.heading, turn);
    if (legalMove(observation, candidate)) {
      memory.heading = candidate;
      return core::moveAction(candidate);
    }
  }
  return Action::Wait;
}

void Application::tick() noexcept {
  if (engine_.state().status != core::GameStatus::Running) {
    return;
  }
  std::array<Action, core::kAiCount> actions{};
  for (std::size_t ai = 0; ai < actions.size(); ++ai) {
    actions[ai] = chooseAction(ai);
  }
  engine_.step(actions);
  for (std::size_t ai = 0; ai < ai_memory_.size(); ++ai) {
    const auto& entity = engine_.state().entities[ai + 1U];
    if (!entity.alive) {
      continue;
    }
    auto& count = ai_memory_[ai].visits[positionIndex(entity.position)];
    if (count < 0xffffU) {
      ++count;
    }
  }
}

core::Observation Application::playerObservation() const noexcept {
  return engine_.observe(EntityId::Player);
}

std::uint64_t Application::stateHash() const noexcept {
  std::uint64_t hash = engine_.stateHash();
  const auto mix = [&hash](std::uint64_t value) {
    hash ^= value + 0x9e3779b97f4a7c15ULL + (hash << 6U) + (hash >> 2U);
  };
  for (const auto& memory : ai_memory_) {
    mix(static_cast<std::uint8_t>(memory.heading));
    for (std::uint16_t visits : memory.visits) {
      mix(visits);
    }
  }
  return hash;
}

}  // namespace catamaze::app
