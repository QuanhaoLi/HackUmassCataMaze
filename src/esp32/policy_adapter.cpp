// Created at: 2026-11-15 00:24 EST
// Created by: Codex
// Last Modified at: 2026-11-14 19:00 EST
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
#include "policy_release.hpp"

extern const std::uint8_t catamaze_policy_start[] asm(
    "_binary_src_esp32_model_catamaze_policy_espdl_start");

namespace catamaze::esp32 {
namespace {

constexpr int kInternalArenaBytes = 128 * 1024;

template <std::size_t Size>
bool shapeEquals(dl::TensorBase* tensor, const std::array<std::size_t, Size>& expected) {
  if (tensor == nullptr || tensor->get_shape().size() != expected.size()) return false;
  for (std::size_t index = 0U; index < expected.size(); ++index) {
    if (tensor->get_shape()[index] != static_cast<int>(expected[index])) return false;
  }
  return true;
}

bool supportedType(dl::TensorBase* tensor) {
  if (tensor == nullptr) return false;
  return tensor->get_dtype() == dl::DATA_TYPE_INT8 || tensor->get_dtype() == dl::DATA_TYPE_INT16 ||
         tensor->get_dtype() == dl::DATA_TYPE_FLOAT;
}

float tensorScale(dl::TensorBase* tensor) { return std::ldexp(1.0F, tensor->exponent.get()); }

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
  return shapeEquals(spatial_, policy_release::kSpatialShape) &&
         shapeEquals(scalar_, policy_release::kScalarShape) &&
         shapeEquals(hidden_, policy_release::kHiddenShape) &&
         shapeEquals(logits_, policy_release::kLogitsShape) &&
         shapeEquals(value_, policy_release::kValueShape) &&
         shapeEquals(next_hidden_, policy_release::kNextHiddenShape) && supportedType(spatial_) &&
         supportedType(scalar_) && supportedType(hidden_) && supportedType(logits_) &&
         supportedType(value_) && supportedType(next_hidden_);
}

bool PolicyAdapter::begin() noexcept {
  const std::size_t internal_before = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
  const std::size_t psram_before = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
  model_ = new (std::nothrow) dl::Model(reinterpret_cast<const char*>(catamaze_policy_start),
                                        fbs::MODEL_LOCATION_IN_FLASH_RODATA, kInternalArenaBytes,
                                        dl::MEMORY_MANAGER_GREEDY, nullptr, true);
  if (model_ == nullptr) return failInference(app::PolicyFailure::ModelUnavailable);
  if (!resolveContract()) return failInference(app::PolicyFailure::TensorContract);
  health_.internal_used_bytes =
      static_cast<std::uint32_t>(internal_before - heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
  health_.psram_used_bytes =
      static_cast<std::uint32_t>(psram_before - heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
  // ESP-DL 3.3.11 differs from the 3.3.15 exporter by two INT16 units in one
  // hidden element, so the release gate below validates decoded FP32 envelopes.
  health_.exact_vector_test_passed = false;
  model_->reset();
  const std::int64_t benchmark_started = esp_timer_get_time();
  for (std::size_t agent = 0; agent < core::kAiCount; ++agent) {
    writeSpatial(spatial_, kPolicyReferenceSpatial);
    writeFloat(scalar_, kPolicyReferenceScalar.data(), kPolicyReferenceScalar.size());
    hidden_->memset(0);
    model_->run(dl::RUNTIME_MODE_SINGLE_CORE);
  }
  health_.boot_three_inference_us =
      static_cast<std::uint32_t>(esp_timer_get_time() - benchmark_started);
  health_.vector_test_passed = validateReleaseEnvelope();
  if (!health_.vector_test_passed) {
    return failInference(app::PolicyFailure::ReferenceEnvelope);
  }
  if (health_.boot_three_inference_us > policy_release::kMaximumThreeAgentUs) {
    return failInference(app::PolicyFailure::LatencyBudget);
  }
  health_.mode = app::PolicyMode::ModelActive;
  health_.failure = app::PolicyFailure::None;
  model_->reset();
  resetSession();
  return true;
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
  health_.boot_max_logit_error = maximum_logit_error;
  health_.boot_value_error = std::abs(actual_value - kPolicyReferenceValue);
  health_.boot_max_hidden_error = maximum_hidden_error;
  return health_.boot_max_logit_error <= policy_release::kMaximumLogitError &&
         health_.boot_value_error <= policy_release::kMaximumValueError &&
         health_.boot_max_hidden_error <= policy_release::kMaximumHiddenError;
}

void PolicyAdapter::resetSession() noexcept {
  hidden_states_ = {};
  health_.last_tick_inference_us = 0U;
  if (model_ != nullptr) model_->reset();
}

bool PolicyAdapter::failInference(app::PolicyFailure failure, std::uint32_t tick_us) noexcept {
  health_.mode = app::PolicyMode::FallbackLatched;
  health_.failure = failure;
  if (tick_us > 0U) {
    health_.last_tick_inference_us = tick_us;
    health_.max_tick_inference_us = std::max(health_.max_tick_inference_us, tick_us);
  }
  ++health_.inference_failures;
  return false;
}

bool PolicyAdapter::selectTick(const app::PolicyTickInput& input,
                               std::array<core::Action, core::kAiCount>& actions) noexcept {
  if (health_.mode != app::PolicyMode::ModelActive) return false;
  actions.fill(core::Action::Wait);
  std::array<HiddenState, core::kAiCount> proposed_hidden = hidden_states_;
  std::uint32_t complete_tick_us = 0U;

  for (std::size_t ai = 0U; ai < input.active.size(); ++ai) {
    if (!input.active[ai]) continue;
    const core::EncodedObservation& observation = input.observations[ai];
    writeSpatial(spatial_, observation.spatial);
    writeFloat(scalar_, observation.scalar.data(), observation.scalar.size());
    writeFloat(hidden_, hidden_states_[ai].data(), hidden_states_[ai].size());

    const std::int64_t started = esp_timer_get_time();
    model_->run(dl::RUNTIME_MODE_SINGLE_CORE);
    complete_tick_us += static_cast<std::uint32_t>(esp_timer_get_time() - started);
    ++health_.inference_calls;

    if (!std::isfinite(readFloat(value_, 0U))) {
      return failInference(app::PolicyFailure::NonFiniteOutput, complete_tick_us);
    }
    std::array<float, core::kPolicyActionCount> decoded_logits{};
    for (std::size_t index = 0; index < decoded_logits.size(); ++index) {
      decoded_logits[index] = readFloat(logits_, index);
      if (!std::isfinite(decoded_logits[index])) {
        return failInference(app::PolicyFailure::NonFiniteOutput, complete_tick_us);
      }
    }
    HiddenState next{};
    for (std::size_t index = 0; index < next.size(); ++index) {
      next[index] = readFloat(next_hidden_, index);
      if (!std::isfinite(next[index])) {
        return failInference(app::PolicyFailure::NonFiniteOutput, complete_tick_us);
      }
    }

    std::size_t best = static_cast<std::size_t>(core::Action::Wait);
    if (!observation.action_mask[best]) {
      return failInference(app::PolicyFailure::IllegalAction, complete_tick_us);
    }
    float best_logit = decoded_logits[best];
    for (std::size_t index = 0; index < decoded_logits.size(); ++index) {
      if (observation.action_mask[index] && decoded_logits[index] > best_logit) {
        best = index;
        best_logit = decoded_logits[index];
      }
    }
    proposed_hidden[ai] = next;
    actions[ai] = static_cast<core::Action>(best);
  }
  health_.last_tick_inference_us = complete_tick_us;
  health_.max_tick_inference_us = std::max(health_.max_tick_inference_us, complete_tick_us);
  if (complete_tick_us > policy_release::kMaximumThreeAgentUs) {
    return failInference(app::PolicyFailure::LatencyBudget, complete_tick_us);
  }
  hidden_states_ = proposed_hidden;
  return true;
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
  mix(static_cast<std::uint8_t>(health_.mode));
  mix(static_cast<std::uint8_t>(health_.failure));
  return hash;
}

}  // namespace catamaze::esp32
