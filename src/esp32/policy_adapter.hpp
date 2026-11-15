// Created at: 2026-11-15 00:24 EST
// Created by: Codex
// Last Modified at: 2026-11-14 19:00 EST
// Last Modified by: Codex
// Declares the resident ESP-DL policy and its fail-closed heuristic fallback boundary.

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "catamaze/app/application.hpp"

namespace dl {
class Model;
class TensorBase;
}  // namespace dl

namespace catamaze::esp32 {

class PolicyAdapter final : public app::ResidentPolicyModule {
 public:
  PolicyAdapter() = default;
  ~PolicyAdapter() override;

  bool begin() noexcept;
  void resetSession() noexcept override;
  bool selectTick(const app::PolicyTickInput& input,
                  std::array<core::Action, core::kAiCount>& actions) noexcept override;
  std::uint64_t stateHash() const noexcept override;
  const app::PolicyHealth& health() const noexcept override { return health_; }

  const app::PolicyHealth& diagnostics() const noexcept { return health_; }

 private:
  using HiddenState = std::array<float, 256U>;

  bool resolveContract() noexcept;
  bool validateReleaseEnvelope() noexcept;
  bool failInference(app::PolicyFailure failure, std::uint32_t tick_us = 0U) noexcept;

  dl::Model* model_{nullptr};
  dl::TensorBase* spatial_{nullptr};
  dl::TensorBase* scalar_{nullptr};
  dl::TensorBase* hidden_{nullptr};
  dl::TensorBase* logits_{nullptr};
  dl::TensorBase* value_{nullptr};
  dl::TensorBase* next_hidden_{nullptr};
  std::array<HiddenState, core::kAiCount> hidden_states_{};
  app::PolicyHealth health_{};
};

}  // namespace catamaze::esp32
