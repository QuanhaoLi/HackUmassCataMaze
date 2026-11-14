// Created at: 2026-11-14 02:19 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Implements stable action, direction, and status helpers without platform dependencies.

#include "catamaze/core/types.hpp"

namespace catamaze::core {

Position moved(Position origin, Direction direction) noexcept {
  switch (direction) {
    case Direction::Up:
      --origin.y;
      break;
    case Direction::Right:
      ++origin.x;
      break;
    case Direction::Down:
      ++origin.y;
      break;
    case Direction::Left:
      --origin.x;
      break;
  }
  return origin;
}

bool isMoveAction(Action action) noexcept {
  return action == Action::MoveUp || action == Action::MoveDown || action == Action::MoveLeft ||
         action == Action::MoveRight;
}

bool isShootAction(Action action) noexcept {
  return action == Action::ShootUp || action == Action::ShootDown || action == Action::ShootLeft ||
         action == Action::ShootRight;
}

Direction actionDirection(Action action) noexcept {
  switch (action) {
    case Action::MoveUp:
    case Action::ShootUp:
      return Direction::Up;
    case Action::MoveRight:
    case Action::ShootRight:
      return Direction::Right;
    case Action::MoveDown:
    case Action::ShootDown:
      return Direction::Down;
    case Action::MoveLeft:
    case Action::ShootLeft:
      return Direction::Left;
    case Action::Wait:
      return Direction::Up;
  }
  return Direction::Up;
}

Action moveAction(Direction direction) noexcept {
  switch (direction) {
    case Direction::Up:
      return Action::MoveUp;
    case Direction::Right:
      return Action::MoveRight;
    case Direction::Down:
      return Action::MoveDown;
    case Direction::Left:
      return Action::MoveLeft;
  }
  return Action::Wait;
}

Action shootAction(Direction direction) noexcept {
  switch (direction) {
    case Direction::Up:
      return Action::ShootUp;
    case Direction::Right:
      return Action::ShootRight;
    case Direction::Down:
      return Action::ShootDown;
    case Direction::Left:
      return Action::ShootLeft;
  }
  return Action::Wait;
}

std::string_view toString(Action action) noexcept {
  switch (action) {
    case Action::MoveUp:
      return "MOVE_UP";
    case Action::MoveDown:
      return "MOVE_DOWN";
    case Action::MoveLeft:
      return "MOVE_LEFT";
    case Action::MoveRight:
      return "MOVE_RIGHT";
    case Action::ShootUp:
      return "SHOOT_UP";
    case Action::ShootDown:
      return "SHOOT_DOWN";
    case Action::ShootLeft:
      return "SHOOT_LEFT";
    case Action::ShootRight:
      return "SHOOT_RIGHT";
    case Action::Wait:
      return "WAIT";
  }
  return "WAIT";
}

std::string_view toString(GameStatus status) noexcept {
  switch (status) {
    case GameStatus::Running:
      return "RUNNING";
    case GameStatus::Victory:
      return "VICTORY";
    case GameStatus::Death:
      return "DEATH";
    case GameStatus::Timeout:
      return "TIMEOUT";
  }
  return "RUNNING";
}

}  // namespace catamaze::core
