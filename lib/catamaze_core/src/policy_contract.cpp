// Created at: 2026-11-14 03:37 EST
// Created by: Codex
// Last Modified at: 2026-11-14 03:37 EST
// Last Modified by: Codex
// Implements the frozen 13x5x5, 46-scalar, and nine-action policy contract.

#include "catamaze/core/policy_contract.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>

namespace catamaze::core {
namespace {

std::size_t terrainChannel(Terrain terrain) noexcept {
  switch (terrain) {
    case Terrain::Wall:
      return 0U;
    case Terrain::Floor:
    case Terrain::Entrance:
      return 1U;
    case Terrain::Exit:
      return 2U;
  }
  return 0U;
}

std::size_t entityChannel(EntityId entity, EntityId self) noexcept {
  if (entity == self) {
    return 4U;
  }
  return 5U + entityIndex(entity);
}

std::size_t bulletChannel(Direction direction) noexcept {
  switch (direction) {
    case Direction::Up:
      return 9U;
    case Direction::Down:
      return 10U;
    case Direction::Left:
      return 11U;
    case Direction::Right:
      return 12U;
  }
  return 9U;
}

std::size_t soundBucket(std::int8_t dx, std::int8_t dy) noexcept {
  if (dx == 0 && dy == 0) {
    return 8U;
  }
  if (dy < 0) {
    return dx < 0 ? 7U : (dx > 0 ? 1U : 0U);
  }
  if (dy > 0) {
    return dx < 0 ? 5U : (dx > 0 ? 3U : 4U);
  }
  return dx < 0 ? 6U : 2U;
}

bool walkableObservedCell(const ObservedCell& cell) noexcept {
  return cell.visible && cell.terrain != Terrain::Wall;
}

}  // namespace

std::array<bool, kPolicyActionCount> legalPolicyActionMask(
    const Observation& observation) noexcept {
  std::array<bool, kPolicyActionCount> mask{};
  if (!observation.self.alive) {
    return mask;
  }

  mask[static_cast<std::size_t>(Action::MoveUp)] =
      walkableObservedCell(observation.cells[7U]);
  mask[static_cast<std::size_t>(Action::MoveDown)] =
      walkableObservedCell(observation.cells[17U]);
  mask[static_cast<std::size_t>(Action::MoveLeft)] =
      walkableObservedCell(observation.cells[11U]);
  mask[static_cast<std::size_t>(Action::MoveRight)] =
      walkableObservedCell(observation.cells[13U]);
  const bool can_shoot = observation.self.ammo > 0U;
  mask[static_cast<std::size_t>(Action::ShootUp)] = can_shoot;
  mask[static_cast<std::size_t>(Action::ShootDown)] = can_shoot;
  mask[static_cast<std::size_t>(Action::ShootLeft)] = can_shoot;
  mask[static_cast<std::size_t>(Action::ShootRight)] = can_shoot;
  mask[static_cast<std::size_t>(Action::Wait)] = true;
  return mask;
}

EncodedObservation encodePolicyObservation(const Observation& observation,
                                           std::uint16_t tick) noexcept {
  EncodedObservation encoded{};
  for (std::size_t cell_index = 0; cell_index < observation.cells.size(); ++cell_index) {
    const ObservedCell& cell = observation.cells[cell_index];
    if (!cell.visible) {
      encoded.spatial[spatialIndex(3U, cell_index)] = 1U;
      continue;
    }
    encoded.spatial[spatialIndex(terrainChannel(cell.terrain), cell_index)] = 1U;
    if (cell.entity >= 0 && static_cast<std::size_t>(cell.entity) < kEntityCount) {
      const EntityId entity = static_cast<EntityId>(cell.entity);
      encoded.spatial[spatialIndex(entityChannel(entity, observation.self.id), cell_index)] = 1U;
    }
    if (cell.bullet) {
      encoded.spatial[spatialIndex(bulletChannel(cell.bullet_direction), cell_index)] = 1U;
    }
  }

  encoded.scalar[0U] = static_cast<float>(observation.self.hp) / static_cast<float>(kMaxHp);
  encoded.scalar[1U] = static_cast<float>(observation.self.ammo) / static_cast<float>(kMaxAmmo);
  encoded.scalar[2U] = static_cast<float>(observation.self.recharge_progress) / 2.0F;
  encoded.scalar[3U] = static_cast<float>(observation.self.position.x) / 49.0F;
  encoded.scalar[4U] = static_cast<float>(observation.self.position.y) / 49.0F;
  encoded.scalar[5U] = static_cast<float>(std::min(tick, kMaxTicks)) /
                       static_cast<float>(kMaxTicks);

  const std::size_t last_action = static_cast<std::size_t>(observation.self.last_action);
  if (last_action < kPolicyActionCount) {
    encoded.scalar[kScalarLastActionOffset + last_action] = 1.0F;
  }
  const std::size_t last_result = static_cast<std::size_t>(observation.self.last_result);
  if (last_result < 10U) {
    encoded.scalar[kScalarLastResultOffset + last_result] = 1.0F;
  }
  if (observation.sound.heard) {
    const std::size_t bucket =
        soundBucket(observation.sound.direction_x, observation.sound.direction_y);
    encoded.scalar[kScalarSoundPresenceOffset + bucket] = 1.0F;
    encoded.scalar[kScalarSoundDistanceOffset + bucket] =
        static_cast<float>(std::min<std::uint8_t>(observation.sound.distance, 3U)) / 3.0F;
  }
  const std::size_t persona = static_cast<std::size_t>(observation.self.persona);
  if (persona >= static_cast<std::size_t>(Persona::Aggressive) &&
      persona <= static_cast<std::size_t>(Persona::Explorer)) {
    encoded.scalar[kScalarPersonaOffset + persona - 1U] = 1.0F;
  }
  encoded.action_mask = legalPolicyActionMask(observation);
  return encoded;
}

}  // namespace catamaze::core
