// Created at: 2026-11-14 18:58 EST
// Created by: Codex
// Last Modified at: 2026-11-14 18:58 EST
// Last Modified by: Codex
// Implements stable Policy Health mode and failure names for UI and serial diagnostics.

#include "catamaze/app/resident_policy.hpp"

#include <string_view>

namespace catamaze::app {

std::string_view policyModeName(PolicyMode mode) noexcept {
  switch (mode) {
    case PolicyMode::Heuristic:
      return "HEURISTIC";
    case PolicyMode::ModelActive:
      return "MODEL_ACTIVE";
    case PolicyMode::FallbackLatched:
      return "FALLBACK";
  }
  return "HEURISTIC";
}

std::string_view policyFailureName(PolicyFailure failure) noexcept {
  switch (failure) {
    case PolicyFailure::None:
      return "NONE";
    case PolicyFailure::ModelUnavailable:
      return "MODEL_UNAVAILABLE";
    case PolicyFailure::TensorContract:
      return "TENSOR_CONTRACT";
    case PolicyFailure::ReferenceEnvelope:
      return "REFERENCE_ENVELOPE";
    case PolicyFailure::NonFiniteOutput:
      return "NONFINITE_OUTPUT";
    case PolicyFailure::IllegalAction:
      return "ILLEGAL_ACTION";
    case PolicyFailure::LatencyBudget:
      return "LATENCY_BUDGET";
  }
  return "NONE";
}

}  // namespace catamaze::app
