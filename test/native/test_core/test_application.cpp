// Created at: 2026-11-14 02:26 EST
// Created by: Codex
// Last Modified at: 2026-11-15 00:20 EST
// Last Modified by: Codex
// Verifies deterministic heuristic policies and one-owner application coordination.

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <cstddef>

#include "catamaze/app/application.hpp"

namespace catamaze::app {
namespace {

class WaitProvider final : public AiActionProvider {
 public:
  void reset() noexcept override { ++reset_count; }
  void beginTick() noexcept override { ++begin_count; }
  bool select(std::size_t, const core::EncodedObservation& observation,
              core::Action& action) noexcept override {
    EXPECT_TRUE(observation.action_mask[static_cast<std::size_t>(core::Action::Wait)]);
    ++select_count;
    action = core::Action::Wait;
    return true;
  }
  void endTick() noexcept override { ++end_count; }

  std::size_t reset_count{0U};
  std::size_t begin_count{0U};
  std::size_t select_count{0U};
  std::size_t end_count{0U};
};

TEST(Application, SameSeedAndPlayerCommandsRemainDeterministic) {
  Application first(0x1234abcdU);
  Application second(0x1234abcdU);
  constexpr std::array<core::Action, 6> commands{core::Action::MoveUp,   core::Action::MoveRight,
                                                 core::Action::Wait,     core::Action::ShootDown,
                                                 core::Action::MoveLeft, core::Action::ShootUp};

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
      EXPECT_NE(entity.last_result, core::ActionResult::InvalidFallback) << tick << ':' << ai;
      saw_non_wait_action = saw_non_wait_action || entity.last_action != core::Action::Wait;
    }
  }
  EXPECT_TRUE(saw_non_wait_action);
  EXPECT_GT(application.state().tick, 0U);
}

TEST(Application, InstalledProviderControlsEveryLivingAiAndResetsWithTheRun) {
  Application application(0x4321abcdU);
  WaitProvider provider;
  application.setAiActionProvider(&provider);
  ASSERT_EQ(provider.reset_count, 1U);

  const std::size_t living = static_cast<std::size_t>(std::count_if(
      application.state().entities.begin() + 1U, application.state().entities.end(),
      [](const core::EntityState& entity) { return entity.alive; }));
  application.tick();
  EXPECT_EQ(provider.begin_count, 1U);
  EXPECT_EQ(provider.end_count, 1U);
  EXPECT_EQ(provider.select_count, living);
  for (std::size_t ai = 1U; ai < core::kEntityCount; ++ai) {
    if (application.state().entities[ai].alive) {
      EXPECT_EQ(application.state().entities[ai].last_action, core::Action::Wait);
    }
  }

  application.reset(0x4321abcdU);
  EXPECT_EQ(provider.reset_count, 2U);
}

}  // namespace
}  // namespace catamaze::app
