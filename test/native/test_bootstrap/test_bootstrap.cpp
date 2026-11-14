// Created at: 2026-11-14 02:13 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Verifies that GoogleTest links against the portable Game Core library.

#include <gtest/gtest.h>

#include "catamaze/core/version.hpp"

TEST(Bootstrap, ExposesStableVersionIdentifiers) {
  EXPECT_EQ(catamaze::core::kProductName, "CataMaze");
  EXPECT_EQ(catamaze::core::kRulesVersion, "catamaze.rules.v1");
  EXPECT_EQ(catamaze::core::kCoreVersion, "0.1.0");
}

int main(int argc, char** argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
