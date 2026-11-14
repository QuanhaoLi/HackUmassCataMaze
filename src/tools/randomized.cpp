// Created at: 2026-11-14 02:51 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Runs deterministic randomized games and checks domain invariants after every simulated tick.

#include <array>
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>

#include "catamaze/app/application.hpp"
#include "catamaze/core/random.hpp"

namespace {

bool parseUnsigned(const std::string& text, std::uint64_t& value) {
  errno = 0;
  char* end = nullptr;
  const unsigned long long parsed = std::strtoull(text.c_str(), &end, 0);
  if (errno != 0 || end == text.c_str() || *end != '\0') return false;
  value = static_cast<std::uint64_t>(parsed);
  return true;
}

bool validate(const catamaze::core::WorldState& state, std::string& error) {
  using namespace catamaze::core;
  if (state.tick > kMaxTicks) {
    error = "tick exceeded maximum";
    return false;
  }
  if (state.player_queue.size() > kPlayerQueueCapacity) {
    error = "player queue exceeded capacity";
    return false;
  }
  if (state.bullet_count > kMaxBullets || state.event_count > kMaxEvents) {
    error = "fixed-capacity collection overflow";
    return false;
  }
  for (std::size_t index = 0; index < state.entities.size(); ++index) {
    const auto& entity = state.entities[index];
    if (!state.map.inBounds(entity.position) || !state.map.isWalkable(entity.position)) {
      error = "entity left walkable terrain";
      return false;
    }
    if (entity.hp > kMaxHp || entity.ammo > kMaxAmmo || entity.recharge_progress > 1U ||
        entity.alive != (entity.hp > 0U)) {
      error = "entity resource invariant failed";
      return false;
    }
    if (!entity.alive) continue;
    for (std::size_t other = index + 1U; other < state.entities.size(); ++other) {
      if (state.entities[other].alive && entity.position == state.entities[other].position) {
        error = "living entities overlap";
        return false;
      }
    }
  }
  for (std::size_t index = 0; index < state.bullet_count; ++index) {
    if (!state.map.inBounds(state.bullets[index].position) ||
        !state.map.isWalkable(state.bullets[index].position)) {
      error = "bullet left walkable terrain";
      return false;
    }
  }
  const auto& player = state.entities[entityIndex(EntityId::Player)];
  if (state.status == GameStatus::Death && player.alive) {
    error = "death status has living player";
    return false;
  }
  if (state.status == GameStatus::Victory &&
      (!player.alive || state.map.at(player.position) != Terrain::Exit)) {
    error = "victory status is inconsistent";
    return false;
  }
  if (state.status == GameStatus::Timeout && state.tick != kMaxTicks) {
    error = "timeout did not occur at maximum tick";
    return false;
  }
  return true;
}

std::uint64_t nextSeed(catamaze::core::Pcg32& random) {
  return (static_cast<std::uint64_t>(random.next()) << 32U) | random.next();
}

}  // namespace

int main(int argc, char** argv) {
  std::uint64_t total_ticks = 100000U;
  std::uint64_t seed = 0x5eed1234cafebabeULL;
  for (int index = 1; index < argc; ++index) {
    const std::string option = argv[index];
    if ((option == "--ticks" || option == "--seed") && index + 1 >= argc) {
      std::cerr << option << " requires a value\n";
      return 2;
    }
    if (option == "--ticks") {
      if (!parseUnsigned(argv[++index], total_ticks) || total_ticks == 0U) {
        std::cerr << "invalid tick count\n";
        return 2;
      }
    } else if (option == "--seed") {
      if (!parseUnsigned(argv[++index], seed)) {
        std::cerr << "invalid seed\n";
        return 2;
      }
    } else {
      std::cerr << "unknown option: " << option << '\n';
      return 2;
    }
  }

  constexpr std::array<catamaze::core::Action, 9> kActions{
      catamaze::core::Action::MoveUp,    catamaze::core::Action::MoveDown,
      catamaze::core::Action::MoveLeft,  catamaze::core::Action::MoveRight,
      catamaze::core::Action::ShootUp,   catamaze::core::Action::ShootDown,
      catamaze::core::Action::ShootLeft, catamaze::core::Action::ShootRight,
      catamaze::core::Action::Wait};

  catamaze::core::Pcg32 random(seed, 0x72616e646f6d697aULL);
  catamaze::app::Application application(nextSeed(random));
  std::uint64_t aggregate = 0xcbf29ce484222325ULL;
  std::uint64_t games = 1U;

  for (std::uint64_t simulated = 0; simulated < total_ticks; ++simulated) {
    if (application.state().status != catamaze::core::GameStatus::Running) {
      application.reset(nextSeed(random));
      ++games;
    }
    if (random.bounded(97U) == 0U) application.clearPlayerQueue();
    const std::uint32_t burst = 1U + random.bounded(4U);
    for (std::uint32_t input = 0; input < burst; ++input) {
      application.enqueuePlayerAction(kActions[random.bounded(kActions.size())]);
    }
    application.tick();

    std::string error;
    if (!validate(application.state(), error)) {
      std::cerr << "RANDOMIZED_FAILURE simulated=" << simulated
                << " game_tick=" << application.state().tick << " hash=0x" << std::hex
                << application.stateHash() << std::dec << " reason=" << error << '\n';
      return 1;
    }
    aggregate ^=
        application.stateHash() + 0x9e3779b97f4a7c15ULL + (aggregate << 6U) + (aggregate >> 2U);
  }

  std::cout << "RANDOMIZED_OK ticks=" << total_ticks << " games=" << games << " hash=0x" << std::hex
            << std::setw(16) << std::setfill('0') << aggregate << std::dec << '\n';
  return 0;
}
