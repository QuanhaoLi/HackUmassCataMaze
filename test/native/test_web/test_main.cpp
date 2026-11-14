// Created at: 2026-11-14 02:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:34 EST
// Last Modified by: Codex
// Provides an isolated GoogleTest entry point for renderer and web-contract tests.

#include <gtest/gtest.h>

int main(int argc, char** argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
