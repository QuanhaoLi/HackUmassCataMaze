// Created at: 2026-11-14 03:43 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:38 EST
// Last Modified by: Codex
// Binds batched in-memory C++ environments to fixed-shape NumPy tensors.

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

#include "catamaze/core/engine.hpp"
#include "catamaze/core/map.hpp"
#include "catamaze/core/policy_contract.hpp"
#include "catamaze/core/random.hpp"
#include "catamaze/core/version.hpp"

namespace py = pybind11;

namespace catamaze::training {
namespace {

using core::Action;
using core::EntityId;
using core::Event;
using core::GameEngine;

template <typename T>
using CArray = py::array_t<T, py::array::c_style | py::array::forcecast>;

std::size_t positionIndex(core::Position position) noexcept {
  return static_cast<std::size_t>(position.y) * static_cast<std::size_t>(core::kMapSize) +
         static_cast<std::size_t>(position.x);
}

void requireAction(std::uint8_t value) {
  if (value >= core::kPolicyActionCount) {
    throw py::value_error("actions must be in range [0, 8]");
  }
}

void appendU8(std::string& output, std::uint8_t value) {
  output.push_back(static_cast<char>(value));
}

void appendU16(std::string& output, std::uint16_t value) {
  appendU8(output, static_cast<std::uint8_t>(value & 0xffU));
  appendU8(output, static_cast<std::uint8_t>((value >> 8U) & 0xffU));
}

void appendU64(std::string& output, std::uint64_t value) {
  for (std::size_t byte = 0; byte < 8U; ++byte) {
    appendU8(output, static_cast<std::uint8_t>((value >> (byte * 8U)) & 0xffU));
  }
}

class StateReader {
 public:
  explicit StateReader(const std::string& input) : input_(input) {}

  std::uint8_t u8() {
    require(1U);
    return static_cast<std::uint8_t>(input_[position_++]);
  }

  std::uint16_t u16() {
    const std::uint16_t low = u8();
    return static_cast<std::uint16_t>(low | (static_cast<std::uint16_t>(u8()) << 8U));
  }

  std::uint64_t u64() {
    std::uint64_t value = 0U;
    for (std::size_t byte = 0; byte < 8U; ++byte) {
      value |= static_cast<std::uint64_t>(u8()) << (byte * 8U);
    }
    return value;
  }

  void magic(const std::string& expected) {
    require(expected.size());
    if (input_.compare(position_, expected.size(), expected) != 0) {
      throw py::value_error("invalid Native environment state magic");
    }
    position_ += expected.size();
  }

  void requireEnd() const {
    if (position_ != input_.size()) {
      throw py::value_error("Native environment state has trailing data");
    }
  }

 private:
  void require(std::size_t size) const {
    if (size > input_.size() - std::min(position_, input_.size())) {
      throw py::value_error("truncated Native environment state");
    }
  }

