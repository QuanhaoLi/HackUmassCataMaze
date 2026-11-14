// Created at: 2026-11-14 02:55 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Exhaustively verifies stable direction, action, movement, and status helper mappings.

#include <gtest/gtest.h>

#include <array>

#include "catamaze/core/types.hpp"

namespace catamaze::core {
namespace {

TEST(Types, DirectionsMoveAndRoundTripThroughActions) {
  constexpr Position origin{10, 10};
  constexpr std::array<Direction, 4> directions{Direction::Up, Direction::Right, Direction::Down,
                                                Direction::Left};
  constexpr std::array<Position, 4> expected{Position{10, 9}, Position{11, 10}, Position{10, 11},
                                             Position{9, 10}};

  for (std::size_t index = 0; index < directions.size(); ++index) {
    EXPECT_EQ(moved(origin, directions[index]), expected[index]);
    EXPECT_TRUE(isMoveAction(moveAction(directions[index])));
    EXPECT_FALSE(isShootAction(moveAction(directions[index])));
    EXPECT_TRUE(isShootAction(shootAction(directions[index])));
    EXPECT_FALSE(isMoveAction(shootAction(directions[index])));
    EXPECT_EQ(actionDirection(moveAction(directions[index])), directions[index]);
    EXPECT_EQ(actionDirection(shootAction(directions[index])), directions[index]);
  }
  EXPECT_FALSE(isMoveAction(Action::Wait));
  EXPECT_FALSE(isShootAction(Action::Wait));
  EXPECT_EQ(actionDirection(Action::Wait), Direction::Up);
}

TEST(Types, EveryActionHasTheFrozenWireName) {
  constexpr std::array<Action, 9> actions{Action::MoveUp,    Action::MoveDown,   Action::MoveLeft,
                                          Action::MoveRight, Action::ShootUp,    Action::ShootDown,
                                          Action::ShootLeft, Action::ShootRight, Action::Wait};
  constexpr std::array<std::string_view, 9> names{"MOVE_UP",    "MOVE_DOWN",   "MOVE_LEFT",
                                                  "MOVE_RIGHT", "SHOOT_UP",    "SHOOT_DOWN",
                                                  "SHOOT_LEFT", "SHOOT_RIGHT", "WAIT"};
  for (std::size_t index = 0; index < actions.size(); ++index) {
    EXPECT_EQ(toString(actions[index]), names[index]);
  }
}

TEST(Types, EveryGameStatusHasTheFrozenWireName) {
  EXPECT_EQ(toString(GameStatus::Running), "RUNNING");
  EXPECT_EQ(toString(GameStatus::Victory), "VICTORY");
  EXPECT_EQ(toString(GameStatus::Death), "DEATH");
  EXPECT_EQ(toString(GameStatus::Timeout), "TIMEOUT");
}

TEST(Types, PositionAndEntityIndexOperatorsAreStable) {
  EXPECT_EQ((Position{4, 9}), (Position{4, 9}));
  EXPECT_NE((Position{4, 9}), (Position{9, 4}));
  EXPECT_EQ(entityIndex(EntityId::Player), 0U);
  EXPECT_EQ(entityIndex(EntityId::Aggressive), 1U);
  EXPECT_EQ(entityIndex(EntityId::Cautious), 2U);
  EXPECT_EQ(entityIndex(EntityId::Explorer), 3U);
}

}  // namespace
}  // namespace catamaze::core
