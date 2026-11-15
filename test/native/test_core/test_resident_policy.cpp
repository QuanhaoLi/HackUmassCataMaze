// Created at: 2026-11-14 18:58 EST
// Created by: Codex
// Last Modified at: 2026-11-14 18:58 EST
// Last Modified by: Codex
// Verifies stable product-visible Resident Policy mode and failure names.

#include <gtest/gtest.h>

#include "catamaze/app/resident_policy.hpp"

namespace catamaze::app {
namespace {

TEST(ResidentPolicy, PublicModeAndFailureNamesAreStable) {
  EXPECT_EQ(policyModeName(PolicyMode::Heuristic), "HEURISTIC");
  EXPECT_EQ(policyModeName(PolicyMode::ModelActive), "MODEL_ACTIVE");
  EXPECT_EQ(policyModeName(PolicyMode::FallbackLatched), "FALLBACK");
  EXPECT_EQ(policyFailureName(PolicyFailure::None), "NONE");
  EXPECT_EQ(policyFailureName(PolicyFailure::ModelUnavailable), "MODEL_UNAVAILABLE");
  EXPECT_EQ(policyFailureName(PolicyFailure::TensorContract), "TENSOR_CONTRACT");
  EXPECT_EQ(policyFailureName(PolicyFailure::ReferenceEnvelope), "REFERENCE_ENVELOPE");
  EXPECT_EQ(policyFailureName(PolicyFailure::NonFiniteOutput), "NONFINITE_OUTPUT");
  EXPECT_EQ(policyFailureName(PolicyFailure::IllegalAction), "ILLEGAL_ACTION");
  EXPECT_EQ(policyFailureName(PolicyFailure::LatencyBudget), "LATENCY_BUDGET");
}

}  // namespace
}  // namespace catamaze::app
