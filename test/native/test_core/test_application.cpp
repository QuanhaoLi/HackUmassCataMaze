// Created at: 2026-11-14 02:26 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:32 EST
// Last Modified by: Codex
// Verifies deterministic heuristic policies and one-owner application coordination.

#include <array>
#include <cstddef>

#include <gtest/gtest.h>

#include "catamaze/app/application.hpp"

namespace catamaze::app {
namespace {

TEST(Application, SameSeedAndPlayerCommandsRemainDeterministic) {
  Application first(0x1234abcdU);
  Application second(0x1234abcdU);
  constexpr std::array<core::Action, 6> commands{
      core::Action::MoveUp,   core::Action::MoveRight, core::Action::Wait,
      core::Action::ShootDown, core::Action::MoveLeft, core::Action::ShootUp};

  for (std::size_t tick = 0; tick < 256U; ++tick) {
    if (first.state().status != core::GameStatus::Running) {
      break;
    }
    ASSERT_TRUE(first.enqueuePlayerAction(commands[tick % commands.size()]));
    ASSERT_TRUE(second.enqueuePlayerAction(commands[tick % commands.size()]));
    first.tick();
    second.tick();
    ASSERT_EQ(first.stateHash(), second.stateHash()) << tick;
  }
  EXPECT_EQ(first.state().status, second.state().status);
  EXPECT_EQ(first.state().tick, second.state().tick);
}

TEST(Application, HeuristicPoliciesActWithoutUnavailableFallbacks) {
  Application application(0x55aa55aaU);
  bool saw_non_wait_action = false;
  for (std::size_t tick = 0; tick < 200U; ++tick) {
    if (application.state().status != core::GameStatus::Running) {
      break;
    }
    application.tick();
    for (std::size_t ai = 1U; ai < core::kEntityCount; ++ai) {
      const auto& entity = application.state().entities[ai];
      if (!entity.alive) {
        continue;
      }
      EXPECT_NE(entity.last_result, core::ActionResult::InvalidFallback)
          << tick << ':' << ai;
      saw_non_wait_action =
          saw_non_wait_action || entity.last_action != core::Action::Wait;
    }
  }
  EXPECT_TRUE(saw_non_wait_action);
  EXPECT_GT(application.state().tick, 0U);
}

}  // namespace
}  // namespace catamaze::app
