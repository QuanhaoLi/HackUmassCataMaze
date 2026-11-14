// Created at: 2026-11-14 02:13 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:13 EST
// Last Modified by: Codex
// Bootstraps the Native target without introducing platform concerns into Game Core.

#include <iostream>

#include "catamaze/core/version.hpp"

int main() {
  std::cout << catamaze::core::kProductName << " Native "
            << catamaze::core::kCoreVersion << " ("
            << catamaze::core::kRulesVersion << ")\n";
  return 0;
}
