// Created at: 2026-11-15 00:24 EST
// Created by: Codex
// Last Modified at: 2026-11-15 00:24 EST
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

inline constexpr const char* kPolicyArtifactSha256 =
    "0cc8bb5025ff22c435b0107fd739560f4c4e13c16e2683a1ad3f0e0ee7044322";
inline constexpr std::size_t kPolicyArtifactBytes = 1490800U;
inline constexpr std::uint32_t kPolicyThreeAgentBudgetUs = 900000U;

struct PolicyDiagnostics {
  bool ready{false};
  bool vector_test_passed{false};
  bool exact_vector_test_passed{false};
  bool fallback_latched{false};
  std::uint32_t internal_used_bytes{0U};
  std::uint32_t psram_used_bytes{0U};
  std::uint32_t inference_calls{0U};
  std::uint32_t inference_failures{0U};
  std::uint32_t max_inference_us{0U};
  std::uint32_t last_tick_inference_us{0U};
  std::uint32_t boot_three_inference_us{0U};
  float boot_max_logit_error{0.0F};
  float boot_value_error{0.0F};
  float boot_max_hidden_error{0.0F};
};

class PolicyAdapter final : public app::AiActionProvider {
 public:
  PolicyAdapter() = default;
  ~PolicyAdapter() override;

  bool begin() noexcept;
  void reset() noexcept override;
  void beginTick() noexcept override;
  bool select(std::size_t ai_index, const core::EncodedObservation& observation,
              core::Action& action) noexcept override;
  void endTick() noexcept override;
  std::uint64_t stateHash() const noexcept override;

  const PolicyDiagnostics& diagnostics() const noexcept { return diagnostics_; }

 private:
  using HiddenState = std::array<float, 256U>;

  bool resolveContract() noexcept;
  bool validateReleaseEnvelope() noexcept;
  bool failInference() noexcept;

  dl::Model* model_{nullptr};
  dl::TensorBase* spatial_{nullptr};
  dl::TensorBase* scalar_{nullptr};
  dl::TensorBase* hidden_{nullptr};
  dl::TensorBase* logits_{nullptr};
  dl::TensorBase* value_{nullptr};
  dl::TensorBase* next_hidden_{nullptr};
  std::array<HiddenState, core::kAiCount> hidden_states_{};
  PolicyDiagnostics diagnostics_{};
  std::uint32_t current_tick_inference_us_{0U};
};

}  // namespace catamaze::esp32
