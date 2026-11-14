// Created at: 2026-11-14 04:37 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:50 EST
// Last Modified by: Codex
// Declares canonical player-observable audio events shared by Native and ESP32 adapters.

#pragma once

#include <cstddef>
#include <cstdint>
#include <string_view>

#include "catamaze/core/engine.hpp"

namespace catamaze::app {

enum class AudioEvent : std::uint8_t {
  None = 0,
  PlayerShot = 1,
  EnemyShotHeard = 2,
  PlayerDamage = 3,
  PlayerDeath = 4,
  PlayerVictory = 5,
};

AudioEvent selectAudioEvent(const core::WorldState& state) noexcept;
std::string_view audioEventName(AudioEvent event) noexcept;
std::uint8_t audioEventPriority(AudioEvent event) noexcept;
std::size_t formatAudioSerialLine(AudioEvent event, std::uint32_t sequence, std::uint16_t tick,
                                  char* output, std::size_t capacity) noexcept;

}  // namespace catamaze::app
