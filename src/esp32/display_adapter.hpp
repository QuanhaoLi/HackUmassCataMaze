// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:56 EST
// Last Modified by: Codex
// Declares independent SSD1306-compatible Map and HUD display adapters on two I2C controllers.

#pragma once

#include <Wire.h>

#include <cstddef>
#include <cstdint>

#include "catamaze/render/framebuffer.hpp"

namespace catamaze::esp32 {

struct DisplayDiagnostics {
  bool map_bus_started{false};
  bool hud_bus_started{false};
  std::uint8_t map_device_count{0U};
  std::uint8_t hud_device_count{0U};
  std::uint8_t map_address{0U};
  std::uint8_t hud_address{0U};
  bool map_initialized{false};
  bool hud_initialized{false};
};

class DisplayAdapter {
 public:
  DisplayAdapter();

  bool begin();
  void queueMap(const render::Framebuffer& framebuffer);
  void queueHud(const render::Framebuffer& framebuffer);
  bool service();
  bool hasPendingFrames() const noexcept { return map_dirty_ || hud_dirty_; }
  const DisplayDiagnostics& diagnostics() const noexcept { return diagnostics_; }

 private:
  static std::uint8_t scan(TwoWire& bus, std::uint8_t& first_address);
  static bool sendCommands(TwoWire& bus, const std::uint8_t* commands, std::size_t count);
  static bool initializePanel(TwoWire& bus);
  static bool writeChunk(TwoWire& bus, const render::Framebuffer& framebuffer, std::size_t& offset,
                         bool& window_sent);

  TwoWire hud_wire_;
  DisplayDiagnostics diagnostics_{};
  render::Framebuffer pending_map_{};
  render::Framebuffer pending_hud_{};
  std::size_t map_offset_{0U};
  std::size_t hud_offset_{0U};
  bool map_window_sent_{false};
  bool hud_window_sent_{false};
  bool map_dirty_{false};
  bool hud_dirty_{false};
  bool service_map_next_{true};
};

}  // namespace catamaze::esp32