  const std::string& input_;
  std::size_t position_{0U};
};

std::string serializeEngine(const GameEngine& engine) {
  const core::WorldState& state = engine.state();
  std::string output;
  output.reserve(5000U);
  output.append("CMTR", 4U);
  appendU8(output, 1U);
  appendU64(output, state.seed);
  appendU16(output, state.tick);
  appendU8(output, static_cast<std::uint8_t>(state.status));
  for (core::Terrain terrain : state.map.cells()) {
    appendU8(output, static_cast<std::uint8_t>(terrain));
  }
  for (const core::EntityState& entity : state.entities) {
    appendU8(output, static_cast<std::uint8_t>(entity.id));
    appendU8(output, static_cast<std::uint8_t>(entity.persona));
    appendU16(output, static_cast<std::uint16_t>(entity.position.x));
    appendU16(output, static_cast<std::uint16_t>(entity.position.y));
    appendU8(output, entity.hp);
    appendU8(output, entity.ammo);
    appendU8(output, entity.recharge_progress);
    appendU8(output, entity.alive ? 1U : 0U);
    appendU8(output, static_cast<std::uint8_t>(entity.last_action));
    appendU8(output, static_cast<std::uint8_t>(entity.last_result));
  }
  appendU16(output, static_cast<std::uint16_t>(state.bullet_count));
  for (std::size_t index = 0; index < state.bullet_count; ++index) {
    const core::Bullet& bullet = state.bullets[index];
    appendU16(output, static_cast<std::uint16_t>(bullet.position.x));
    appendU16(output, static_cast<std::uint16_t>(bullet.position.y));
    appendU8(output, static_cast<std::uint8_t>(bullet.direction));
    appendU8(output, static_cast<std::uint8_t>(bullet.shooter));
  }
  appendU8(output, static_cast<std::uint8_t>(state.player_queue.size()));
  for (std::size_t index = 0; index < state.player_queue.size(); ++index) {
    appendU8(output, static_cast<std::uint8_t>(state.player_queue.at(index)));
  }
  appendU16(output, static_cast<std::uint16_t>(state.event_count));
  for (std::size_t index = 0; index < state.event_count; ++index) {
    const Event& event = state.events[index];
    appendU8(output, static_cast<std::uint8_t>(event.type));
    appendU8(output, static_cast<std::uint8_t>(event.actor));
    appendU8(output, static_cast<std::uint8_t>(event.target));
    appendU16(output, static_cast<std::uint16_t>(event.position.x));
    appendU16(output, static_cast<std::uint16_t>(event.position.y));
    appendU8(output, static_cast<std::uint8_t>(event.direction));
    appendU8(output, event.value);
  }
  return output;
}

core::WorldState deserializeEngine(const std::string& input) {
  StateReader reader(input);
  reader.magic("CMTR");
  if (reader.u8() != 1U) {
    throw py::value_error("unsupported Native environment state version");
  }
  core::WorldState state{};
  state.seed = reader.u64();
  state.tick = reader.u16();
  state.status = static_cast<core::GameStatus>(reader.u8());
  for (std::int16_t y = 0; y < core::kMapSize; ++y) {
    for (std::int16_t x = 0; x < core::kMapSize; ++x) {
      const auto terrain = static_cast<core::Terrain>(reader.u8());
      if (static_cast<std::uint8_t>(terrain) > static_cast<std::uint8_t>(core::Terrain::Exit)) {
        throw py::value_error("invalid terrain in Native environment state");
      }
      state.map.set(core::Position{x, y}, terrain);
    }
  }
  for (core::EntityState& entity : state.entities) {
    entity.id = static_cast<EntityId>(reader.u8());
    entity.persona = static_cast<core::Persona>(reader.u8());
    entity.position.x = static_cast<std::int16_t>(reader.u16());
    entity.position.y = static_cast<std::int16_t>(reader.u16());
    entity.hp = reader.u8();
    entity.ammo = reader.u8();
    entity.recharge_progress = reader.u8();
    entity.alive = reader.u8() != 0U;
    entity.last_action = static_cast<Action>(reader.u8());
    entity.last_result = static_cast<core::ActionResult>(reader.u8());
  }
  state.bullet_count = reader.u16();
  if (state.bullet_count > core::kMaxBullets) {
    throw py::value_error("too many bullets in Native environment state");
  }
  for (std::size_t index = 0; index < state.bullet_count; ++index) {
    core::Bullet& bullet = state.bullets[index];
    bullet.position.x = static_cast<std::int16_t>(reader.u16());
    bullet.position.y = static_cast<std::int16_t>(reader.u16());
    bullet.direction = static_cast<core::Direction>(reader.u8());
    bullet.shooter = static_cast<EntityId>(reader.u8());
  }
  const std::size_t queue_size = reader.u8();
  if (queue_size > core::kPlayerQueueCapacity) {
    throw py::value_error("player queue too large in Native environment state");
  }
  for (std::size_t index = 0; index < queue_size; ++index) {
    if (!state.player_queue.push(static_cast<Action>(reader.u8()))) {
      throw py::value_error("invalid player queue in Native environment state");
    }
  }
  state.event_count = reader.u16();
  if (state.event_count > core::kMaxEvents) {
    throw py::value_error("too many events in Native environment state");
  }
  for (std::size_t index = 0; index < state.event_count; ++index) {
    Event& event = state.events[index];
    event.type = static_cast<core::EventType>(reader.u8());
    event.actor = static_cast<EntityId>(reader.u8());
    event.target = static_cast<EntityId>(reader.u8());
    event.position.x = static_cast<std::int16_t>(reader.u16());
    event.position.y = static_cast<std::int16_t>(reader.u16());
    event.direction = static_cast<core::Direction>(reader.u8());
    event.value = reader.u8();
  }
  reader.requireEnd();
  return state;
}

core::GameSetup randomizedSetup(std::uint64_t seed) {
  const core::GeneratedWorld generated = core::MazeGenerator::generate(seed);
  core::GameSetup setup{generated.map, generated.spawns, seed};
  std::array<core::Position, core::kMapCellCount> candidates{};
  std::size_t candidate_count = 0U;
  for (std::int16_t y = 0; y < core::kMapSize; ++y) {
    for (std::int16_t x = 0; x < core::kMapSize; ++x) {
      const core::Position position{x, y};
      if (setup.map.isWalkable(position) && setup.map.at(position) != core::Terrain::Exit) {
        candidates[candidate_count++] = position;
      }
    }
  }
  core::Pcg32 random(seed, 0x545241494e53504eULL);
  for (std::size_t entity = 0; entity < core::kEntityCount; ++entity) {
    const std::size_t selected =
        entity + random.bounded(static_cast<std::uint32_t>(candidate_count - entity));
    std::swap(candidates[entity], candidates[selected]);
    setup.spawns[entity] = candidates[entity];
  }
  return setup;
}

Action shortestPathAction(const core::WorldState& state,
                          const core::EncodedObservation& player_observation) noexcept {
  const core::EntityState& player = state.entities[core::entityIndex(EntityId::Player)];
  if (!player.alive) {
    return Action::Wait;
  }
  core::Position exit{};
  bool found_exit = false;
  for (std::int16_t y = 0; y < core::kMapSize && !found_exit; ++y) {
    for (std::int16_t x = 0; x < core::kMapSize; ++x) {
      if (state.map.at(core::Position{x, y}) == core::Terrain::Exit) {
        exit = core::Position{x, y};
        found_exit = true;
        break;
      }
    }
  }
  if (!found_exit) {
    return Action::Wait;
  }
  const core::DistanceField distances = core::shortestDistances(state.map, exit);
  const std::int16_t current_distance = distances[positionIndex(player.position)];
  constexpr std::array<core::Direction, 4> kDirections{
      core::Direction::Up, core::Direction::Right, core::Direction::Down, core::Direction::Left};
  constexpr std::array<Action, 4> kActions{Action::MoveUp, Action::MoveRight, Action::MoveDown,
                                           Action::MoveLeft};
  Action best = Action::Wait;
  std::int16_t best_distance = current_distance;
  for (std::size_t index = 0; index < kDirections.size(); ++index) {
    const Action action = kActions[index];
    if (!player_observation.action_mask[static_cast<std::size_t>(action)]) {
      continue;
    }
    const core::Position next = core::moved(player.position, kDirections[index]);
    const std::int16_t candidate_distance = distances[positionIndex(next)];
    if (candidate_distance >= 0 && candidate_distance < best_distance) {
      best = action;
      best_distance = candidate_distance;
    }
  }
  return best;
}

class NativeBatch {
 public:
  explicit NativeBatch(const CArray<std::uint64_t>& seeds, bool randomize_spawns)
      : randomize_spawns_(randomize_spawns) {
    initialize(seeds);
  }

