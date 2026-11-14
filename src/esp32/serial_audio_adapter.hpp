// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:50 EST
// Last Modified by: Codex
// Declares best-effort, no-backlog USB Serial audio output and its dropped-event counter.

#pragma once

#include <cstdint>

#include "catamaze/app/audio_event.hpp"

namespace catamaze::esp32 {

class SerialAudioAdapter {
 public:
  bool emit(app::AudioEvent event, std::uint16_t tick);
  std::uint32_t droppedEvents() const noexcept { return dropped_events_; }

 private:
  std::uint32_t sequence_{0U};
  std::uint32_t dropped_events_{0U};
};

}  // namespace catamaze::esp32
