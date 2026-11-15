// Created at: 2026-11-14 11:30 EST
// Created by: Codex
// Last Modified at: 2026-11-14 19:00 EST
// Last Modified by: Codex
// Declares explicit-time Companion Idle and inactivity coordination outside deterministic game
// state.

#pragma once

#include <cstdint>
#include <string_view>

#include "catamaze/app/system_controller.hpp"

namespace catamaze::app {

enum class ProductMode : std::uint8_t {
  CompanionIdle = 0,
  Active = 1,
  InactivityPrompt = 2,
};

enum class CompanionFrame : std::uint8_t {
  Neutral = 0,
  LookLeft = 1,
  BlinkHalf = 2,
  BlinkClosed = 3,
  LookRight = 4,
  Happy = 5,
  Curious = 6,
  Sleepy = 7,
  Surprised = 8,
};

struct ProductSnapshot {
  ProductMode mode{ProductMode::CompanionIdle};
  SystemSnapshot system{};
  PolicyHealth policy_health{};
  CompanionFrame companion_frame{CompanionFrame::Neutral};
  std::uint8_t prompt_focus{0U};
  bool prompt_resumes_playing{false};
};

class ProductShell {
 public:
  inline static constexpr std::uint32_t kInactivityMs = 30000U;
  inline static constexpr std::uint32_t kCompanionCycleMs = 24000U;

  explicit ProductShell(std::uint64_t first_seed) noexcept;

  void begin(std::uint32_t now_ms) noexcept;
  bool handle(SystemInput input, std::uint32_t now_ms) noexcept;
  bool update(std::uint32_t now_ms) noexcept;
  void tick() noexcept;

  const ProductSnapshot& snapshot() const noexcept { return snapshot_; }
  const SystemController& system() const noexcept { return system_; }
  SystemController& system() noexcept { return system_; }
  const Application& application() const noexcept { return system_.application(); }
  Application& application() noexcept { return system_.application(); }
  core::PlayerObservation playerObservation() const noexcept;

 private:
  void syncSystemSnapshot() noexcept;
  void enterIdle(std::uint32_t now_ms) noexcept;
  void enterPrompt(bool resumes_playing) noexcept;
  void continueFromPrompt() noexcept;
  static std::uint32_t elapsed(std::uint32_t now_ms, std::uint32_t since_ms) noexcept;

  SystemController system_;
  ProductSnapshot snapshot_{};
  std::uint32_t last_activity_ms_{0U};
  std::uint32_t idle_started_ms_{0U};
  bool clock_initialized_{false};
};

CompanionFrame companionFrameAt(std::uint32_t idle_elapsed_ms) noexcept;
std::string_view productModeName(ProductMode mode) noexcept;
std::string_view companionFrameName(CompanionFrame frame) noexcept;

}  // namespace catamaze::app