  std::size_t size() const noexcept { return engines_.size(); }

  py::dict reset(const CArray<std::uint64_t>& seeds) {
    if (seeds.ndim() != 1) {
      throw py::value_error("reset seeds must have shape [num_envs]");
    }
    const auto input = seeds.unchecked<1>();
    if (static_cast<std::size_t>(input.shape(0)) != engines_.size()) {
      throw py::value_error("reset seeds must have shape [num_envs]");
    }
    {
      py::gil_scoped_release release;
      for (py::ssize_t env = 0; env < input.shape(0); ++env) {
        resetOne(static_cast<std::size_t>(env), input(env));
      }
    }
    return snapshot();
  }

  py::dict resetAt(const CArray<std::int64_t>& indices,
                   const CArray<std::uint64_t>& seeds) {
    if (indices.ndim() != 1 || seeds.ndim() != 1) {
      throw py::value_error("reset_at indices and seeds must be one-dimensional");
    }
    const auto index_values = indices.unchecked<1>();
    const auto seed_values = seeds.unchecked<1>();
    if (index_values.shape(0) != seed_values.shape(0)) {
      throw py::value_error("reset_at indices and seeds must have equal length");
    }
    std::vector<bool> selected(engines_.size(), false);
    for (py::ssize_t item = 0; item < index_values.shape(0); ++item) {
      const std::int64_t index = index_values(item);
      if (index < 0 || static_cast<std::size_t>(index) >= engines_.size()) {
        throw py::value_error("reset_at index is out of range");
      }
      if (selected[static_cast<std::size_t>(index)]) {
        throw py::value_error("reset_at indices must be unique");
      }
      selected[static_cast<std::size_t>(index)] = true;
    }
    {
      py::gil_scoped_release release;
      for (py::ssize_t item = 0; item < index_values.shape(0); ++item) {
        resetOne(static_cast<std::size_t>(index_values(item)), seed_values(item));
      }
    }
    return snapshot();
  }

