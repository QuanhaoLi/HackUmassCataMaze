// Created at: 2026-11-14 02:37 EST
// Created by: Codex
// Last Modified at: 2026-11-14 04:37 EST
// Last Modified by: Codex
// Implements a bounded-command Native adapter with one simulation owner and immutable snapshots.

#include "native_server.hpp"

#include <httplib.h>

#include <array>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <nlohmann/json.hpp>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>

#include "catamaze/app/application.hpp"
#include "catamaze/app/audio_event.hpp"
#include "catamaze/core/version.hpp"
#include "catamaze/render/renderer.hpp"

namespace catamaze::native {
namespace {

using Json = nlohmann::json;

enum class CommandType : std::uint8_t {
  Action,
  Clear,
  Reset,
  Pause,
  Realtime,
  Step,
};

struct Command {
  CommandType type{CommandType::Action};
  core::Action action{core::Action::Wait};
  std::uint64_t seed{0};
};

std::string readAsset(const std::filesystem::path& root, std::string_view name) {
  const std::filesystem::path path = root / std::string(name);
  std::ifstream input(path, std::ios::binary);
  if (!input) {
    throw std::runtime_error("unable to read browser asset: " + path.string());
  }
  std::ostringstream content;
  content << input.rdbuf();
  return content.str();
}

std::string hex64(std::uint64_t value) {
  std::ostringstream output;
  output << "0x" << std::hex << std::setw(16) << std::setfill('0') << value;
  return output.str();
}

std::string frameHex(const render::Framebuffer& frame) {
  static constexpr char kHex[] = "0123456789abcdef";
  std::string encoded;
  encoded.resize(render::Framebuffer::kByteCount * 2U);
  std::size_t output = 0U;
  for (std::uint8_t byte : frame.bytes()) {
    encoded[output++] = kHex[(byte >> 4U) & 0x0fU];
    encoded[output++] = kHex[byte & 0x0fU];
  }
  return encoded;
}

bool parseSeed(const Json& body, std::uint64_t& seed) {
  if (!body.is_object() || !body.contains("seed") || !body["seed"].is_string()) {
    return false;
  }
  const std::string text = body["seed"].get<std::string>();
  errno = 0;
  char* end = nullptr;
  const unsigned long long value = std::strtoull(text.c_str(), &end, 0);
  if (errno != 0 || end == text.c_str() || *end != '\0') {
    return false;
  }
  seed = static_cast<std::uint64_t>(value);
  return true;
}

bool parseAction(std::string_view value, core::Action& action, bool& clear) {
  clear = false;
  if (value == "MOVE_UP")
    action = core::Action::MoveUp;
  else if (value == "MOVE_DOWN")
    action = core::Action::MoveDown;
  else if (value == "MOVE_LEFT")
    action = core::Action::MoveLeft;
  else if (value == "MOVE_RIGHT")
    action = core::Action::MoveRight;
  else if (value == "SHOOT_UP")
    action = core::Action::ShootUp;
  else if (value == "SHOOT_DOWN")
    action = core::Action::ShootDown;
  else if (value == "SHOOT_LEFT")
    action = core::Action::ShootLeft;
  else if (value == "SHOOT_RIGHT")
    action = core::Action::ShootRight;
  else if (value == "WAIT")
    action = core::Action::Wait;
  else if (value == "CLEAR")
    clear = true;
  else
    return false;
  return true;
}

void securityHeaders(httplib::Response& response) {
  response.set_header("Cache-Control", "no-store");
  response.set_header("X-Content-Type-Options", "nosniff");
  response.set_header("X-Frame-Options", "DENY");
  response.set_header("Content-Security-Policy",
                      "default-src 'self'; script-src 'self'; style-src 'self'; "
                      "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'");
}

void jsonError(httplib::Response& response, int status, std::string_view code,
               std::string_view message) {
  response.status = status;
  response.set_content(Json{{"error", std::string(code)}, {"message", std::string(message)}}.dump(),
                       "application/json; charset=utf-8");
}

bool isJsonRequest(const httplib::Request& request) {
  const std::string content_type = request.get_header_value("Content-Type");
  return content_type.rfind("application/json", 0U) == 0U;
}

bool parseJsonBody(const httplib::Request& request, httplib::Response& response, Json& body) {
  if (!isJsonRequest(request)) {
    jsonError(response, 415, "UNSUPPORTED_MEDIA_TYPE", "Content-Type must be application/json");
    return false;
  }
  body = Json::parse(request.body, nullptr, false);
  if (body.is_discarded() || !body.is_object()) {
    jsonError(response, 400, "INVALID_JSON", "Request body must be a JSON object");
    return false;
  }
  return true;
}

Json playerObservableEvents(const core::WorldState& state) {
  Json events = Json::array();
  const app::AudioEvent event = app::selectAudioEvent(state);
  if (event != app::AudioEvent::None) {
    events.push_back({{"type", std::string(app::audioEventName(event))}});
  }
  return events;
}

}  // namespace

class NativeServer::Impl {
 public:
  explicit Impl(NativeServerOptions options)
      : options_(std::move(options)),
        application_(options_.seed),
        realtime_(!options_.start_paused),
        index_html_(readAsset(options_.web_root, "index.html")),
        app_css_(readAsset(options_.web_root, "app.css")),
        app_js_(readAsset(options_.web_root, "app.js")) {
    publishSnapshot();
    configureRoutes();
  }

