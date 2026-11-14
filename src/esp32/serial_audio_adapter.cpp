// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 05:43 EST
// Last Modified by: Codex
// Emits one complete canonical audio line only when USB Serial is connected and has capacity.

#include "serial_audio_adapter.hpp"

#include <Arduino.h>

#include <array>
#include <cstddef>
#include <cstdint>

namespace catamaze::esp32 {

bool SerialAudioAdapter::emit(app::AudioEvent event, std::uint16_t tick) {
  if (event == app::AudioEvent::None) return true;
  std::array<char, 128> line{};
  const std::uint32_t event_sequence = sequence_++;
  const std::size_t length =
      app::formatAudioSerialLine(event, event_sequence, tick, line.data(), line.size());
  if (length == 0U || Serial0.availableForWrite() < static_cast<int>(length)) {
    ++dropped_events_;
    return false;
  }
  const std::size_t written =
      Serial0.write(reinterpret_cast<const std::uint8_t*>(line.data()), length);
  if (written != length) {
    ++dropped_events_;
    return false;
  }
  return true;
}

}  // namespace catamaze::esp32