  py::dict step(const CArray<std::uint8_t>& player_actions,
                const CArray<std::uint8_t>& ai_actions) {
    if (player_actions.ndim() != 1) {
      throw py::value_error("player_actions must have shape [num_envs]");
    }
    if (ai_actions.ndim() != 2) {
      throw py::value_error("ai_actions must have shape [num_envs, 3]");
    }
    const auto players = player_actions.unchecked<1>();
    const auto agents = ai_actions.unchecked<2>();
    const py::ssize_t env_count = static_cast<py::ssize_t>(engines_.size());
    if (players.shape(0) != env_count) {
      throw py::value_error("player_actions must have shape [num_envs]");
    }
    if (agents.shape(0) != env_count || agents.shape(1) != static_cast<py::ssize_t>(core::kAiCount)) {
      throw py::value_error("ai_actions must have shape [num_envs, 3]");
    }

    std::vector<Action> player_values(engines_.size());
    std::vector<std::array<Action, core::kAiCount>> agent_values(engines_.size());
    for (py::ssize_t env = 0; env < env_count; ++env) {
      requireAction(players(env));
      player_values[static_cast<std::size_t>(env)] = static_cast<Action>(players(env));
      for (std::size_t agent = 0; agent < core::kAiCount; ++agent) {
        requireAction(agents(env, static_cast<py::ssize_t>(agent)));
        agent_values[static_cast<std::size_t>(env)][agent] =
            static_cast<Action>(agents(env, static_cast<py::ssize_t>(agent)));
      }
    }

    {
      py::gil_scoped_release release;
      for (std::size_t env = 0; env < engines_.size(); ++env) {
        GameEngine& engine = engines_[env];
        if (!engine.enqueuePlayerAction(player_values[env]) &&
            engine.state().status == core::GameStatus::Running) {
          throw std::runtime_error("player action queue unexpectedly rejected a training action");
        }
        engine.step(agent_values[env]);
      }
    }
    return snapshot();
  }

