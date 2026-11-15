// Created at: 2026-11-14 18:51 EST
// Created by: Codex
// Last Modified at: 2026-11-14 18:51 EST
// Last Modified by: Codex
// Generated from model/policy_release.json; do not hand-edit release values.

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string_view>

namespace catamaze::esp32::policy_release {

inline constexpr std::string_view kSchema{"catamaze.policy.release.v1"};
inline constexpr std::string_view kRelease{"production-100364306-w8a16"};
inline constexpr std::string_view kArtifact{"catamaze_policy.espdl"};
inline constexpr std::string_view kArtifactSha256{"0cc8bb5025ff22c435b0107fd739560f4c4e13c16e2683a1ad3f0e0ee7044322"};
inline constexpr std::size_t kArtifactBytes = 1490800U;
inline constexpr std::size_t kParameters = 1010826U;
inline constexpr std::string_view kTarget{"esp32s3"};
inline constexpr std::string_view kQuantization{"w8a16"};
inline constexpr std::string_view kExporterVersion{"3.3.15"};
inline constexpr std::string_view kRuntimeVersion{"3.3.11"};
inline constexpr std::string_view kRuntimeCompatibility{"decoded-envelope-v1"};
inline constexpr std::array<std::size_t, 4U> kSpatialShape{1U, 13U, 5U, 5U};
inline constexpr std::array<std::size_t, 2U> kScalarShape{1U, 46U};
inline constexpr std::array<std::size_t, 3U> kHiddenShape{1U, 1U, 256U};
inline constexpr std::array<std::size_t, 2U> kLogitsShape{1U, 9U};
inline constexpr std::array<std::size_t, 1U> kValueShape{1U};
inline constexpr std::array<std::size_t, 3U> kNextHiddenShape{1U, 1U, 256U};
inline constexpr std::size_t kCalibrationSamples = 512U;
inline constexpr std::size_t kEvaluationSamples = 10000U;
inline constexpr float kMaskedActionAgreement = 0.986100F;
inline constexpr float kMinimumMaskedActionAgreement = 0.985000F;
inline constexpr float kMaximumLogitError = 0.100000F;
inline constexpr float kMaximumValueError = 0.500000F;
inline constexpr float kMaximumHiddenError = 0.180000F;
inline constexpr std::uint32_t kMaximumThreeAgentUs = 900000U;
inline constexpr std::uint32_t kPhysicalThreeInferenceUs = 126287U;
inline constexpr std::uint32_t kPhysicalInternalBytes = 167508U;
inline constexpr std::uint32_t kPhysicalPsramBytes = 1480032U;

}  // namespace catamaze::esp32::policy_release
