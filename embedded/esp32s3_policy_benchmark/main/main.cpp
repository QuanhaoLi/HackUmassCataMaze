// Created at: 2026-11-14 23:59 EST
// Created by: Codex
// Last Modified at: 2026-11-14 23:59 EST
// Last Modified by: Codex
// Validates the accepted recurrent policy and measures physical ESP32-S3 latency.

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

#include "dl_model_base.hpp"
#include "dl_tensor_base.hpp"
#include "esp_heap_caps.h"
#include "esp_psram.h"
#include "esp_timer.h"

extern const std::uint8_t catamaze_model_start[]
    asm("_binary_catamaze_policy_espdl_start");

namespace {

constexpr std::size_t kSpatialElements = 13U * 5U * 5U;
constexpr std::size_t kScalarElements = 46U;
constexpr std::size_t kHiddenElements = 256U;
constexpr std::size_t kActionCount = 9U;
constexpr std::size_t kAgentCount = 3U;
constexpr std::size_t kSamples = 31U;
constexpr std::size_t kWarmupRounds = 2U;
constexpr int kInternalArenaBytes = 128 * 1024;

using HiddenState = std::array<float, kHiddenElements>;

bool shapeEquals(dl::TensorBase *tensor, const std::vector<int> &expected) {
  return tensor != nullptr && tensor->get_shape() == expected;
}

bool supportedQuantizedType(dl::TensorBase *tensor) {
  if (tensor == nullptr) return false;
  return tensor->get_dtype() == dl::DATA_TYPE_INT8 ||
         tensor->get_dtype() == dl::DATA_TYPE_INT16 ||
         tensor->get_dtype() == dl::DATA_TYPE_FLOAT;
}

float scaleFor(dl::TensorBase *tensor) {
  return std::ldexp(1.0F, tensor->exponent.get());
}

void assignFloat(dl::TensorBase *tensor, const float *values, std::size_t count) {
  const float scale = scaleFor(tensor);
  if (tensor->get_dtype() == dl::DATA_TYPE_INT16) {
    auto *destination = tensor->get_element_ptr<std::int16_t>();
    for (std::size_t index = 0; index < count; ++index) {
      destination[index] = dl::quantize<std::int16_t>(values[index], 1.0F / scale);
    }
  } else if (tensor->get_dtype() == dl::DATA_TYPE_INT8) {
    auto *destination = tensor->get_element_ptr<std::int8_t>();
    for (std::size_t index = 0; index < count; ++index) {
      destination[index] = dl::quantize<std::int8_t>(values[index], 1.0F / scale);
    }
  } else {
    std::memcpy(tensor->get_element_ptr<float>(), values, count * sizeof(float));
  }
}

float readFloat(dl::TensorBase *tensor, std::size_t index) {
  const float scale = scaleFor(tensor);
  if (tensor->get_dtype() == dl::DATA_TYPE_INT16) {
    return dl::dequantize<std::int16_t>(
        tensor->get_element_ptr<std::int16_t>()[index], scale);
  }
  if (tensor->get_dtype() == dl::DATA_TYPE_INT8) {
    return dl::dequantize<std::int8_t>(
        tensor->get_element_ptr<std::int8_t>()[index], scale);
  }
  return tensor->get_element_ptr<float>()[index];
}

bool copyHidden(dl::TensorBase *source, HiddenState &destination) {
  for (std::size_t index = 0; index < destination.size(); ++index) {
    destination[index] = readFloat(source, index);
    if (!std::isfinite(destination[index])) return false;
  }
  return true;
}

std::size_t bestAction(dl::TensorBase *logits) {
  std::size_t best = 0U;
  float best_value = readFloat(logits, 0U);
  for (std::size_t action = 1U; action < kActionCount; ++action) {
    const float value = readFloat(logits, action);
    if (value > best_value) {
      best = action;
      best_value = value;
    }
  }
  return best;
}

std::int64_t percentile95(std::array<std::int64_t, kSamples> samples) {
  std::sort(samples.begin(), samples.end());
  constexpr std::size_t index = ((kSamples * 95U) + 99U) / 100U - 1U;
  return samples[index];
}

struct Contract {
  dl::TensorBase *spatial;
  dl::TensorBase *scalar;
  dl::TensorBase *hidden;
  dl::TensorBase *logits;
  dl::TensorBase *value;
  dl::TensorBase *next_hidden;
};

bool resolveContract(dl::Model &model, Contract &contract) {
  contract = Contract{
      model.get_input("spatial"), model.get_input("scalar"), model.get_input("hidden"),
      model.get_output("logits"), model.get_output("value"),
      model.get_output("next_hidden")};
  return shapeEquals(contract.spatial, {1, 13, 5, 5}) &&
         shapeEquals(contract.scalar, {1, 46}) &&
         shapeEquals(contract.hidden, {1, 1, 256}) &&
         shapeEquals(contract.logits, {1, 9}) && shapeEquals(contract.value, {1}) &&
         shapeEquals(contract.next_hidden, {1, 1, 256}) &&
         supportedQuantizedType(contract.spatial) && supportedQuantizedType(contract.scalar) &&
         supportedQuantizedType(contract.hidden) && supportedQuantizedType(contract.logits) &&
         supportedQuantizedType(contract.value) && supportedQuantizedType(contract.next_hidden);
}

bool runRound(dl::Model &model, Contract &contract,
              std::array<HiddenState, kAgentCount> &hidden_states,
              dl::runtime_mode_t mode, std::array<std::size_t, kAgentCount> &actions) {
  contract.spatial->memset(0);
  contract.scalar->memset(0);
  for (std::size_t agent = 0; agent < kAgentCount; ++agent) {
    assignFloat(contract.hidden, hidden_states[agent].data(), kHiddenElements);
    model.run(mode);
    if (!copyHidden(contract.next_hidden, hidden_states[agent])) return false;
    actions[agent] = bestAction(contract.logits);
  }
  return true;
}

bool benchmarkMode(dl::Model &model, Contract &contract, dl::runtime_mode_t mode,
                   std::int64_t &p95_us, std::int64_t &maximum_us,
                   std::array<std::size_t, kAgentCount> &actions) {
  std::array<HiddenState, kAgentCount> hidden_states{};
  for (std::size_t warmup = 0; warmup < kWarmupRounds; ++warmup) {
    if (!runRound(model, contract, hidden_states, mode, actions)) return false;
  }
  std::array<std::int64_t, kSamples> samples{};
  for (std::size_t sample = 0; sample < samples.size(); ++sample) {
    const std::int64_t started = esp_timer_get_time();
    if (!runRound(model, contract, hidden_states, mode, actions)) return false;
    samples[sample] = esp_timer_get_time() - started;
  }
  p95_us = percentile95(samples);
  maximum_us = *std::max_element(samples.begin(), samples.end());
  return true;
}

}  // namespace