  py::dict snapshot() const {
    const py::ssize_t env_count = static_cast<py::ssize_t>(engines_.size());
    py::array_t<std::uint8_t> spatial(
        std::vector<py::ssize_t>{env_count, 3, 13, 5, 5});
    py::array_t<float> scalar(std::vector<py::ssize_t>{env_count, 3, 46});
    py::array_t<bool> action_mask(std::vector<py::ssize_t>{env_count, 3, 9});
    py::array_t<bool> alive(std::vector<py::ssize_t>{env_count, 3});
    py::array_t<std::int16_t> positions(std::vector<py::ssize_t>{env_count, 4, 2});
    py::array_t<std::uint8_t> hp(std::vector<py::ssize_t>{env_count, 4});
    py::array_t<std::uint8_t> ammo(std::vector<py::ssize_t>{env_count, 4});
    py::array_t<std::uint8_t> recharge(std::vector<py::ssize_t>{env_count, 4});
    py::array_t<std::uint8_t> last_action(std::vector<py::ssize_t>{env_count, 4});
    py::array_t<std::uint8_t> last_result(std::vector<py::ssize_t>{env_count, 4});
    py::array_t<std::uint8_t> status(std::vector<py::ssize_t>{env_count});
    py::array_t<std::uint16_t> tick(std::vector<py::ssize_t>{env_count});
    py::array_t<std::uint64_t> seed(std::vector<py::ssize_t>{env_count});
    py::array_t<std::uint64_t> state_hash(std::vector<py::ssize_t>{env_count});
    py::array_t<std::int16_t> events(
        std::vector<py::ssize_t>{env_count, static_cast<py::ssize_t>(core::kMaxEvents), 7});
    py::array_t<std::uint16_t> event_count(std::vector<py::ssize_t>{env_count});
    py::array_t<std::int16_t> distance_to_player(
        std::vector<py::ssize_t>{env_count, 3});
    py::array_t<std::uint8_t> player_spatial(
        std::vector<py::ssize_t>{env_count, 13, 5, 5});
    py::array_t<bool> player_action_mask(std::vector<py::ssize_t>{env_count, 9});
    py::array_t<std::uint8_t> shortest_path_action(
        std::vector<py::ssize_t>{env_count});

    auto spatial_out = spatial.mutable_unchecked<5>();
    auto scalar_out = scalar.mutable_unchecked<3>();
    auto mask_out = action_mask.mutable_unchecked<3>();
    auto alive_out = alive.mutable_unchecked<2>();
    auto position_out = positions.mutable_unchecked<3>();
    auto hp_out = hp.mutable_unchecked<2>();
    auto ammo_out = ammo.mutable_unchecked<2>();
    auto recharge_out = recharge.mutable_unchecked<2>();
    auto last_action_out = last_action.mutable_unchecked<2>();
    auto last_result_out = last_result.mutable_unchecked<2>();
    auto status_out = status.mutable_unchecked<1>();
    auto tick_out = tick.mutable_unchecked<1>();
    auto seed_out = seed.mutable_unchecked<1>();
    auto hash_out = state_hash.mutable_unchecked<1>();
    auto events_out = events.mutable_unchecked<3>();
    auto event_count_out = event_count.mutable_unchecked<1>();
    auto distance_out = distance_to_player.mutable_unchecked<2>();
    auto player_spatial_out = player_spatial.mutable_unchecked<4>();
    auto player_mask_out = player_action_mask.mutable_unchecked<2>();
    auto shortest_action_out = shortest_path_action.mutable_unchecked<1>();

    std::fill(events.mutable_data(), events.mutable_data() + events.size(),
              static_cast<std::int16_t>(-1));
    for (std::size_t env = 0; env < engines_.size(); ++env) {
      const GameEngine& engine = engines_[env];
      const core::WorldState& state = engine.state();
      const py::ssize_t env_index = static_cast<py::ssize_t>(env);
      status_out(env_index) = static_cast<std::uint8_t>(state.status);
      tick_out(env_index) = state.tick;
      seed_out(env_index) = state.seed;
      hash_out(env_index) = engine.stateHash();

      for (std::size_t entity = 0; entity < core::kEntityCount; ++entity) {
        const core::EntityState& current = state.entities[entity];
        const py::ssize_t entity_index = static_cast<py::ssize_t>(entity);
        position_out(env_index, entity_index, 0) = current.position.x;
        position_out(env_index, entity_index, 1) = current.position.y;
        hp_out(env_index, entity_index) = current.hp;
        ammo_out(env_index, entity_index) = current.ammo;
        recharge_out(env_index, entity_index) = current.recharge_progress;
        last_action_out(env_index, entity_index) = static_cast<std::uint8_t>(current.last_action);
        last_result_out(env_index, entity_index) = static_cast<std::uint8_t>(current.last_result);
      }

      const core::EntityState& player = state.entities[core::entityIndex(EntityId::Player)];
      const core::DistanceField distances = core::shortestDistances(state.map, player.position);
      const core::EncodedObservation encoded_player =
          core::encodePolicyObservation(engine.observe(EntityId::Player), state.tick);
      for (std::size_t channel = 0; channel < core::kPolicySpatialChannels; ++channel) {
        for (std::size_t cell = 0; cell < core::kPolicyGridCellCount; ++cell) {
          player_spatial_out(env_index, static_cast<py::ssize_t>(channel),
                             static_cast<py::ssize_t>(cell / 5U),
                             static_cast<py::ssize_t>(cell % 5U)) =
              encoded_player.spatial[core::spatialIndex(channel, cell)];
        }
      }
      for (std::size_t action = 0; action < core::kPolicyActionCount; ++action) {
        player_mask_out(env_index, static_cast<py::ssize_t>(action)) =
            encoded_player.action_mask[action];
      }
      shortest_action_out(env_index) =
          static_cast<std::uint8_t>(shortestPathAction(state, encoded_player));
      for (std::size_t agent = 0; agent < core::kAiCount; ++agent) {
        const EntityId id = static_cast<EntityId>(agent + 1U);
        const core::Observation observation = engine.observe(id);
        const core::EncodedObservation encoded =
            core::encodePolicyObservation(observation, state.tick);
        const py::ssize_t agent_index = static_cast<py::ssize_t>(agent);
        alive_out(env_index, agent_index) = observation.self.alive;
        for (std::size_t channel = 0; channel < core::kPolicySpatialChannels; ++channel) {
          for (std::size_t cell = 0; cell < core::kPolicyGridCellCount; ++cell) {
            spatial_out(env_index, agent_index, static_cast<py::ssize_t>(channel),
                        static_cast<py::ssize_t>(cell / 5U),
                        static_cast<py::ssize_t>(cell % 5U)) =
                encoded.spatial[core::spatialIndex(channel, cell)];
          }
        }
        for (std::size_t feature = 0; feature < core::kPolicyScalarFeatures; ++feature) {
          scalar_out(env_index, agent_index, static_cast<py::ssize_t>(feature)) =
              encoded.scalar[feature];
        }
        for (std::size_t action = 0; action < core::kPolicyActionCount; ++action) {
          mask_out(env_index, agent_index, static_cast<py::ssize_t>(action)) =
              encoded.action_mask[action];
        }
        distance_out(env_index, agent_index) =
            observation.self.alive && player.alive
                ? distances[positionIndex(observation.self.position)]
                : core::kUnreachableDistance;
      }

      event_count_out(env_index) = static_cast<std::uint16_t>(state.event_count);
      for (std::size_t event_index = 0; event_index < state.event_count; ++event_index) {
        const Event& event = state.events[event_index];
        const py::ssize_t output_index = static_cast<py::ssize_t>(event_index);
        events_out(env_index, output_index, 0) = static_cast<std::uint8_t>(event.type);
        events_out(env_index, output_index, 1) = static_cast<std::uint8_t>(event.actor);
        events_out(env_index, output_index, 2) = static_cast<std::uint8_t>(event.target);
        events_out(env_index, output_index, 3) = event.position.x;
        events_out(env_index, output_index, 4) = event.position.y;
        events_out(env_index, output_index, 5) = static_cast<std::uint8_t>(event.direction);
        events_out(env_index, output_index, 6) = event.value;
      }
    }

    py::dict result;
    result["spatial"] = std::move(spatial);
    result["scalar"] = std::move(scalar);
    result["action_mask"] = std::move(action_mask);
    result["alive"] = std::move(alive);
    result["positions"] = std::move(positions);
    result["hp"] = std::move(hp);
    result["ammo"] = std::move(ammo);
    result["recharge_progress"] = std::move(recharge);
    result["last_action"] = std::move(last_action);
    result["last_result"] = std::move(last_result);
    result["status"] = std::move(status);
    result["tick"] = std::move(tick);
    result["seed"] = std::move(seed);
    result["state_hash"] = std::move(state_hash);
    result["events"] = std::move(events);
    result["event_count"] = std::move(event_count);
    result["distance_to_player"] = std::move(distance_to_player);
    result["player_spatial"] = std::move(player_spatial);
    result["player_action_mask"] = std::move(player_action_mask);
    result["shortest_path_action"] = std::move(shortest_path_action);
    return result;
  }

