// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Implements the fixed-capacity, allocation-free player FIFO.

#pragma once

#include <array>
#include <cstddef>

#include "catamaze/core/types.hpp"

namespace catamaze::core {

class ActionQueue {
 public:
  bool push(Action action) noexcept {
    if (size_ == actions_.size()) {
      return false;
    }
    const std::size_t tail = (head_ + size_) % actions_.size();
    actions_[tail] = action;
    ++size_;
    return true;
  }

  Action popOrWait() noexcept {
    if (size_ == 0U) {
      return Action::Wait;
    }
    const Action action = actions_[head_];
    head_ = (head_ + 1U) % actions_.size();
    --size_;
    return action;
  }

  void clear() noexcept {
    head_ = 0U;
    size_ = 0U;
  }

  std::size_t size() const noexcept { return size_; }
  constexpr std::size_t capacity() const noexcept { return actions_.size(); }
  bool empty() const noexcept { return size_ == 0U; }

  Action at(std::size_t ordered_index) const noexcept {
    if (ordered_index >= size_) {
      return Action::Wait;
    }
    return actions_[(head_ + ordered_index) % actions_.size()];
  }

 private:
  std::array<Action, kPlayerQueueCapacity> actions_{};
  std::size_t head_{0};
  std::size_t size_{0};
};

}  // namespace catamaze::core
