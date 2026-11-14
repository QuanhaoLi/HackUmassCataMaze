// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:56 EST
// Last Modified by: Codex
// Composes deterministic gameplay with verified buttons, two OLED buses, and optional Serial audio.

#include <Arduino.h>

#include <cstdint>

#include "button_adapter.hpp"
#include "catamaze/app/application.hpp"
#include "catamaze/app/audio_event.hpp"
#include "catamaze/render/renderer.hpp"
#include "display_adapter.hpp"
#include "hardware_config.hpp"
#include "serial_audio_adapter.hpp"

namespace {

catamaze::app::Application application(catamaze::esp32::kDefaultSeed);
catamaze::esp32::ButtonAdapter buttons;
catamaze::esp32::DisplayAdapter displays;
catamaze::esp32::SerialAudioAdapter audio;
bool hardware_ready = false;
bool boot_diagnostics_pending = true;
std::uint32_t next_tick_ms = 0U;

void renderBoth() {
  const auto map = catamaze::render::Renderer::mapScreen(application.playerObservation());
  const auto hud = catamaze::render::Renderer::hudScreen(application.state());
  displays.queueMap(map);
  displays.queueHud(hud);
}

void printBootDiagnostics() {
  const auto& display = displays.diagnostics();
  Serial.printf(
      "CATAMAZE_BOOT {\"schema\":\"catamaze.boot.v1\","
      "\"flash_bytes\":%lu,\"psram_found\":%s,\"psram_bytes\":%lu,"
      "\"map_i2c_count\":%u,\"map_i2c_address\":%u,"
      "\"hud_i2c_count\":%u,\"hud_i2c_address\":%u,"
      "\"gpio4_configured\":false,\"ready\":%s}\n",
      static_cast<unsigned long>(ESP.getFlashChipSize()), psramFound() ? "true" : "false",
      static_cast<unsigned long>(ESP.getPsramSize()),
      static_cast<unsigned>(display.map_device_count), static_cast<unsigned>(display.map_address),
      static_cast<unsigned>(display.hud_device_count), static_cast<unsigned>(display.hud_address),
      hardware_ready ? "true" : "false");
}

}  // namespace

void setup() {
  Serial.begin(catamaze::esp32::kSerialBaud);
  buttons.begin(millis());
  const bool memory_ok = ESP.getFlashChipSize() == 16U * 1024U * 1024U && psramFound() &&
                         ESP.getPsramSize() == 8U * 1024U * 1024U;
  hardware_ready = memory_ok && displays.begin();
  if (hardware_ready) renderBoth();
  next_tick_ms = millis() + catamaze::esp32::kTickIntervalMs;
}

void loop() {
  const std::uint32_t now = millis();
  if (boot_diagnostics_pending && Serial) {
    printBootDiagnostics();
    boot_diagnostics_pending = false;
  }
  if (!hardware_ready) {
    yield();
    return;
  }

  if (!displays.service()) {
    hardware_ready = false;
    yield();
    return;
  }

  if (buttons.poll(now, application)) {
    const auto hud = catamaze::render::Renderer::hudScreen(application.state());
    displays.queueHud(hud);
  }

  if (application.state().status == catamaze::core::GameStatus::Running &&
      static_cast<std::int32_t>(now - next_tick_ms) >= 0) {
    application.tick();
    audio.emit(catamaze::app::selectAudioEvent(application.state()), application.state().tick);
    renderBoth();
    next_tick_ms += catamaze::esp32::kTickIntervalMs;
    if (static_cast<std::int32_t>(now - next_tick_ms) >= 0) {
      next_tick_ms = now + catamaze::esp32::kTickIntervalMs;
    }
  }
  yield();
}
