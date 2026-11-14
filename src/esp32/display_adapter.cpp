// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:56 EST
// Last Modified by: Codex
// Initializes and writes two independent SSD1306-compatible displays using validated 16-byte
// chunks.

#include "display_adapter.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

#include "hardware_config.hpp"

namespace catamaze::esp32 {
namespace {

constexpr std::array<std::uint8_t, 25> kInitializationCommands{
    0xae, 0xd5, 0x80, 0xa8, 0x3f, 0xd3, 0x00, 0x40, 0x8d, 0x14, 0x20, 0x00, 0xa1,
    0xc8, 0xda, 0x12, 0x81, 0xcf, 0xd9, 0xf1, 0xdb, 0x40, 0xa4, 0xa6, 0xaf};
constexpr std::array<std::uint8_t, 6> kFullWindowCommands{0x21, 0x00, 0x7f, 0x22, 0x00, 0x07};
constexpr std::size_t kDataChunkBytes = 16U;

}  // namespace

DisplayAdapter::DisplayAdapter() : hud_wire_(1U) {}

std::uint8_t DisplayAdapter::scan(TwoWire& bus, std::uint8_t& first_address) {
  std::uint8_t count = 0U;
  first_address = 0U;
  for (std::uint8_t address = 1U; address < 127U; ++address) {
    bus.beginTransmission(address);
    if (bus.endTransmission() == 0U) {
      if (count == 0U) first_address = address;
      ++count;
    }
  }
  return count;
}

bool DisplayAdapter::sendCommands(TwoWire& bus, const std::uint8_t* commands, std::size_t count) {
  bus.beginTransmission(kDisplayAddress);
  bus.write(0x00U);
  for (std::size_t index = 0; index < count; ++index) bus.write(commands[index]);
  return bus.endTransmission() == 0U;
}

bool DisplayAdapter::initializePanel(TwoWire& bus) {
  return sendCommands(bus, kInitializationCommands.data(), kInitializationCommands.size());
}

bool DisplayAdapter::writeChunk(TwoWire& bus, const render::Framebuffer& framebuffer,
                                std::size_t& offset, bool& window_sent) {
  if (!window_sent) {
    if (!sendCommands(bus, kFullWindowCommands.data(), kFullWindowCommands.size())) {
      return false;
    }
    window_sent = true;
  }
  const auto& bytes = framebuffer.bytes();
  bus.beginTransmission(kDisplayAddress);
  bus.write(0x40U);
  bus.write(bytes.data() + offset, kDataChunkBytes);
  if (bus.endTransmission() != 0U) return false;
  offset += kDataChunkBytes;
  return true;
}

bool DisplayAdapter::begin() {
  diagnostics_.map_bus_started = Wire.begin(kMapSdaPin, kMapSclPin, kI2cFrequency);
  diagnostics_.hud_bus_started = hud_wire_.begin(kHudSdaPin, kHudSclPin, kI2cFrequency);
  Wire.setTimeOut(50U);
  hud_wire_.setTimeOut(50U);
  diagnostics_.map_device_count = scan(Wire, diagnostics_.map_address);
  diagnostics_.hud_device_count = scan(hud_wire_, diagnostics_.hud_address);
  diagnostics_.map_initialized =
      diagnostics_.map_bus_started && diagnostics_.map_device_count == 1U &&
      diagnostics_.map_address == kDisplayAddress && initializePanel(Wire);
  diagnostics_.hud_initialized =
      diagnostics_.hud_bus_started && diagnostics_.hud_device_count == 1U &&
      diagnostics_.hud_address == kDisplayAddress && initializePanel(hud_wire_);
  return diagnostics_.map_initialized && diagnostics_.hud_initialized;
}

void DisplayAdapter::queueMap(const render::Framebuffer& framebuffer) {
  if (!diagnostics_.map_initialized) return;
  pending_map_ = framebuffer;
  map_offset_ = 0U;
  map_window_sent_ = false;
  map_dirty_ = true;
}

void DisplayAdapter::queueHud(const render::Framebuffer& framebuffer) {
  if (!diagnostics_.hud_initialized) return;
  pending_hud_ = framebuffer;
  hud_offset_ = 0U;
  hud_window_sent_ = false;
  hud_dirty_ = true;
}

bool DisplayAdapter::service() {
  if (!map_dirty_ && !hud_dirty_) return true;
  const bool use_map = map_dirty_ && (!hud_dirty_ || service_map_next_);
  service_map_next_ = !use_map;
  if (use_map) {
    if (!writeChunk(Wire, pending_map_, map_offset_, map_window_sent_)) {
      diagnostics_.map_initialized = false;
      map_dirty_ = false;
      return false;
    }
    if (map_offset_ >= pending_map_.bytes().size()) map_dirty_ = false;
    return true;
  }
  if (!writeChunk(hud_wire_, pending_hud_, hud_offset_, hud_window_sent_)) {
    diagnostics_.hud_initialized = false;
    hud_dirty_ = false;
    return false;
  }
  if (hud_offset_ >= pending_hud_.bytes().size()) hud_dirty_ = false;
  return true;
}

}  // namespace catamaze::esp32
