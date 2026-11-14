// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Verifies the allocation-free FIFO, capacity rejection, CLEAR, and empty WAIT behavior.

#include <gtest/gtest.h>

#include <array>
#include <cstddef>

#include "catamaze/core/action_queue.hpp"

namespace catamaze::core {
namespace {

TEST(ActionQueue, PreservesFifoOrderAcrossRingWrap) {
  ActionQueue queue;
  constexpr std::array<Action, 4> pattern{Action::MoveUp, Action::MoveRight, Action::ShootDown,
                                          Action::Wait};

  for (std::size_t index = 0; index < kPlayerQueueCapacity; ++index) {
    ASSERT_TRUE(queue.push(pattern[index % pattern.size()]));
  }
  EXPECT_FALSE(queue.push(Action::MoveLeft));
  for (std::size_t index = 0; index < 12U; ++index) {
    EXPECT_EQ(queue.popOrWait(), pattern[index % pattern.size()]);
  }
  for (std::size_t index = 0; index < 12U; ++index) {
    ASSERT_TRUE(queue.push(Action::ShootLeft));
  }
  for (std::size_t index = 12U; index < kPlayerQueueCapacity; ++index) {
    EXPECT_EQ(queue.popOrWait(), pattern[index % pattern.size()]);
  }
  for (std::size_t index = 0; index < 12U; ++index) {
    EXPECT_EQ(queue.popOrWait(), Action::ShootLeft);
  }
  EXPECT_TRUE(queue.empty());
}

TEST(ActionQueue, ClearDropsPendingActionsAndEmptyQueueWaits) {
  ActionQueue queue;
  ASSERT_TRUE(queue.push(Action::MoveUp));
  ASSERT_TRUE(queue.push(Action::ShootRight));
  queue.clear();
  EXPECT_EQ(queue.size(), 0U);
  EXPECT_EQ(queue.capacity(), kPlayerQueueCapacity);
  EXPECT_EQ(queue.at(0U), Action::Wait);
  EXPECT_EQ(queue.popOrWait(), Action::Wait);
}

}  // namespace
}  // namespace catamaze::core
