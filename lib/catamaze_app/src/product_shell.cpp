// Created at: 2026-11-14 11:30 EST
// Created by: Codex
// Last Modified at: 2026-11-14 19:00 EST
// Last Modified by: Codex
// Implements wrap-safe Companion Idle, consumed Wake, and guarded inactivity transitions.

#include "catamaze/app/product_shell.hpp"

#include <cstdint>

namespace catamaze::app {

CompanionFrame companionFrameAt(std::uint32_t idle_elapsed_ms) noexcept {
  const std::uint32_t phase = idle_elapsed_ms % ProductShell::kCompanionCycleMs;
  if (phase < 3000U) return CompanionFrame::Neutral;
  if (phase < 5000U) return CompanionFrame::LookLeft;
  if (phase < 5100U) return CompanionFrame::BlinkHalf;
  if (phase < 5300U) return CompanionFrame::BlinkClosed;
  if (phase < 5400U) return CompanionFrame::BlinkHalf;
  if (phase < 7500U) return CompanionFrame::LookRight;
  if (phase < 10000U) return CompanionFrame::Happy;
  if (phase < 13500U) return CompanionFrame::Curious;
  if (phase < 15000U) return CompanionFrame::Neutral;
  if (phase < 17500U) return CompanionFrame::Sleepy;
  if (phase < 19500U) return CompanionFrame::Surprised;
  return CompanionFrame::Neutral;
}

ProductShell::ProductShell(std::uint64_t first_seed) noexcept : system_(first_seed) {
  syncSystemSnapshot();
}

std::uint32_t ProductShell::elapsed(std::uint32_t now_ms, std::uint32_t since_ms) noexcept {
  return now_ms - since_ms;
}

void ProductShell::syncSystemSnapshot() noexcept {
  snapshot_.system = system_.snapshot();
  snapshot_.policy_health = system_.application().policyHealth();
}

void ProductShell::begin(std::uint32_t now_ms) noexcept {
  last_activity_ms_ = now_ms;
  idle_started_ms_ = now_ms;
  snapshot_.companion_frame = CompanionFrame::Neutral;
  clock_initialized_ = true;
  syncSystemSnapshot();
}

void ProductShell::enterIdle(std::uint32_t now_ms) noexcept {
  system_.abandonToHome();
  snapshot_.mode = ProductMode::CompanionIdle;
  snapshot_.prompt_focus = 0U;
  snapshot_.prompt_resumes_playing = false;
  snapshot_.companion_frame = CompanionFrame::Neutral;
  idle_started_ms_ = now_ms;
  last_activity_ms_ = now_ms;
  syncSystemSnapshot();
}

void ProductShell::enterPrompt(bool resumes_playing) noexcept {
  snapshot_.mode = ProductMode::InactivityPrompt;
  snapshot_.prompt_focus = 0U;
  snapshot_.prompt_resumes_playing = resumes_playing;
  syncSystemSnapshot();
}

void ProductShell::continueFromPrompt() noexcept {
  if (snapshot_.prompt_resumes_playing && system_.snapshot().mode == SystemMode::Paused) {
    system_.handle(SystemInput::ClearShort);
  }
  snapshot_.mode = ProductMode::Active;
  snapshot_.prompt_focus = 0U;
  snapshot_.prompt_resumes_playing = false;
  syncSystemSnapshot();
}

bool ProductShell::handle(SystemInput input, std::uint32_t now_ms) noexcept {
  if (!clock_initialized_) begin(now_ms);
  last_activity_ms_ = now_ms;

  if (snapshot_.mode == ProductMode::CompanionIdle) {
    snapshot_.mode = ProductMode::Active;
    syncSystemSnapshot();
    return true;
  }

  if (snapshot_.mode == ProductMode::InactivityPrompt) {
    if (input == SystemInput::ClearShort) {
      continueFromPrompt();
      return true;
    }
    if (input == SystemInput::Up && snapshot_.prompt_focus > 0U) {
      --snapshot_.prompt_focus;
      return true;
    }
    if (input == SystemInput::Down && snapshot_.prompt_focus < 1U) {
      ++snapshot_.prompt_focus;
      return true;
    }
    if (input == SystemInput::Fire) {
      if (snapshot_.prompt_focus == 0U) {
        continueFromPrompt();
      } else {
        enterIdle(now_ms);
      }
      return true;
    }
    return false;
  }

  if (system_.snapshot().mode == SystemMode::Home && input == SystemInput::ClearLong) {
    enterIdle(now_ms);
    return true;
  }
  const bool changed = system_.handle(input);
  syncSystemSnapshot();
  return changed;
}

bool ProductShell::update(std::uint32_t now_ms) noexcept {
  if (!clock_initialized_) {
    begin(now_ms);
    return false;
  }

  if (snapshot_.mode == ProductMode::CompanionIdle) {
    const CompanionFrame next = companionFrameAt(elapsed(now_ms, idle_started_ms_));
    if (next == snapshot_.companion_frame) return false;
    snapshot_.companion_frame = next;
    return true;
  }
  if (snapshot_.mode == ProductMode::InactivityPrompt ||
      elapsed(now_ms, last_activity_ms_) < kInactivityMs) {
    return false;
  }

  switch (system_.snapshot().mode) {
    case SystemMode::Playing:
      system_.handle(SystemInput::ClearLong);
      enterPrompt(true);
      return true;
    case SystemMode::Paused:
      enterPrompt(false);
      return true;
    case SystemMode::ConfirmHome:
      return false;
    case SystemMode::Home:
    case SystemMode::Setup:
    case SystemMode::System:
    case SystemMode::About:
    case SystemMode::Result:
      enterIdle(now_ms);
      return true;
  }
  return false;
}

void ProductShell::tick() noexcept {
  if (snapshot_.mode != ProductMode::Active) return;
  system_.tick();
  syncSystemSnapshot();
}

core::PlayerObservation ProductShell::playerObservation() const noexcept {
  return system_.playerObservation();
}

std::string_view productModeName(ProductMode mode) noexcept {
  switch (mode) {
    case ProductMode::CompanionIdle:
      return "IDLE";
    case ProductMode::Active:
      return "ACTIVE";
    case ProductMode::InactivityPrompt:
      return "INACTIVITY_PROMPT";
  }
  return "IDLE";
}

std::string_view companionFrameName(CompanionFrame frame) noexcept {
  switch (frame) {
    case CompanionFrame::Neutral:
      return "NEUTRAL";
    case CompanionFrame::LookLeft:
      return "LOOK_LEFT";
    case CompanionFrame::BlinkHalf:
      return "BLINK_HALF";
    case CompanionFrame::BlinkClosed:
      return "BLINK_CLOSED";
    case CompanionFrame::LookRight:
      return "LOOK_RIGHT";
    case CompanionFrame::Happy:
      return "HAPPY";
    case CompanionFrame::Curious:
      return "CURIOUS";
    case CompanionFrame::Sleepy:
      return "SLEEPY";
    case CompanionFrame::Surprised:
      return "SURPRISED";
  }
  return "NEUTRAL";
}

}  // namespace catamaze::app
