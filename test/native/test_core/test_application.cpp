// Created at: 2026-11-14 02:26 EST
// Created by: Codex
// Last Modified at: 2026-11-14 19:00 EST
// Last Modified by: Codex
// Verifies deterministic heuristic policies and one-owner application coordination.

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <cstddef>

#include "catamaze/app/application.hpp"

namespace catamaze::app {
namespace {

class WaitPolicy final : public ResidentPolicyModule {
 public:
  void resetSession() noexcept override { ++reset_count; }
  bool selectTick(const PolicyTickInput& input,
                  std::array<core::Action, core::kAiCount>& actions) noexcept override {
    ++tick_count;
    for (std::size_t ai = 0U; ai < input.active.size(); ++ai) {
      if (!input.active[ai]) continue;
      EXPECT_TRUE(input.observations[ai].action_mask[static_cast<std::size_t>(core::Action::Wait)]);
      ++active_count;
      actions[ai] = core::Action::Wait;
    }
    return true;
  }
  const PolicyHealth& health() const noexcept override { return health_; }

  std::size_t reset_count{0U};
  std::size_t tick_count{0U};
  std::size_t active_count{0U};
  PolicyHealth health_{PolicyMode::ModelActive};
};

class FailingPolicy final : public ResidentPolicyModule {
 public:
  void resetSession() noexcept override {}
  bool selectTick(const PolicyTickInput&,
                  std::array<core::Action, core::kAiCount>& actions) noexcept override {
    actions.fill(core::Action::ShootUp);
    health_.mode = PolicyMode::FallbackLatched;
    health_.failure = PolicyFailure::NonFiniteOutput;
    return false;
  }
  const PolicyHealth& health() const noexcept override { return health_; }

 private:
  PolicyHealth health_{PolicyMode::ModelActive};
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

TEST(Application, InstalledResidentPolicyControlsOneAtomicTickAndResetsWithTheRun) {
  Application application(0x4321abcdU);
  WaitPolicy policy;
  application.installResidentPolicy(policy);
  ASSERT_EQ(policy.reset_count, 1U);

  const std::size_t living = static_cast<std::size_t>(
      std::count_if(application.state().entities.begin() + 1U, application.state().entities.end(),
                    [](const core::EntityState& entity) { return entity.alive; }));
  application.tick();
  EXPECT_EQ(policy.tick_count, 1U);
  EXPECT_EQ(policy.active_count, living);
  EXPECT_EQ(application.policyHealth().mode, PolicyMode::ModelActive);
  for (std::size_t ai = 1U; ai < core::kEntityCount; ++ai) {
    if (application.state().entities[ai].alive) {
      EXPECT_EQ(application.state().entities[ai].last_action, core::Action::Wait);
    }
  }

  application.reset(0x4321abcdU);
  EXPECT_EQ(policy.reset_count, 2U);
}

TEST(Application, FailedResidentPolicyFallsBackForTheEntireTick) {
  constexpr std::uint64_t kSeed = 0x9173U;
  Application expected(kSeed);
  Application actual(kSeed);
  FailingPolicy policy;
  actual.installResidentPolicy(policy);

  expected.tick();
  actual.tick();

  EXPECT_EQ(actual.policyHealth().mode, PolicyMode::FallbackLatched);
  EXPECT_EQ(actual.policyHealth().failure, PolicyFailure::NonFiniteOutput);
  EXPECT_EQ(actual.state().tick, expected.state().tick);
  EXPECT_EQ(actual.state().bullet_count, expected.state().bullet_count);
  for (std::size_t ai = 1U; ai < core::kEntityCount; ++ai) {
    EXPECT_EQ(actual.state().entities[ai].last_action, expected.state().entities[ai].last_action)
        << ai;
    EXPECT_EQ(actual.state().entities[ai].position, expected.state().entities[ai].position) << ai;
  }

  actual.reset(kSeed);
  EXPECT_EQ(actual.policyHealth().mode, PolicyMode::FallbackLatched);
  EXPECT_EQ(actual.policyHealth().failure, PolicyFailure::NonFiniteOutput);
}

}  // namespace
}  // namespace catamaze::app
