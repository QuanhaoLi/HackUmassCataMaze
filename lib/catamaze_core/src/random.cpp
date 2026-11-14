// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:32 EST
// Last Modified by: Codex
// Implements reference PCG-XSH-RR output and unbiased bounded sampling.

#include "catamaze/core/random.hpp"

namespace catamaze::core {

Pcg32::Pcg32(std::uint64_t seed, std::uint64_t sequence) noexcept
    : increment_((sequence << 1U) | 1U) {
  next();
  state_ += seed;
  next();
}

std::uint32_t Pcg32::next() noexcept {
  const std::uint64_t old_state = state_;
  state_ = old_state * 6364136223846793005ULL + increment_;
  const auto xorshifted = static_cast<std::uint32_t>(
      ((old_state >> 18U) ^ old_state) >> 27U);
  const auto rotation = static_cast<std::uint32_t>(old_state >> 59U);
  return (xorshifted >> rotation) |
         (xorshifted << ((0U - rotation) & 31U));
}

std::uint32_t Pcg32::bounded(std::uint32_t upper_bound) noexcept {
  if (upper_bound == 0U) {
    return 0U;
  }
  const std::uint32_t threshold = (0U - upper_bound) % upper_bound;
  for (;;) {
    const std::uint32_t value = next();
    if (value >= threshold) {
      return value % upper_bound;
    }
  }
}

}  // namespace catamaze::core
