// Created at: 2026-11-14 04:50 EST
// Created by: Codex
// Last Modified at: 2026-11-14 11:43 EST
// Last Modified by: Codex
// Composes deterministic gameplay with verified buttons, two OLED buses, and optional Serial audio.

#include <Arduino.h>

#include <cstdint>
#include <string_view>

#include "button_adapter.hpp"
#include "catamaze/app/audio_event.hpp"
#include "catamaze/app/product_shell.hpp"
#include "catamaze/render/product_renderer.hpp"
#include "display_adapter.hpp"
#include "hardware_config.hpp"
#include "policy_adapter.hpp"
#include "serial_audio_adapter.hpp"

SET_LOOP_TASK_STACK_SIZE(48U * 1024U);

namespace {

catamaze::app::ProductShell* product_controller = nullptr;
catamaze::esp32::ButtonAdapter buttons;
catamaze::esp32::DisplayAdapter displays;
catamaze::esp32::SerialAudioAdapter audio;
catamaze::esp32::PolicyAdapter policy;
bool hardware_ready = false;
bool boot_diagnostics_pending = true;
std::uint32_t next_tick_ms = 0U;

catamaze::app::ProductShell& product() { return *product_controller; }

void renderBoth() {
  const auto frames = catamaze::render::ProductRenderer::screens(
      product().snapshot(), product().playerObservation(), product().application().state());
  displays.queueMap(frames.left);
  displays.queueHud(frames.right);
}

void printBootDiagnostics() {
  const auto& display = displays.diagnostics();
  const auto& product_snapshot = product().snapshot();
  const auto& snapshot = product_snapshot.system;
  const auto& policy_status = policy.diagnostics();
  const std::string_view mode = catamaze::app::productModeName(product_snapshot.mode);
  const std::string_view system_mode = catamaze::app::systemModeName(snapshot.mode);
  const std::string_view companion_frame =
      catamaze::app::companionFrameName(product_snapshot.companion_frame);
  Serial0.printf(
      "CATAMAZE_BOOT {\"schema\":\"catamaze.boot.v4\","
      "\"flash_bytes\":%lu,\"psram_found\":%s,\"psram_bytes\":%lu,"
      "\"map_i2c_count\":%u,\"map_i2c_address\":%u,"
      "\"hud_i2c_count\":%u,\"hud_i2c_address\":%u,"
      "\"button_count\":%u,\"gpio10_configured\":false,"
      "\"mode\":\"%.*s\",\"system_mode\":\"%.*s\","
      "\"companion_frame\":\"%.*s\",\"confirmed_map_size\":%u,"
      "\"tick_budget\":%u,"
      "\"policy\":\"ESP-DL-W8A16\",\"policy_runtime\":\"3.3.11\","
      "\"policy_artifact_bytes\":%u,\"policy_artifact_sha256\":\"%s\","
      "\"policy_masked_agreement\":0.9861,\"policy_ready\":%s,"
      "\"policy_vector_test\":%s,\"policy_exact_vector_test\":%s,"
      "\"policy_boot_max_logit_error\":%.6f,\"policy_boot_value_error\":%.6f,"
      "\"policy_boot_max_hidden_error\":%.6f,"
      "\"policy_boot_three_inference_us\":%u,"
      "\"policy_internal_bytes\":%u,"
      "\"policy_psram_bytes\":%u,\"policy_fallback_latched\":%s,"
      "\"loop_stack_high_water_words\":%u,"
      "\"gpio4_configured\":false,\"ready\":%s}\n",
      static_cast<unsigned long>(ESP.getFlashChipSize()), psramFound() ? "true" : "false",
      static_cast<unsigned long>(ESP.getPsramSize()),
      static_cast<unsigned>(display.map_device_count), static_cast<unsigned>(display.map_address),
      static_cast<unsigned>(display.hud_device_count), static_cast<unsigned>(display.hud_address),
      static_cast<unsigned>(catamaze::esp32::kButtonPins.size()), static_cast<int>(mode.size()),
      mode.data(), static_cast<int>(system_mode.size()), system_mode.data(),
      static_cast<int>(companion_frame.size()), companion_frame.data(),
      static_cast<unsigned>(snapshot.confirmed_map_size),
      static_cast<unsigned>(snapshot.tick_budget),
      static_cast<unsigned>(catamaze::esp32::kPolicyArtifactBytes),
      catamaze::esp32::kPolicyArtifactSha256, policy_status.ready ? "true" : "false",
      policy_status.vector_test_passed ? "true" : "false",
      policy_status.exact_vector_test_passed ? "true" : "false",
      static_cast<double>(policy_status.boot_max_logit_error),
      static_cast<double>(policy_status.boot_value_error),
      static_cast<double>(policy_status.boot_max_hidden_error),
      static_cast<unsigned>(policy_status.boot_three_inference_us),
      static_cast<unsigned>(policy_status.internal_used_bytes),
      static_cast<unsigned>(policy_status.psram_used_bytes),
      policy_status.fallback_latched ? "true" : "false",
      static_cast<unsigned>(uxTaskGetStackHighWaterMark(nullptr)),
      hardware_ready ? "true" : "false");
}

}  // namespace

void setup() {
  Serial0.begin(catamaze::esp32::kSerialBaud);
  static catamaze::app::ProductShell product_instance(catamaze::esp32::kDefaultSeed);
  product_controller = &product_instance;
  const std::uint32_t started_ms = millis();
  product().begin(started_ms);
  buttons.begin(started_ms);
  const bool memory_ok = ESP.getFlashChipSize() == 16U * 1024U * 1024U && psramFound() &&
                         ESP.getPsramSize() == 8U * 1024U * 1024U;
  hardware_ready = memory_ok && displays.begin();
  policy.begin();
  product().application().setAiActionProvider(&policy);
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

  if (buttons.poll(now, product())) renderBoth();
  if (product().update(now)) renderBoth();

  if (static_cast<std::int32_t>(now - next_tick_ms) >= 0) {
    const std::uint16_t previous_tick = product().application().state().tick;
    product().tick();
    const auto& state = product().application().state();
    if (state.tick != previous_tick) {
      audio.emit(catamaze::app::selectAudioEvent(state), state.tick);
      renderBoth();
    }
    next_tick_ms += catamaze::esp32::kTickIntervalMs;
    if (static_cast<std::int32_t>(now - next_tick_ms) >= 0) {
      next_tick_ms = now + catamaze::esp32::kTickIntervalMs;
    }
  }
  yield();
}
