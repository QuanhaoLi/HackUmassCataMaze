// Created at: 2026-11-14 02:26 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Declares the one-owner application coordinator and deterministic heuristic AI lifecycle.

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "catamaze/core/engine.hpp"

namespace catamaze::app {

class Application {
 public:
  explicit Application(std::uint64_t seed) noexcept;

  void reset(std::uint64_t seed) noexcept;
  bool enqueuePlayerAction(core::Action action) noexcept;
  void clearPlayerQueue() noexcept;
  void tick() noexcept;

  core::Observation playerObservation() const noexcept;
  const core::WorldState& state() const noexcept { return engine_.state(); }
  std::uint64_t stateHash() const noexcept;

 private:
  struct AiMemory {
    std::array<std::uint16_t, core::kMapCellCount> visits{};
    core::Direction heading{core::Direction::Up};
  };

  core::Action chooseAction(std::size_t ai_index) noexcept;
  static bool legalMove(const core::Observation& observation, core::Direction direction) noexcept;
  static std::size_t positionIndex(core::Position position) noexcept;
  void initializeAiMemory(std::uint64_t seed) noexcept;

  core::GameEngine engine_;
  std::array<AiMemory, core::kAiCount> ai_memory_{};
};

}  // namespace catamaze::app