  ~Impl() { stopSimulation(); }

  int run() {
    startSimulation();
    int selected_port = -1;
    if (options_.port == 0U) {
      selected_port = server_.bind_to_any_port("127.0.0.1");
    } else if (server_.bind_to_port("127.0.0.1", options_.port)) {
      selected_port = options_.port;
    }
    if (selected_port <= 0) {
      std::cerr << "failed to bind Native server on 127.0.0.1\n";
      stopSimulation();
      return 1;
    }
    std::cout << "CATAMAZE_URL=http://127.0.0.1:" << selected_port << '\n' << std::flush;
    const bool served = server_.listen_after_bind();
    stopSimulation();
    return served ? 0 : 1;
  }

  void requestStop() { server_.stop(); }

 private:
  static constexpr std::size_t kCommandCapacity = 128U;

  bool enqueue(Command command) {
    std::lock_guard<std::mutex> lock(command_mutex_);
    if (!running_.load() || command_size_ == commands_.size()) {
      return false;
    }
    const std::size_t tail = (command_head_ + command_size_) % commands_.size();
    commands_[tail] = command;
    ++command_size_;
    command_ready_.notify_one();
    return true;
  }

  bool popCommand(Command& command) {
    std::lock_guard<std::mutex> lock(command_mutex_);
    if (command_size_ == 0U) {
      return false;
    }
    command = commands_[command_head_];
    command_head_ = (command_head_ + 1U) % commands_.size();
    --command_size_;
    return true;
  }

  void startSimulation() {
    running_.store(true);
    simulation_thread_ = std::thread([this] { simulationLoop(); });
  }

  void stopSimulation() {
    if (!running_.exchange(false)) {
      return;
    }
    command_ready_.notify_all();
    server_.stop();
    if (simulation_thread_.joinable()) {
      simulation_thread_.join();
    }
  }

  void simulationLoop() {
    auto next_tick = std::chrono::steady_clock::now() + options_.tick_interval;
    while (running_.load()) {
      {
        std::unique_lock<std::mutex> lock(command_mutex_);
        if (realtime_) {
          command_ready_.wait_until(lock, next_tick,
                                    [this] { return !running_.load() || command_size_ > 0U; });
        } else {
          command_ready_.wait(lock, [this] { return !running_.load() || command_size_ > 0U; });
        }
      }
      if (!running_.load()) {
        break;
      }

      bool changed = false;
      Command command{};
      while (popCommand(command)) {
        switch (command.type) {
          case CommandType::Action:
            application_.enqueuePlayerAction(command.action);
            changed = true;
            break;
          case CommandType::Clear:
            application_.clearPlayerQueue();
            changed = true;
            break;
          case CommandType::Reset:
            application_.reset(command.seed);
            next_tick = std::chrono::steady_clock::now() + options_.tick_interval;
            changed = true;
            break;
          case CommandType::Pause:
            realtime_ = false;
            changed = true;
            break;
          case CommandType::Realtime:
            realtime_ = true;
            next_tick = std::chrono::steady_clock::now() + options_.tick_interval;
            changed = true;
            break;
          case CommandType::Step:
            if (!realtime_) {
              application_.tick();
              changed = true;
            }
            break;
        }
      }

      const auto now = std::chrono::steady_clock::now();
      if (realtime_ && now >= next_tick) {
        application_.tick();
        next_tick += options_.tick_interval;
        if (next_tick <= now) {
          next_tick = now + options_.tick_interval;
        }
        changed = true;
      }
      if (changed) {
        publishSnapshot();
      }
    }
  }

  void publishSnapshot() {
    const auto map_frame = render::Renderer::mapScreen(application_.playerObservation());
    const auto hud_frame = render::Renderer::hudScreen(application_.state());
    const auto& state = application_.state();
    const auto& player = state.entities[core::entityIndex(core::EntityId::Player)];
    Json snapshot{{"schema", "catamaze.snapshot.v1"},
                  {"rules", std::string(core::kRulesVersion)},
                  {"seed", hex64(state.seed)},
                  {"state_hash", hex64(application_.stateHash())},
                  {"status", std::string(core::toString(state.status))},
                  {"tick", state.tick},
                  {"player",
                   {{"hp", player.hp},
                    {"ammo", player.ammo},
                    {"queue", state.player_queue.size()},
                    {"x", player.position.x},
                    {"y", player.position.y}}},
                  {"map_frame_hex", frameHex(map_frame)},
                  {"hud_frame_hex", frameHex(hud_frame)},
                  {"last_events", playerObservableEvents(state)}};
    std::lock_guard<std::mutex> lock(snapshot_mutex_);
    snapshot_json_ = snapshot.dump();
  }

