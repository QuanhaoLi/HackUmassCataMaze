// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 06:34 EST
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

SET_LOOP_TASK_STACK_SIZE(48U * 1024U);

namespace {

catamaze::app::Application* application = nullptr;
catamaze::esp32::ButtonAdapter buttons;
catamaze::esp32::DisplayAdapter displays;
catamaze::esp32::SerialAudioAdapter audio;
bool hardware_ready = false;
bool boot_diagnostics_pending = true;
std::uint32_t next_tick_ms = 0U;

catamaze::app::Application& game() { return *application; }

void renderBoth() {
  const auto map = catamaze::render::Renderer::mapScreen(game().playerObservation());
  const auto hud = catamaze::render::Renderer::hudScreen(game().state());
  displays.queueMap(map);
  displays.queueHud(hud);
}

void printBootDiagnostics() {
  const auto& display = displays.diagnostics();
  Serial0.printf(
      "CATAMAZE_BOOT {\"schema\":\"catamaze.boot.v1\","
      "\"flash_bytes\":%lu,\"psram_found\":%s,\"psram_bytes\":%lu,"
      "\"map_i2c_count\":%u,\"map_i2c_address\":%u,"
      "\"hud_i2c_count\":%u,\"hud_i2c_address\":%u,"
      "\"loop_stack_high_water_words\":%u,"
      "\"gpio4_configured\":false,\"ready\":%s}\n",
      static_cast<unsigned long>(ESP.getFlashChipSize()), psramFound() ? "true" : "false",
      static_cast<unsigned long>(ESP.getPsramSize()),
      static_cast<unsigned>(display.map_device_count), static_cast<unsigned>(display.map_address),
      static_cast<unsigned>(display.hud_device_count), static_cast<unsigned>(display.hud_address),
      static_cast<unsigned>(uxTaskGetStackHighWaterMark(nullptr)),
      hardware_ready ? "true" : "false");
}

}  // namespace

void setup() {
  Serial0.begin(catamaze::esp32::kSerialBaud);
  static catamaze::app::Application application_instance(catamaze::esp32::kDefaultSeed);
  application = &application_instance;
  buttons.begin(millis());
  const bool memory_ok = ESP.getFlashChipSize() == 16U * 1024U * 1024U && psramFound() &&
                         ESP.getPsramSize() == 8U * 1024U * 1024U;
  hardware_ready = memory_ok && displays.begin();
  if (hardware_ready) renderBoth();
  next_tick_ms = millis() + catamaze::esp32::kTickIntervalMs;
}

void loop() {
  const std::uint32_t now = millis();
  if (boot_diagnostics_pending) {
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

  if (buttons.poll(now, game())) {
    const auto hud = catamaze::render::Renderer::hudScreen(game().state());
    displays.queueHud(hud);
  }

  if (game().state().status == catamaze::core::GameStatus::Running &&
      static_cast<std::int32_t>(now - next_tick_ms) >= 0) {
    game().tick();
    audio.emit(catamaze::app::selectAudioEvent(game().state()), game().state().tick);
    renderBoth();
    next_tick_ms += catamaze::esp32::kTickIntervalMs;
    if (static_cast<std::int32_t>(now - next_tick_ms) >= 0) {
      next_tick_ms = now + catamaze::esp32::kTickIntervalMs;
    }
  }
  yield();
}
