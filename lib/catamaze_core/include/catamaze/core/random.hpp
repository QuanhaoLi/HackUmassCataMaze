// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Declares the repository-owned PCG32 generator used for cross-target determinism.

#pragma once

#include <cstdint>

namespace catamaze::core {

class Pcg32 {
 public:
  explicit Pcg32(std::uint64_t seed, std::uint64_t sequence = 0x9e3779b97f4a7c15ULL) noexcept;

  std::uint32_t next() noexcept;
  std::uint32_t bounded(std::uint32_t upper_bound) noexcept;
  std::uint64_t state() const noexcept { return state_; }
  std::uint64_t increment() const noexcept { return increment_; }

 private:
  std::uint64_t state_{0};
  std::uint64_t increment_{0};
};

}  // namespace catamaze::core