  py::list saveState() const {
    py::list output;
    for (const GameEngine& engine : engines_) {
      output.append(py::bytes(serializeEngine(engine)));
    }
    return output;
  }

  void loadState(const py::sequence& states) {
    if (static_cast<std::size_t>(py::len(states)) != engines_.size()) {
      throw py::value_error("Native environment state count does not match num_envs");
    }
    std::vector<core::WorldState> decoded;
    decoded.reserve(engines_.size());
    for (std::size_t env = 0; env < engines_.size(); ++env) {
      decoded.push_back(deserializeEngine(py::cast<std::string>(states[env])));
    }
    for (std::size_t env = 0; env < engines_.size(); ++env) {
      engines_[env].restore(decoded[env]);
    }
  }

 private:
  void initialize(const CArray<std::uint64_t>& seeds) {
    if (seeds.ndim() != 1) {
      throw py::value_error("seeds must have non-empty shape [num_envs]");
    }
    const auto input = seeds.unchecked<1>();
    if (input.shape(0) <= 0) {
      throw py::value_error("seeds must have non-empty shape [num_envs]");
    }
    engines_.reserve(static_cast<std::size_t>(input.shape(0)));
    for (py::ssize_t env = 0; env < input.shape(0); ++env) {
      if (randomize_spawns_) {
        engines_.emplace_back(randomizedSetup(input(env)));
      } else {
        engines_.emplace_back(input(env));
      }
    }
  }

