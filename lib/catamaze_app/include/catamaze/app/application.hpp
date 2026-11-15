// Created at: 2026-11-14 02:26 EST
// Created by: Codex
// Last Modified at: 2026-11-14 19:00 EST
// Last Modified by: Codex
// Declares the one-owner application coordinator and deterministic heuristic AI lifecycle.

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "catamaze/app/resident_policy.hpp"
#include "catamaze/core/engine.hpp"

namespace catamaze::app {

class Application {
 public:
  explicit Application(std::uint64_t seed) noexcept;
  explicit Application(core::GameConfig config) noexcept;

  void reset(std::uint64_t seed) noexcept;
  void reset(core::GameConfig config) noexcept;
  bool enqueuePlayerAction(core::Action action) noexcept;
  void clearPlayerQueue() noexcept;
  void tick() noexcept;
  void installResidentPolicy(ResidentPolicyModule& policy) noexcept;

  core::PlayerObservation playerObservation() const noexcept;
  const core::WorldState& state() const noexcept { return engine_.state(); }
  const PolicyHealth& policyHealth() const noexcept;
  std::uint64_t stateHash() const noexcept;

 private:
  struct AiMemory {
    std::array<std::uint16_t, core::kMapCellCount> visits{};
    core::Direction heading{core::Direction::Up};
  };

  core::Action chooseHeuristicAction(std::size_t ai_index,
                                     const core::Observation& observation) noexcept;
  static bool legalMove(const core::Observation& observation, core::Direction direction) noexcept;
  static std::size_t positionIndex(core::Position position) noexcept;
  void initializeAiMemory(std::uint64_t seed) noexcept;

  core::GameEngine engine_;
  std::array<AiMemory, core::kAiCount> ai_memory_{};
  ResidentPolicyModule* resident_policy_{nullptr};
  PolicyHealth heuristic_health_{};
};

}  // namespace catamaze::app
