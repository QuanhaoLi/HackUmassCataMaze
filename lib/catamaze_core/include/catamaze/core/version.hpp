// Created at: 2026-11-14 02:13 EST
// Created by: Codex
// Last Modified at: 2026-11-14 03:38 EST
// Last Modified by: Codex
// Defines stable build-visible version identifiers for the portable Game Core.

#pragma once

#include <string_view>

namespace catamaze::core {

inline constexpr std::string_view kProductName{"CataMaze"};
inline constexpr std::string_view kRulesVersion{"catamaze.rules.v1"};
inline constexpr std::string_view kEnvironmentVersion{"catamaze.environment.v1"};
inline constexpr std::string_view kObservationSchemaVersion{"catamaze.observation.v1"};
inline constexpr std::string_view kCoreVersion{"0.1.0"};

}  // namespace catamaze::core
