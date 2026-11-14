// Created at: 2026-11-15 00:24 EST
// Created by: Codex
// Last Modified at: 2026-11-15 00:24 EST
// Last Modified by: Codex
// Runs one shared W8A16 recurrent model for three independently stateful AI agents.

#include "policy_adapter.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <new>
#include <vector>

#include "dl_model_base.hpp"
#include "dl_tensor_base.hpp"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "policy_reference.hpp"

extern const std::uint8_t catamaze_policy_start[]
    asm("_binary_src_esp32_model_catamaze_policy_espdl_start");

namespace catamaze::esp32 {
namespace {

constexpr int kInternalArenaBytes = 128 * 1024;

bool shapeEquals(dl::TensorBase* tensor, const std::vector<int>& expected) {
  return tensor != nullptr && tensor->get_shape() == expected;
}

bool supportedType(dl::TensorBase* tensor) {
  if (tensor == nullptr) return false;
  return tensor->get_dtype() == dl::DATA_TYPE_INT8 ||
         tensor->get_dtype() == dl::DATA_TYPE_INT16 ||
         tensor->get_dtype() == dl::DATA_TYPE_FLOAT;
}

float tensorScale(dl::TensorBase* tensor) {
  return std::ldexp(1.0F, tensor->exponent.get());
}

void writeFloat(dl::TensorBase* tensor, const float* values, std::size_t count) {
  const float scale = tensorScale(tensor);
  if (tensor->get_dtype() == dl::DATA_TYPE_INT16) {
    auto* destination = tensor->get_element_ptr<std::int16_t>();
    for (std::size_t index = 0; index < count; ++index) {
      destination[index] = dl::quantize<std::int16_t>(values[index], 1.0F / scale);
    }
  } else if (tensor->get_dtype() == dl::DATA_TYPE_INT8) {
    auto* destination = tensor->get_element_ptr<std::int8_t>();
    for (std::size_t index = 0; index < count; ++index) {
      destination[index] = dl::quantize<std::int8_t>(values[index], 1.0F / scale);
    }
  } else {
    std::memcpy(tensor->get_element_ptr<float>(), values, count * sizeof(float));
  }
}

void writeSpatial(dl::TensorBase* tensor,
                  const std::array<std::uint8_t, core::kPolicySpatialFeatures>& values) {
  const float scale = tensorScale(tensor);
  if (tensor->get_dtype() == dl::DATA_TYPE_INT16) {
    auto* destination = tensor->get_element_ptr<std::int16_t>();
    for (std::size_t index = 0; index < values.size(); ++index) {
      destination[index] =
          dl::quantize<std::int16_t>(static_cast<float>(values[index]), 1.0F / scale);
    }
  } else if (tensor->get_dtype() == dl::DATA_TYPE_INT8) {
    auto* destination = tensor->get_element_ptr<std::int8_t>();
    for (std::size_t index = 0; index < values.size(); ++index) {
      destination[index] =
          dl::quantize<std::int8_t>(static_cast<float>(values[index]), 1.0F / scale);
    }
  } else {
    auto* destination = tensor->get_element_ptr<float>();
    for (std::size_t index = 0; index < values.size(); ++index) {
      destination[index] = static_cast<float>(values[index]);
    }
  }
}

float readFloat(dl::TensorBase* tensor, std::size_t index) {
  const float scale = tensorScale(tensor);
  if (tensor->get_dtype() == dl::DATA_TYPE_INT16) {
    return dl::dequantize<std::int16_t>(tensor->get_element_ptr<std::int16_t>()[index], scale);
  }
  if (tensor->get_dtype() == dl::DATA_TYPE_INT8) {
    return dl::dequantize<std::int8_t>(tensor->get_element_ptr<std::int8_t>()[index], scale);
  }
  return tensor->get_element_ptr<float>()[index];
}

}  // namespace

PolicyAdapter::~PolicyAdapter() { delete model_; }

bool PolicyAdapter::resolveContract() noexcept {
  spatial_ = model_->get_input("spatial");
  scalar_ = model_->get_input("scalar");
  hidden_ = model_->get_input("hidden");
  logits_ = model_->get_output("logits");
  value_ = model_->get_output("value");
  next_hidden_ = model_->get_output("next_hidden");
  return shapeEquals(spatial_, {1, 13, 5, 5}) && shapeEquals(scalar_, {1, 46}) &&
         shapeEquals(hidden_, {1, 1, 256}) && shapeEquals(logits_, {1, 9}) &&
         shapeEquals(value_, {1}) && shapeEquals(next_hidden_, {1, 1, 256}) &&
         supportedType(spatial_) && supportedType(scalar_) && supportedType(hidden_) &&
         supportedType(logits_) && supportedType(value_) && supportedType(next_hidden_);
}

bool PolicyAdapter::begin() noexcept {
  const std::size_t internal_before = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
  const std::size_t psram_before = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
  model_ = new (std::nothrow) dl::Model(
      reinterpret_cast<const char*>(catamaze_policy_start),
      fbs::MODEL_LOCATION_IN_FLASH_RODATA, kInternalArenaBytes, dl::MEMORY_MANAGER_GREEDY,
      nullptr, true);
  if (model_ == nullptr || !resolveContract()) {
    diagnostics_.fallback_latched = true;
    return false;
  }
  diagnostics_.internal_used_bytes = static_cast<std::uint32_t>(
      internal_before - heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
  diagnostics_.psram_used_bytes =
      static_cast<std::uint32_t>(psram_before - heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
  // ESP-DL 3.3.11 differs from the 3.3.15 exporter by two INT16 units in one
  // hidden element, so the release gate below validates decoded FP32 envelopes.
  diagnostics_.exact_vector_test_passed = false;
  model_->reset();
  const std::int64_t benchmark_started = esp_timer_get_time();
  for (std::size_t agent = 0; agent < core::kAiCount; ++agent) {
    writeSpatial(spatial_, kPolicyReferenceSpatial);
    writeFloat(scalar_, kPolicyReferenceScalar.data(), kPolicyReferenceScalar.size());
    hidden_->memset(0);
    model_->run(dl::RUNTIME_MODE_SINGLE_CORE);
  }
  diagnostics_.boot_three_inference_us =
      static_cast<std::uint32_t>(esp_timer_get_time() - benchmark_started);
  diagnostics_.vector_test_passed =
      validateReleaseEnvelope() &&
      diagnostics_.boot_three_inference_us <= kPolicyThreeAgentBudgetUs;
  diagnostics_.ready = diagnostics_.vector_test_passed;
  diagnostics_.fallback_latched = !diagnostics_.ready;
  model_->reset();
  reset();
  return diagnostics_.ready;
}

bool PolicyAdapter::validateReleaseEnvelope() noexcept {
  float maximum_logit_error = 0.0F;
  for (std::size_t index = 0; index < kPolicyReferenceLogits.size(); ++index) {
    const float actual = readFloat(logits_, index);
    if (!std::isfinite(actual)) return false;
    maximum_logit_error =
        std::max(maximum_logit_error, std::abs(actual - kPolicyReferenceLogits[index]));
  }
  const float actual_value = readFloat(value_, 0U);
  if (!std::isfinite(actual_value)) return false;
  float maximum_hidden_error = 0.0F;
  for (std::size_t index = 0; index < kPolicyReferenceHidden.size(); ++index) {
    const float actual = readFloat(next_hidden_, index);
    if (!std::isfinite(actual)) return false;
    maximum_hidden_error =
        std::max(maximum_hidden_error, std::abs(actual - kPolicyReferenceHidden[index]));
  }
  diagnostics_.boot_max_logit_error = maximum_logit_error;
  diagnostics_.boot_value_error = std::abs(actual_value - kPolicyReferenceValue);
  diagnostics_.boot_max_hidden_error = maximum_hidden_error;
  return diagnostics_.boot_max_logit_error <= kPolicyReleaseMaxLogitError &&
         diagnostics_.boot_value_error <= kPolicyReleaseMaxValueError &&
         diagnostics_.boot_max_hidden_error <= kPolicyReleaseMaxHiddenError;
}

void PolicyAdapter::reset() noexcept {
  hidden_states_ = {};
  current_tick_inference_us_ = 0U;
  if (model_ != nullptr) model_->reset();
}

void PolicyAdapter::beginTick() noexcept { current_tick_inference_us_ = 0U; }

bool PolicyAdapter::failInference() noexcept {
  diagnostics_.ready = false;
  diagnostics_.fallback_latched = true;
  ++diagnostics_.inference_failures;
  return false;
}

bool PolicyAdapter::select(std::size_t ai_index,
                           const core::EncodedObservation& observation,
                           core::Action& action) noexcept {
  if (!diagnostics_.ready || ai_index >= hidden_states_.size()) return false;
  writeSpatial(spatial_, observation.spatial);
  writeFloat(scalar_, observation.scalar.data(), observation.scalar.size());
  writeFloat(hidden_, hidden_states_[ai_index].data(), hidden_states_[ai_index].size());

  const std::int64_t started = esp_timer_get_time();
  model_->run(dl::RUNTIME_MODE_SINGLE_CORE);
  const std::uint32_t elapsed = static_cast<std::uint32_t>(esp_timer_get_time() - started);
  current_tick_inference_us_ += elapsed;
  diagnostics_.max_inference_us = std::max(diagnostics_.max_inference_us, elapsed);
  ++diagnostics_.inference_calls;

  if (!std::isfinite(readFloat(value_, 0U))) return failInference();
  std::array<float, core::kPolicyActionCount> decoded_logits{};
  for (std::size_t index = 0; index < decoded_logits.size(); ++index) {
    decoded_logits[index] = readFloat(logits_, index);
    if (!std::isfinite(decoded_logits[index])) return failInference();
  }
  HiddenState next{};
  for (std::size_t index = 0; index < next.size(); ++index) {
    next[index] = readFloat(next_hidden_, index);
    if (!std::isfinite(next[index])) return failInference();
  }

  std::size_t best = static_cast<std::size_t>(core::Action::Wait);
  float best_logit = decoded_logits[best];
  for (std::size_t index = 0; index < decoded_logits.size(); ++index) {
    if (observation.action_mask[index] && decoded_logits[index] > best_logit) {
      best = index;
      best_logit = decoded_logits[index];
    }
  }
  if (!observation.action_mask[best]) return failInference();
  hidden_states_[ai_index] = next;
  action = static_cast<core::Action>(best);
  return true;
}

void PolicyAdapter::endTick() noexcept {
  diagnostics_.last_tick_inference_us = current_tick_inference_us_;
  if (current_tick_inference_us_ > kPolicyThreeAgentBudgetUs) failInference();
}

std::uint64_t PolicyAdapter::stateHash() const noexcept {
  std::uint64_t hash = 1469598103934665603ULL;
  const auto mix = [&hash](std::uint32_t value) {
    hash ^= value;
    hash *= 1099511628211ULL;
  };
  for (const HiddenState& hidden_state : hidden_states_) {
    for (float value : hidden_state) {
      std::uint32_t bits = 0U;
      std::memcpy(&bits, &value, sizeof(bits));
      mix(bits);
    }
  }
  mix(diagnostics_.ready ? 1U : 0U);
  mix(diagnostics_.fallback_latched ? 1U : 0U);
  return hash;
}

}  // namespace catamaze::esp32
