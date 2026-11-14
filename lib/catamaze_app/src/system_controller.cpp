// Created at: 2026-11-14 07:02 EST
// Created by: Codex
// Last Modified at: 2026-11-14 11:30 EST
// Last Modified by: Codex
// Implements deterministic launcher, preset, pause, confirmation, and result transitions.

#include "catamaze/app/system_controller.hpp"

#include <cstddef>
#include <cstdint>

namespace catamaze::app {
namespace {

constexpr std::uint8_t kDefaultMapSize = 30U;

core::Action movementFor(SystemInput input) noexcept {
  switch (input) {
    case SystemInput::Up:
      return core::Action::MoveUp;
    case SystemInput::Down:
      return core::Action::MoveDown;
    case SystemInput::Left:
      return core::Action::MoveLeft;
    case SystemInput::Right:
      return core::Action::MoveRight;
    case SystemInput::ShootUp:
      return core::Action::ShootUp;
    case SystemInput::ShootDown:
      return core::Action::ShootDown;
    case SystemInput::ShootLeft:
      return core::Action::ShootLeft;
    case SystemInput::ShootRight:
      return core::Action::ShootRight;
    case SystemInput::Fire:
    case SystemInput::ClearShort:
    case SystemInput::ClearLong:
      return core::Action::Wait;
  }
  return core::Action::Wait;
}

bool isGameplayAction(SystemInput input) noexcept {
  return input >= SystemInput::Up && input <= SystemInput::ShootRight;
}

}  // namespace

SystemController::SystemController(std::uint64_t first_seed) noexcept
    : application_(core::GameConfig{kDefaultMapSize, first_seed}) {
  snapshot_.confirmed_map_size = kDefaultMapSize;
  snapshot_.pending_map_size = kDefaultMapSize;
  snapshot_.next_seed = first_seed;
  snapshot_.tick_budget = core::tickBudgetForMapSize(kDefaultMapSize);
}

void SystemController::moveFocus(int delta, std::uint8_t count) noexcept {
  const int next = static_cast<int>(snapshot_.focus) + delta;
  if (next >= 0 && next < count) snapshot_.focus = static_cast<std::uint8_t>(next);
}

void SystemController::cycleMapPreset(int delta) noexcept {
  std::size_t index = 0U;
  for (; index < core::kMapPresets.size(); ++index) {
    if (core::kMapPresets[index] == snapshot_.pending_map_size) break;
  }
  const int count = static_cast<int>(core::kMapPresets.size());
  const int next = (static_cast<int>(index) + delta + count) % count;
  snapshot_.pending_map_size = core::kMapPresets[static_cast<std::size_t>(next)];
  snapshot_.tick_budget = core::tickBudgetForMapSize(snapshot_.pending_map_size);
}

std::uint64_t SystemController::nextSeed(std::uint64_t seed) noexcept {
  seed += 0x9e3779b97f4a7c15ULL;
  std::uint64_t mixed = seed;
  mixed = (mixed ^ (mixed >> 30U)) * 0xbf58476d1ce4e5b9ULL;
  mixed = (mixed ^ (mixed >> 27U)) * 0x94d049bb133111ebULL;
  return mixed ^ (mixed >> 31U);
}

void SystemController::startNewRun(bool advance_seed) noexcept {
  snapshot_.confirmed_map_size = snapshot_.pending_map_size;
  snapshot_.active_seed = snapshot_.next_seed;
  if (advance_seed) snapshot_.next_seed = nextSeed(snapshot_.next_seed);
  snapshot_.tick_budget = core::tickBudgetForMapSize(snapshot_.confirmed_map_size);
  application_.reset(core::GameConfig{snapshot_.confirmed_map_size, snapshot_.active_seed});
  snapshot_.mode = SystemMode::Playing;
  snapshot_.focus = 0U;
  snapshot_.game_status = core::GameStatus::Running;
  snapshot_.has_active_session = true;
}

void SystemController::restartSameRun() noexcept {
  application_.reset(core::GameConfig{snapshot_.confirmed_map_size, snapshot_.active_seed});
  snapshot_.mode = SystemMode::Playing;
  snapshot_.focus = 0U;
  snapshot_.game_status = core::GameStatus::Running;
  snapshot_.has_active_session = true;
}

void SystemController::enterHome() noexcept {
  snapshot_.mode = SystemMode::Home;
  snapshot_.focus = 0U;
  snapshot_.pending_map_size = snapshot_.confirmed_map_size;
  snapshot_.tick_budget = core::tickBudgetForMapSize(snapshot_.confirmed_map_size);
  snapshot_.has_active_session = false;
}

void SystemController::handleHome(SystemInput input) noexcept {
  if (input == SystemInput::Up) moveFocus(-1, 4U);
  if (input == SystemInput::Down) moveFocus(1, 4U);
  if (input != SystemInput::Fire) return;
  switch (snapshot_.focus) {
    case 0U:
      snapshot_.pending_map_size = snapshot_.confirmed_map_size;
      startNewRun(true);
      break;
    case 1U:
      snapshot_.mode = SystemMode::Setup;
      snapshot_.focus = 0U;
      snapshot_.pending_map_size = snapshot_.confirmed_map_size;
      break;
    case 2U:
      snapshot_.mode = SystemMode::System;
      snapshot_.focus = 0U;
      break;
    case 3U:
      snapshot_.mode = SystemMode::About;
      snapshot_.focus = 0U;
      break;
    default:
      break;
  }
}

void SystemController::handleSetup(SystemInput input) noexcept {
  if (input == SystemInput::ClearShort || input == SystemInput::ClearLong) {
    enterHome();
    return;
  }
  if (input == SystemInput::Up) moveFocus(-1, 2U);
  if (input == SystemInput::Down) moveFocus(1, 2U);
  if (snapshot_.focus == 0U && input == SystemInput::Left) cycleMapPreset(-1);
  if (snapshot_.focus == 0U && input == SystemInput::Right) cycleMapPreset(1);
  if (input == SystemInput::Fire) {
    if (snapshot_.focus == 0U) {
      snapshot_.focus = 1U;
    } else {
      startNewRun(true);
    }
  }
}

void SystemController::handleSystem(SystemInput input) noexcept {
  if (input == SystemInput::ClearShort || input == SystemInput::ClearLong) {
    enterHome();
    return;
  }
  if (input == SystemInput::Up) moveFocus(-1, 3U);
  if (input == SystemInput::Down) moveFocus(1, 3U);
}

void SystemController::handlePlaying(SystemInput input) noexcept {
  if (input == SystemInput::ClearShort) {
    application_.clearPlayerQueue();
  } else if (input == SystemInput::ClearLong) {
    snapshot_.mode = SystemMode::Paused;
    snapshot_.focus = 0U;
  } else if (isGameplayAction(input)) {
    application_.enqueuePlayerAction(movementFor(input));
  }
}

void SystemController::handlePaused(SystemInput input) noexcept {
  if (input == SystemInput::ClearShort) {
    snapshot_.mode = SystemMode::Playing;
    snapshot_.focus = 0U;
    return;
  }
  if (input == SystemInput::Up) moveFocus(-1, 3U);
  if (input == SystemInput::Down) moveFocus(1, 3U);
  if (input != SystemInput::Fire) return;
  if (snapshot_.focus == 0U) {
    snapshot_.mode = SystemMode::Playing;
  } else if (snapshot_.focus == 1U) {
    restartSameRun();
  } else {
    snapshot_.mode = SystemMode::ConfirmHome;
    snapshot_.focus = 0U;
  }
}

void SystemController::handleConfirmHome(SystemInput input) noexcept {
  if (input == SystemInput::ClearShort) {
    snapshot_.mode = SystemMode::Paused;
    snapshot_.focus = 2U;
    return;
  }
  if (input == SystemInput::Up) moveFocus(-1, 2U);
  if (input == SystemInput::Down) moveFocus(1, 2U);
  if (input != SystemInput::Fire) return;
  if (snapshot_.focus == 0U) {
    snapshot_.mode = SystemMode::Paused;
    snapshot_.focus = 2U;
  } else {
    enterHome();
  }
}

void SystemController::handleResult(SystemInput input) noexcept {
  if (input == SystemInput::ClearShort || input == SystemInput::ClearLong) {
    enterHome();
    return;
  }
  if (input == SystemInput::Up) moveFocus(-1, 3U);
  if (input == SystemInput::Down) moveFocus(1, 3U);
  if (input != SystemInput::Fire) return;
  if (snapshot_.focus == 0U) {
    restartSameRun();
  } else if (snapshot_.focus == 1U) {
    snapshot_.pending_map_size = snapshot_.confirmed_map_size;
    startNewRun(true);
  } else {
    enterHome();
  }
}

bool SystemController::handle(SystemInput input) noexcept {
  const SystemSnapshot before = snapshot_;
  const std::size_t queue_before = application_.state().player_queue.size();
  switch (snapshot_.mode) {
    case SystemMode::Home:
      handleHome(input);
      break;
    case SystemMode::Setup:
      handleSetup(input);
      break;
    case SystemMode::System:
      handleSystem(input);
      break;
    case SystemMode::About:
      if (input == SystemInput::ClearShort || input == SystemInput::ClearLong) {
        enterHome();
      }
      break;
    case SystemMode::Playing:
      handlePlaying(input);
      break;
    case SystemMode::Paused:
      handlePaused(input);
      break;
    case SystemMode::ConfirmHome:
      handleConfirmHome(input);
      break;
    case SystemMode::Result:
      handleResult(input);
      break;
  }
  return before.mode != snapshot_.mode || before.focus != snapshot_.focus ||
         before.pending_map_size != snapshot_.pending_map_size ||
         queue_before != application_.state().player_queue.size();
}

void SystemController::tick() noexcept {
  if (snapshot_.mode != SystemMode::Playing) return;
  application_.tick();
  snapshot_.game_status = application_.state().status;
  if (snapshot_.game_status != core::GameStatus::Running) {
    snapshot_.mode = SystemMode::Result;
    snapshot_.focus = 0U;
  }
}

void SystemController::abandonToHome() noexcept { enterHome(); }

core::PlayerObservation SystemController::playerObservation() const noexcept {
  return application_.playerObservation();
}

std::string_view systemModeName(SystemMode mode) noexcept {
  switch (mode) {
    case SystemMode::Home:
      return "HOME";
    case SystemMode::Setup:
      return "SETUP";
    case SystemMode::System:
      return "SYSTEM";
    case SystemMode::About:
      return "ABOUT";
    case SystemMode::Playing:
      return "PLAYING";
    case SystemMode::Paused:
      return "PAUSED";
    case SystemMode::ConfirmHome:
      return "CONFIRM_HOME";
    case SystemMode::Result:
      return "RESULT";
  }
  return "HOME";
}

std::string_view mapPresetName(std::uint8_t map_size) noexcept {
  switch (map_size) {
    case 12U:
      return "TINY";
    case 20U:
      return "SMALL";
    case 30U:
      return "MEDIUM";
    case 50U:
      return "ORIGINAL";
    default:
      return "ORIGINAL";
  }
}

}  // namespace catamaze::app
