// Created at: 2026-11-14 03:43 EST
// Created by: Codex
// Last Modified at: 2026-11-14 03:43 EST
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

class NativeBatch {
 public:
  explicit NativeBatch(const CArray<std::uint64_t>& seeds) { initialize(seeds); }

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
        engines_[static_cast<std::size_t>(env)].reset(input(env));
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
    return result;
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
      engines_.emplace_back(input(env));
    }
  }

  std::vector<GameEngine> engines_;
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
      .def(py::init<const catamaze::training::CArray<std::uint64_t>&>(), py::arg("seeds"))
      .def_property_readonly("num_envs", &catamaze::training::NativeBatch::size)
      .def("reset", &catamaze::training::NativeBatch::reset, py::arg("seeds"))
      .def("step", &catamaze::training::NativeBatch::step, py::arg("player_actions"),
           py::arg("ai_actions"))
      .def("snapshot", &catamaze::training::NativeBatch::snapshot);
}
