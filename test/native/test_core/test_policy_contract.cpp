// Created at: 2026-11-14 03:36 EST
// Created by: Codex
// Last Modified at: 2026-11-14 03:36 EST
// Last Modified by: Codex
// Verifies the frozen policy observation schema and legal-action mask.

#include <gtest/gtest.h>

#include <algorithm>
#include <cstddef>

#include "catamaze/core/policy_contract.hpp"

namespace catamaze::core {
namespace {

Observation contractObservation() {
  Observation observation{};
  observation.self.id = EntityId::Cautious;
  observation.self.persona = Persona::Cautious;
  observation.self.position = Position{7, 11};
  observation.self.hp = 4U;
  observation.self.ammo = 0U;
  observation.self.recharge_progress = 1U;
  observation.self.alive = true;
  observation.self.last_action = Action::ShootLeft;
  observation.self.last_result = ActionResult::Shot;
  observation.sound = SoundObservation{true, 1, -1, 2U};

  auto& center = observation.cells[12];
  center.visible = true;
  center.terrain = Terrain::Floor;
  center.entity = static_cast<std::int8_t>(entityIndex(EntityId::Cautious));

  auto& up = observation.cells[7];
  up.visible = true;
  up.terrain = Terrain::Wall;

  auto& down = observation.cells[17];
  down.visible = true;
  down.terrain = Terrain::Floor;

  auto& left = observation.cells[11];
  left.visible = true;
  left.terrain = Terrain::Floor;
  left.entity = static_cast<std::int8_t>(entityIndex(EntityId::Player));

  auto& right = observation.cells[13];
  right.visible = true;
  right.terrain = Terrain::Floor;
  right.bullet = true;
  right.bullet_direction = Direction::Down;
  return observation;
}

TEST(PolicyContract, EncodesEveryFeatureFamilyAtFrozenIndices) {
  const EncodedObservation encoded = encodePolicyObservation(contractObservation(), 100U);

  EXPECT_EQ(encoded.spatial[spatialIndex(3U, 0U)], 1U);
  EXPECT_EQ(encoded.spatial[spatialIndex(0U, 7U)], 1U);
  EXPECT_EQ(encoded.spatial[spatialIndex(1U, 12U)], 1U);
  EXPECT_EQ(encoded.spatial[spatialIndex(4U, 12U)], 1U);
  EXPECT_EQ(encoded.spatial[spatialIndex(5U, 11U)], 1U);
  EXPECT_EQ(encoded.spatial[spatialIndex(10U, 13U)], 1U);

  EXPECT_FLOAT_EQ(encoded.scalar[0], 4.0F / 5.0F);
  EXPECT_FLOAT_EQ(encoded.scalar[1], 0.0F);
  EXPECT_FLOAT_EQ(encoded.scalar[2], 0.5F);
  EXPECT_FLOAT_EQ(encoded.scalar[3], 7.0F / 49.0F);
  EXPECT_FLOAT_EQ(encoded.scalar[4], 11.0F / 49.0F);
  EXPECT_FLOAT_EQ(encoded.scalar[5], 100.0F / 2000.0F);
  EXPECT_FLOAT_EQ(encoded.scalar[kScalarLastActionOffset + 6U], 1.0F);
  EXPECT_FLOAT_EQ(encoded.scalar[kScalarLastResultOffset + 6U], 1.0F);
  EXPECT_FLOAT_EQ(encoded.scalar[kScalarSoundPresenceOffset + 1U], 1.0F);
  EXPECT_FLOAT_EQ(encoded.scalar[kScalarSoundDistanceOffset + 1U], 2.0F / 3.0F);
  EXPECT_FLOAT_EQ(encoded.scalar[kScalarPersonaOffset + 1U], 1.0F);
}

TEST(PolicyContract, MaskKeepsEntityConflictsForResolutionAndAlwaysAllowsWait) {
  const EncodedObservation encoded = encodePolicyObservation(contractObservation(), 100U);

  EXPECT_FALSE(encoded.action_mask[static_cast<std::size_t>(Action::MoveUp)]);
  EXPECT_TRUE(encoded.action_mask[static_cast<std::size_t>(Action::MoveDown)]);
  EXPECT_TRUE(encoded.action_mask[static_cast<std::size_t>(Action::MoveLeft)]);
  EXPECT_TRUE(encoded.action_mask[static_cast<std::size_t>(Action::MoveRight)]);
  EXPECT_FALSE(encoded.action_mask[static_cast<std::size_t>(Action::ShootUp)]);
  EXPECT_FALSE(encoded.action_mask[static_cast<std::size_t>(Action::ShootDown)]);
  EXPECT_FALSE(encoded.action_mask[static_cast<std::size_t>(Action::ShootLeft)]);
  EXPECT_FALSE(encoded.action_mask[static_cast<std::size_t>(Action::ShootRight)]);
  EXPECT_TRUE(encoded.action_mask[static_cast<std::size_t>(Action::Wait)]);
}

TEST(PolicyContract, DeadAgentsHaveNoPolicyActions) {
  Observation observation = contractObservation();
  observation.self.alive = false;
  const EncodedObservation encoded = encodePolicyObservation(observation, 100U);
  EXPECT_TRUE(std::none_of(encoded.action_mask.begin(), encoded.action_mask.end(),
                           [](bool legal) { return legal; }));
}

}  // namespace
}  // namespace catamaze::core
