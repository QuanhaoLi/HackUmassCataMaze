// Created at: 2026-11-14 07:02 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:02 EST
// Last Modified by: Codex
// Declares portable Home, Setup, Game, Pause, Result, and six-button navigation semantics.

#pragma once

#include <cstdint>
#include <string_view>

#include "catamaze/app/application.hpp"

namespace catamaze::app {

enum class SystemMode : std::uint8_t {
  Home = 0,
  Setup = 1,
  System = 2,
  About = 3,
  Playing = 4,
  Paused = 5,
  ConfirmHome = 6,
  Result = 7,
};

enum class SystemInput : std::uint8_t {
  Up = 0,
  Down = 1,
  Left = 2,
  Right = 3,
  ShootUp = 4,
  ShootDown = 5,
  ShootLeft = 6,
  ShootRight = 7,
  Fire = 8,
  ClearShort = 9,
  ClearLong = 10,
};

struct SystemSnapshot {
  SystemMode mode{SystemMode::Home};
  std::uint8_t focus{0U};
  std::uint8_t confirmed_map_size{30U};
  std::uint8_t pending_map_size{30U};
  std::uint64_t active_seed{0U};
  std::uint64_t next_seed{0U};
  std::uint16_t tick_budget{1200U};
  core::GameStatus game_status{core::GameStatus::Running};
  bool has_active_session{false};
};

class SystemController {
 public:
  explicit SystemController(std::uint64_t first_seed) noexcept;

  bool handle(SystemInput input) noexcept;
  void tick() noexcept;

  const SystemSnapshot& snapshot() const noexcept { return snapshot_; }
  const Application& application() const noexcept { return application_; }
  Application& application() noexcept { return application_; }
  core::PlayerObservation playerObservation() const noexcept;

 private:
  void enterHome() noexcept;
  void startNewRun(bool advance_seed) noexcept;
  void restartSameRun() noexcept;
  void handleHome(SystemInput input) noexcept;
  void handleSetup(SystemInput input) noexcept;
  void handleSystem(SystemInput input) noexcept;
  void handlePlaying(SystemInput input) noexcept;
  void handlePaused(SystemInput input) noexcept;
  void handleConfirmHome(SystemInput input) noexcept;
  void handleResult(SystemInput input) noexcept;
  void moveFocus(int delta, std::uint8_t count) noexcept;
  void cycleMapPreset(int delta) noexcept;
  static std::uint64_t nextSeed(std::uint64_t seed) noexcept;

  Application application_;
  SystemSnapshot snapshot_{};
};

std::string_view systemModeName(SystemMode mode) noexcept;
std::string_view mapPresetName(std::uint8_t map_size) noexcept;

}  // namespace catamaze::app
