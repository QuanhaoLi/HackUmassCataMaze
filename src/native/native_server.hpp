// Created at: 2026-11-14 02:37 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:37 EST
// Last Modified by: Codex
// Declares loopback-only Native server configuration and lifecycle.

#pragma once

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <memory>

namespace catamaze::native {

struct NativeServerOptions {
  std::uint64_t seed{0x000000000134fd5aULL};
  std::uint16_t port{0};
  bool start_paused{false};
  std::chrono::milliseconds tick_interval{1000};
  std::filesystem::path web_root{"web"};
};

class NativeServer {
 public:
  explicit NativeServer(NativeServerOptions options);
  ~NativeServer();

  NativeServer(const NativeServer&) = delete;
  NativeServer& operator=(const NativeServer&) = delete;

  int run();

 private:
  class Impl;
  std::unique_ptr<Impl> impl_;
};

}  // namespace catamaze::native