  void resetOne(std::size_t env, std::uint64_t seed) {
    if (randomize_spawns_) {
      engines_[env] = GameEngine(randomizedSetup(seed));
    } else {
      engines_[env].reset(seed);
    }
  }

  std::vector<GameEngine> engines_;
  bool randomize_spawns_{false};
};

}  // namespace
}  // namespace catamaze::training

PYBIND11_MODULE(_native, module) {
  module.doc() = "CataMaze deterministic batched Native training environment";
  module.attr("environment_version") =
      std::string(catamaze::core::kEnvironmentVersion);
  module.attr("observation_schema_version") =
      std::string(catamaze::core::kObservationSchemaVersion);
  module.attr("STATUS_RUNNING") =
      static_cast<std::uint8_t>(catamaze::core::GameStatus::Running);
  module.attr("STATUS_VICTORY") =
      static_cast<std::uint8_t>(catamaze::core::GameStatus::Victory);
  module.attr("STATUS_DEATH") =
      static_cast<std::uint8_t>(catamaze::core::GameStatus::Death);
  module.attr("STATUS_TIMEOUT") =
      static_cast<std::uint8_t>(catamaze::core::GameStatus::Timeout);
  module.attr("RESULT_MOVED") =
      static_cast<std::uint8_t>(catamaze::core::ActionResult::Moved);
  module.attr("RESULT_BLOCKED_WALL") =
      static_cast<std::uint8_t>(catamaze::core::ActionResult::BlockedWall);
  module.attr("RESULT_BLOCKED_ENTITY") =
      static_cast<std::uint8_t>(catamaze::core::ActionResult::BlockedEntity);
  module.attr("RESULT_BLOCKED_CONFLICT") =
      static_cast<std::uint8_t>(catamaze::core::ActionResult::BlockedConflict);
  module.attr("RESULT_BLOCKED_BOUNDS") =
      static_cast<std::uint8_t>(catamaze::core::ActionResult::BlockedBounds);
  module.attr("RESULT_INVALID_FALLBACK") =
      static_cast<std::uint8_t>(catamaze::core::ActionResult::InvalidFallback);
  module.attr("EVENT_SHOT") = static_cast<std::uint8_t>(catamaze::core::EventType::Shot);
  module.attr("EVENT_DAMAGE_APPLIED") =
      static_cast<std::uint8_t>(catamaze::core::EventType::DamageApplied);
  module.attr("EVENT_ENTITY_DIED") =
      static_cast<std::uint8_t>(catamaze::core::EventType::EntityDied);
  module.attr("EVENT_DAMAGE_CREDIT") =
      static_cast<std::uint8_t>(catamaze::core::EventType::DamageCredit);
  py::class_<catamaze::training::NativeBatch>(module, "NativeBatch")
      .def(py::init<const catamaze::training::CArray<std::uint64_t>&, bool>(), py::arg("seeds"),
           py::arg("randomize_spawns") = false)
      .def_property_readonly("num_envs", &catamaze::training::NativeBatch::size)
      .def("reset", &catamaze::training::NativeBatch::reset, py::arg("seeds"))
      .def("reset_at", &catamaze::training::NativeBatch::resetAt, py::arg("indices"),
           py::arg("seeds"))
      .def("step", &catamaze::training::NativeBatch::step, py::arg("player_actions"),
           py::arg("ai_actions"))
      .def("snapshot", &catamaze::training::NativeBatch::snapshot)
      .def("save_state", &catamaze::training::NativeBatch::saveState)
      .def("load_state", &catamaze::training::NativeBatch::loadState, py::arg("states"));
}