extern "C" void app_main() {
  const std::size_t internal_before = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
  const std::size_t psram_before = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
  std::printf("CATAMAZE_POLICY_START internal_free=%u psram_free=%u psram_bytes=%u\n",
              static_cast<unsigned>(internal_before), static_cast<unsigned>(psram_before),
              static_cast<unsigned>(esp_psram_get_size()));

  dl::Model model(reinterpret_cast<const char *>(catamaze_model_start),
                  fbs::MODEL_LOCATION_IN_FLASH_RODATA, kInternalArenaBytes,
                  dl::MEMORY_MANAGER_GREEDY, nullptr, true);
  if (!model.is_built()) {
    std::puts("CATAMAZE_POLICY_RESULT {\"schema\":\"catamaze.policy.bench.v1\",\"passed\":false,\"reason\":\"model_build\"}");
    return;
  }

  Contract contract{};
  if (!resolveContract(model, contract)) {
    std::puts("CATAMAZE_POLICY_RESULT {\"schema\":\"catamaze.policy.bench.v1\",\"passed\":false,\"reason\":\"tensor_contract\"}");
    return;
  }

  const bool vector_test_passed = model.test() == ESP_OK;
  std::int64_t single_p95_us = 0;
  std::int64_t single_max_us = 0;
  std::int64_t multi_p95_us = 0;
  std::int64_t multi_max_us = 0;
  std::array<std::size_t, kAgentCount> single_actions{};
  std::array<std::size_t, kAgentCount> multi_actions{};
  const bool single_ok = benchmarkMode(model, contract, dl::RUNTIME_MODE_SINGLE_CORE,
                                       single_p95_us, single_max_us, single_actions);
  const bool multi_ok = benchmarkMode(model, contract, dl::RUNTIME_MODE_MULTI_CORE,
                                      multi_p95_us, multi_max_us, multi_actions);
  const std::size_t internal_after = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
  const std::size_t psram_after = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
  const bool latency_passed = single_ok && multi_ok &&
                              std::min(single_p95_us, multi_p95_us) < 900000;
  const bool passed = vector_test_passed && latency_passed;

  std::printf(
      "CATAMAZE_POLICY_RESULT {\"schema\":\"catamaze.policy.bench.v1\","
      "\"passed\":%s,\"vector_test\":%s,\"single_p95_us\":%lld,"
      "\"single_max_us\":%lld,\"multi_p95_us\":%lld,\"multi_max_us\":%lld,"
      "\"selected_mode\":\"%s\",\"three_agent_budget_us\":900000,"
      "\"internal_used_bytes\":%u,\"psram_used_bytes\":%u,"
      "\"single_actions\":[%u,%u,%u],\"multi_actions\":[%u,%u,%u]}\n",
      passed ? "true" : "false", vector_test_passed ? "true" : "false",
      static_cast<long long>(single_p95_us), static_cast<long long>(single_max_us),
      static_cast<long long>(multi_p95_us), static_cast<long long>(multi_max_us),
      single_p95_us <= multi_p95_us ? "single" : "multi",
      static_cast<unsigned>(internal_before - internal_after),
      static_cast<unsigned>(psram_before - psram_after),
      static_cast<unsigned>(single_actions[0]), static_cast<unsigned>(single_actions[1]),
      static_cast<unsigned>(single_actions[2]), static_cast<unsigned>(multi_actions[0]),
      static_cast<unsigned>(multi_actions[1]), static_cast<unsigned>(multi_actions[2]));
}
