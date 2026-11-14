// Created at: 2026-11-14 02:13 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Runs the complete headless Native game without making a web server a core dependency.

#include <atomic>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <thread>
#include <utility>

#include "catamaze/app/application.hpp"
#include "catamaze/core/version.hpp"
#include "native_server.hpp"

namespace {

using catamaze::app::Application;
using catamaze::core::Action;
using catamaze::core::GameStatus;
using catamaze::core::ObservedCell;
using catamaze::core::Terrain;

constexpr std::uint64_t kDefaultSeed = 0x000000000134fd5aULL;
volatile std::sig_atomic_t gStopRequested = 0;

void handleStopSignal(int) { gStopRequested = 1; }

bool parseUnsigned(const std::string& text, std::uint64_t& value) {
  errno = 0;
  char* end = nullptr;
  const unsigned long long parsed = std::strtoull(text.c_str(), &end, 0);
  if (errno != 0 || end == text.c_str() || *end != '\0') {
    return false;
  }
  value = static_cast<std::uint64_t>(parsed);
  return true;
}

char cellGlyph(const ObservedCell& cell, std::size_t center_index) {
  if (!cell.visible) {
    return '?';
  }
  if (center_index == 12U) {
    return '@';
  }
  if (cell.entity >= 0) {
    return 'P';
  }
  if (cell.bullet) {
    return '*';
  }
  switch (cell.terrain) {
    case Terrain::Wall:
      return '#';
    case Terrain::Floor:
      return '.';
    case Terrain::Entrance:
      return 'S';
    case Terrain::Exit:
      return 'E';
  }
  return '?';
}

void printSnapshot(const Application& application) {
  const auto observation = application.playerObservation();
  const auto& state = application.state();
  const auto& player = state.entities[0];
  std::cout << "\nCATAMAZE  " << catamaze::core::toString(state.status) << "  HASH 0x" << std::hex
            << std::setw(16) << std::setfill('0') << application.stateHash() << std::dec
            << std::setfill(' ') << '\n'
            << "TICK   " << state.tick << '/' << catamaze::core::kMaxTicks << '\n'
            << "HP     " << static_cast<int>(player.hp) << '/'
            << static_cast<int>(catamaze::core::kMaxHp) << '\n'
            << "AMMO   " << static_cast<int>(player.ammo) << '/'
            << static_cast<int>(catamaze::core::kMaxAmmo) << '\n'
            << "QUEUE  " << state.player_queue.size() << '/' << state.player_queue.capacity()
            << '\n'
            << "POS    " << player.position.x << ',' << player.position.y << '\n';
  for (std::size_t y = 0; y < 5U; ++y) {
    for (std::size_t x = 0; x < 5U; ++x) {
      const std::size_t index = y * 5U + x;
      std::cout << cellGlyph(observation.cells[index], index) << ' ';
    }
    std::cout << '\n';
  }
}

bool commandAction(const std::string& command, Action& action) {
  if (command == "u" || command == "up") {
    action = Action::MoveUp;
  } else if (command == "d" || command == "down") {
    action = Action::MoveDown;
  } else if (command == "l" || command == "left") {
    action = Action::MoveLeft;
  } else if (command == "r" || command == "right") {
    action = Action::MoveRight;
  } else if (command == "fu" || command == "fire-up") {
    action = Action::ShootUp;
  } else if (command == "fd" || command == "fire-down") {
    action = Action::ShootDown;
  } else if (command == "fl" || command == "fire-left") {
    action = Action::ShootLeft;
  } else if (command == "fr" || command == "fire-right") {
    action = Action::ShootRight;
  } else if (command == "w" || command == "wait") {
    action = Action::Wait;
  } else {
    return false;
  }
  return true;
}

void printHelp() {
  std::cout << "Commands: u/d/l/r move, fu/fd/fl/fr shoot, w wait, clear, tick,\n"
            << "          run <ticks>, reset <seed>, help, quit\n";
}

int interactive(std::uint64_t seed) {
  Application application(seed);
  std::cout << catamaze::core::kProductName << " Native " << catamaze::core::kCoreVersion << " ("
            << catamaze::core::kRulesVersion << ")\n";
  printHelp();
  printSnapshot(application);

  std::string line;
  while (application.state().status == GameStatus::Running && std::cout << "catamaze> " &&
         std::getline(std::cin, line)) {
    std::istringstream input(line);
    std::string command;
    input >> command;
    if (command.empty()) {
      continue;
    }
    if (command == "quit" || command == "q") {
      return 0;
    }
    if (command == "help" || command == "h") {
      printHelp();
      continue;
    }
    if (command == "clear" || command == "c") {
      application.clearPlayerQueue();
      printSnapshot(application);
      continue;
    }
    if (command == "tick" || command == "t") {
      application.tick();
      printSnapshot(application);
      continue;
    }
    if (command == "run") {
      std::uint64_t ticks = 0;
      std::string count;
      input >> count;
      if (!parseUnsigned(count, ticks) || ticks > catamaze::core::kMaxTicks) {
        std::cerr << "run requires a tick count from 0 to 2000\n";
        continue;
      }
      for (std::uint64_t index = 0;
           index < ticks && application.state().status == GameStatus::Running; ++index) {
        application.tick();
      }
      printSnapshot(application);
      continue;
    }
    if (command == "reset") {
      std::string seed_text;
      std::uint64_t next_seed = 0;
      input >> seed_text;
      if (!parseUnsigned(seed_text, next_seed)) {
        std::cerr << "reset requires a decimal or 0x-prefixed seed\n";
        continue;
      }
      application.reset(next_seed);
      printSnapshot(application);
      continue;
    }

    Action action = Action::Wait;
    if (!commandAction(command, action)) {
      std::cerr << "unknown command: " << command << '\n';
      continue;
    }
    if (!application.enqueuePlayerAction(action)) {
      std::cerr << "input rejected: queue full or game ended\n";
    }
    printSnapshot(application);
  }
  printSnapshot(application);
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  std::uint64_t seed = kDefaultSeed;
  std::uint64_t auto_ticks = 0U;
  std::uint64_t port_value = 0U;
  bool serve = false;
  bool paused = false;
  std::string web_root = "web";
  for (int index = 1; index < argc; ++index) {
    const std::string option = argv[index];
    if ((option == "--seed" || option == "--auto" || option == "--port" ||
         option == "--web-root") &&
        index + 1 >= argc) {
      std::cerr << option << " requires a value\n";
      return 2;
    }
    if (option == "--seed") {
      if (!parseUnsigned(argv[++index], seed)) {
        std::cerr << "invalid seed\n";
        return 2;
      }
    } else if (option == "--auto") {
      if (!parseUnsigned(argv[++index], auto_ticks) || auto_ticks > catamaze::core::kMaxTicks) {
        std::cerr << "invalid auto tick count\n";
        return 2;
      }
    } else if (option == "--serve") {
      serve = true;
    } else if (option == "--paused") {
      paused = true;
    } else if (option == "--port") {
      if (!parseUnsigned(argv[++index], port_value) || port_value > 65535U) {
        std::cerr << "invalid TCP port\n";
        return 2;
      }
    } else if (option == "--web-root") {
      web_root = argv[++index];
    } else {
      std::cerr << "unknown option: " << option << '\n';
      return 2;
    }
  }

  if (serve) {
    if (auto_ticks != 0U) {
      std::cerr << "--serve and --auto cannot be combined\n";
      return 2;
    }
    catamaze::native::NativeServerOptions options;
    options.seed = seed;
    options.port = static_cast<std::uint16_t>(port_value);
    options.start_paused = paused;
    options.web_root = web_root;
    try {
      catamaze::native::NativeServer server(std::move(options));
      gStopRequested = 0;
      std::signal(SIGINT, handleStopSignal);
      std::signal(SIGTERM, handleStopSignal);
      std::atomic<bool> server_finished{false};
      std::thread stop_watcher([&server, &server_finished] {
        while (!server_finished.load() && gStopRequested == 0) {
          std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
        if (gStopRequested != 0) server.requestStop();
      });
      const int result = server.run();
      server_finished.store(true);
      stop_watcher.join();
      return gStopRequested != 0 ? 0 : result;
    } catch (const std::exception& error) {
      std::cerr << "Native server failed: " << error.what() << '\n';
      return 1;
    }
  }

  if (auto_ticks == 0U) {
    return interactive(seed);
  }
  Application application(seed);
  for (std::uint64_t tick = 0;
       tick < auto_ticks && application.state().status == GameStatus::Running; ++tick) {
    application.tick();
  }
  std::cout << "CATAMAZE_HEADLESS_OK tick=" << application.state().tick
            << " status=" << catamaze::core::toString(application.state().status) << " hash=0x"
            << std::hex << application.stateHash() << std::dec << '\n';
  return 0;
}
