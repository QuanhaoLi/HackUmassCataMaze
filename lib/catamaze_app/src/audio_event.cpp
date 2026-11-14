// Created at: 2026-11-14 04:37 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:50 EST
// Last Modified by: Codex
// Selects one highest-priority audio event without serializing hidden game state.

#include "catamaze/app/audio_event.hpp"

#include <cstddef>
#include <cstdint>
#include <cstdio>

namespace catamaze::app {
namespace {

std::int16_t absolute(std::int16_t value) noexcept {
  return value < 0 ? static_cast<std::int16_t>(-value) : value;
}

void selectHigher(AudioEvent candidate, AudioEvent& selected) noexcept {
  if (audioEventPriority(candidate) > audioEventPriority(selected)) {
    selected = candidate;
  }
}

}  // namespace

std::uint8_t audioEventPriority(AudioEvent event) noexcept {
  switch (event) {
    case AudioEvent::None:
      return 0U;
    case AudioEvent::PlayerShot:
      return 2U;
    case AudioEvent::EnemyShotHeard:
      return 3U;
    case AudioEvent::PlayerDamage:
      return 4U;
    case AudioEvent::PlayerDeath:
    case AudioEvent::PlayerVictory:
      return 5U;
  }
  return 0U;
}

std::string_view audioEventName(AudioEvent event) noexcept {
  switch (event) {
    case AudioEvent::None:
      return "NONE";
    case AudioEvent::PlayerShot:
      return "PLAYER_SHOT";
    case AudioEvent::EnemyShotHeard:
      return "ENEMY_SHOT_HEARD";
    case AudioEvent::PlayerDamage:
      return "PLAYER_DAMAGE";
    case AudioEvent::PlayerDeath:
      return "PLAYER_DEATH";
    case AudioEvent::PlayerVictory:
      return "PLAYER_VICTORY";
  }
  return "NONE";
}

AudioEvent selectAudioEvent(const core::WorldState& state) noexcept {
  AudioEvent selected = AudioEvent::None;
  const auto& player = state.entities[core::entityIndex(core::EntityId::Player)];

  for (std::size_t index = 0; index < state.event_count; ++index) {
    const core::Event& event = state.events[index];
    if (event.type == core::EventType::Shot) {
      if (event.actor == core::EntityId::Player) {
        selectHigher(AudioEvent::PlayerShot, selected);
      } else {
        const auto dx = static_cast<std::int16_t>(event.position.x - player.position.x);
        const auto dy = static_cast<std::int16_t>(event.position.y - player.position.y);
        if (absolute(dx) <= 3 && absolute(dy) <= 3) {
          selectHigher(AudioEvent::EnemyShotHeard, selected);
        }
      }
    } else if (event.type == core::EventType::DamageApplied &&
               event.target == core::EntityId::Player) {
      selectHigher(AudioEvent::PlayerDamage, selected);
    } else if (event.type == core::EventType::GameEnded) {
      if (state.status == core::GameStatus::Death) {
        selectHigher(AudioEvent::PlayerDeath, selected);
      } else if (state.status == core::GameStatus::Victory) {
        selectHigher(AudioEvent::PlayerVictory, selected);
      }
    }
  }
  return selected;
}

std::size_t formatAudioSerialLine(AudioEvent event, std::uint32_t sequence, std::uint16_t tick,
                                  char* output, std::size_t capacity) noexcept {
  if (output == nullptr || capacity == 0U || event == AudioEvent::None) {
    return 0U;
  }
  const int written =
      std::snprintf(output, capacity,
                    "CATAMAZE_AUDIO {\"schema\":\"catamaze.audio.v1\",\"seq\":%lu,"
                    "\"tick\":%u,\"event\":\"%.*s\"}\n",
                    static_cast<unsigned long>(sequence), static_cast<unsigned>(tick),
                    static_cast<int>(audioEventName(event).size()), audioEventName(event).data());
  if (written < 0 || static_cast<std::size_t>(written) >= capacity) {
    output[0] = '\0';
    return 0U;
  }
  return static_cast<std::size_t>(written);
}

}  // namespace catamaze::app
