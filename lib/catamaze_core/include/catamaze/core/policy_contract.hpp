// Created at: 2026-11-14 03:37 EST
// Created by: Codex
// Last Modified at: 2026-11-14 03:37 EST
// Last Modified by: Codex
// Declares the single portable policy observation and action-mask contract.

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "catamaze/core/engine.hpp"

namespace catamaze::core {

inline constexpr std::size_t kPolicySpatialChannels = 13U;
inline constexpr std::size_t kPolicyGridCellCount = 25U;
inline constexpr std::size_t kPolicySpatialFeatures =
    kPolicySpatialChannels * kPolicyGridCellCount;
inline constexpr std::size_t kPolicyScalarFeatures = 46U;
inline constexpr std::size_t kPolicyActionCount = 9U;

inline constexpr std::size_t kScalarLastActionOffset = 6U;
inline constexpr std::size_t kScalarLastResultOffset = 15U;
inline constexpr std::size_t kScalarSoundPresenceOffset = 25U;
inline constexpr std::size_t kScalarSoundDistanceOffset = 34U;
inline constexpr std::size_t kScalarPersonaOffset = 43U;

constexpr std::size_t spatialIndex(std::size_t channel, std::size_t cell) noexcept {
  return channel * kPolicyGridCellCount + cell;
}

struct EncodedObservation {
  std::array<std::uint8_t, kPolicySpatialFeatures> spatial{};
  std::array<float, kPolicyScalarFeatures> scalar{};
  std::array<bool, kPolicyActionCount> action_mask{};
};

std::array<bool, kPolicyActionCount> legalPolicyActionMask(
    const Observation& observation) noexcept;
EncodedObservation encodePolicyObservation(const Observation& observation,
                                           std::uint16_t tick) noexcept;

}  // namespace catamaze::core
