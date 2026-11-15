// Created at: 2026-11-14 18:58 EST
// Created by: Codex
// Last Modified at: 2026-11-14 18:58 EST
// Last Modified by: Codex
// Declares atomic three-AI policy decisions and bounded product-visible policy health.

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string_view>

#include "catamaze/core/policy_contract.hpp"

namespace catamaze::app {

enum class PolicyMode : std::uint8_t {
  Heuristic = 0,
  ModelActive = 1,
  FallbackLatched = 2,
};

enum class PolicyFailure : std::uint8_t {
  None = 0,
  ModelUnavailable = 1,
  TensorContract = 2,
  ReferenceEnvelope = 3,
  NonFiniteOutput = 4,
  IllegalAction = 5,
  LatencyBudget = 6,
};

struct PolicyTickInput {
  std::array<core::EncodedObservation, core::kAiCount> observations{};
  std::array<bool, core::kAiCount> active{};
};

struct PolicyHealth {
  PolicyMode mode{PolicyMode::Heuristic};
  PolicyFailure failure{PolicyFailure::None};
  bool vector_test_passed{false};
  bool exact_vector_test_passed{false};
  std::uint32_t internal_used_bytes{0U};
  std::uint32_t psram_used_bytes{0U};
  std::uint32_t inference_calls{0U};
  std::uint32_t inference_failures{0U};
  std::uint32_t last_tick_inference_us{0U};
  std::uint32_t max_tick_inference_us{0U};
  std::uint32_t boot_three_inference_us{0U};
  float boot_max_logit_error{0.0F};
  float boot_value_error{0.0F};
  float boot_max_hidden_error{0.0F};
};

class ResidentPolicyModule {
 public:
  virtual ~ResidentPolicyModule() = default;
  virtual void resetSession() noexcept = 0;
  virtual bool selectTick(const PolicyTickInput& input,
                          std::array<core::Action, core::kAiCount>& actions) noexcept = 0;
  virtual std::uint64_t stateHash() const noexcept { return 0U; }
  virtual const PolicyHealth& health() const noexcept = 0;
};

std::string_view policyModeName(PolicyMode mode) noexcept;
std::string_view policyFailureName(PolicyFailure failure) noexcept;

}  // namespace catamaze::app