  void configureRoutes() {
    server_.set_payload_max_length(4096U);
    server_.set_read_timeout(std::chrono::seconds(5));
    server_.set_write_timeout(std::chrono::seconds(5));
    server_.set_post_routing_handler(
        [](const httplib::Request&, httplib::Response& response) { securityHeaders(response); });

    server_.Get("/", [this](const httplib::Request&, httplib::Response& response) {
      response.set_content(index_html_, "text/html; charset=utf-8");
    });
    server_.Get("/app.css", [this](const httplib::Request&, httplib::Response& response) {
      response.set_content(app_css_, "text/css; charset=utf-8");
    });
    server_.Get("/app.js", [this](const httplib::Request&, httplib::Response& response) {
      response.set_content(app_js_, "text/javascript; charset=utf-8");
    });
    server_.Get("/health", [](const httplib::Request&, httplib::Response& response) {
      response.set_content(Json{{"status", "ok"},
                                {"product", std::string(core::kProductName)},
                                {"core_version", std::string(core::kCoreVersion)},
                                {"rules", std::string(core::kRulesVersion)}}
                               .dump(),
                           "application/json; charset=utf-8");
    });
    server_.Get("/api/v1/snapshot", [this](const httplib::Request&, httplib::Response& response) {
      std::lock_guard<std::mutex> lock(snapshot_mutex_);
      response.set_content(snapshot_json_, "application/json; charset=utf-8");
    });

    server_.Post(
        "/api/v1/action", [this](const httplib::Request& request, httplib::Response& response) {
          Json body;
          if (!parseJsonBody(request, response, body)) return;
          if (!body.contains("action") || !body["action"].is_string()) {
            jsonError(response, 400, "INVALID_ACTION", "action must be a supported string");
            return;
          }
          core::Action action = core::Action::Wait;
          bool clear = false;
          if (!parseAction(body["action"].get<std::string>(), action, clear)) {
            jsonError(response, 400, "INVALID_ACTION", "unknown action value");
            return;
          }
          const Command command{clear ? CommandType::Clear : CommandType::Action, action, 0U};
          if (!enqueue(command)) {
            jsonError(response, 409, "COMMAND_QUEUE_FULL", "Native command queue is full");
            return;
          }
          response.status = 202;
          response.set_content("{\"accepted\":true}", "application/json; charset=utf-8");
        });

    server_.Post("/api/v1/reset", [this](const httplib::Request& request,
                                         httplib::Response& response) {
      Json body;
      if (!parseJsonBody(request, response, body)) return;
      std::uint64_t seed = 0U;
      if (!parseSeed(body, seed)) {
        jsonError(response, 400, "INVALID_SEED", "seed must be a decimal or 0x-prefixed string");
        return;
      }
      if (!enqueue(Command{CommandType::Reset, core::Action::Wait, seed})) {
        jsonError(response, 409, "COMMAND_QUEUE_FULL", "Native command queue is full");
        return;
      }
      response.status = 202;
      response.set_content("{\"accepted\":true}", "application/json; charset=utf-8");
    });

    server_.Post(
        "/api/v1/clock", [this](const httplib::Request& request, httplib::Response& response) {
          Json body;
          if (!parseJsonBody(request, response, body)) return;
          CommandType type = CommandType::Pause;
          if (body.contains("mode") && body["mode"] == "PAUSED") {
            type = CommandType::Pause;
          } else if (body.contains("mode") && body["mode"] == "REALTIME") {
            type = CommandType::Realtime;
          } else if (body.contains("command") && body["command"] == "STEP") {
            type = CommandType::Step;
          } else {
            jsonError(response, 400, "INVALID_CLOCK_COMMAND", "use PAUSED, REALTIME, or STEP");
            return;
          }
          if (!enqueue(Command{type, core::Action::Wait, 0U})) {
            jsonError(response, 409, "COMMAND_QUEUE_FULL", "Native command queue is full");
            return;
          }
          response.status = 202;
          response.set_content("{\"accepted\":true}", "application/json; charset=utf-8");
        });
  }

  NativeServerOptions options_;
  app::Application application_;
  std::atomic<bool> running_{false};
  bool realtime_{true};
  std::array<Command, kCommandCapacity> commands_{};
  std::size_t command_head_{0U};
  std::size_t command_size_{0U};
  std::mutex command_mutex_;
  std::condition_variable command_ready_;
  std::thread simulation_thread_;
  std::mutex snapshot_mutex_;
  std::string snapshot_json_;
  std::string index_html_;
  std::string app_css_;
  std::string app_js_;
  httplib::Server server_;
};

NativeServer::NativeServer(NativeServerOptions options)
    : impl_(std::make_unique<Impl>(std::move(options))) {}

NativeServer::~NativeServer() = default;

int NativeServer::run() { return impl_->run(); }

void NativeServer::requestStop() { impl_->requestStop(); }

}  // namespace catamaze::native
