// Created at: 2026-11-14 02:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:58 EST
// Last Modified by: Codex
// Declares a fixed SSD1306 page-order framebuffer and bounds-safe drawing primitives.

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string_view>

namespace catamaze::render {

class Framebuffer {
 public:
  static constexpr std::int16_t kWidth = 128;
  static constexpr std::int16_t kHeight = 64;
  static constexpr std::size_t kByteCount = 1024;

  void clear(bool on = false) noexcept;
  void setPixel(std::int16_t x, std::int16_t y, bool on = true) noexcept;
  bool pixel(std::int16_t x, std::int16_t y) const noexcept;
  void fillRect(std::int16_t x, std::int16_t y, std::int16_t width, std::int16_t height,
                bool on = true) noexcept;
  void drawRect(std::int16_t x, std::int16_t y, std::int16_t width, std::int16_t height,
                bool on = true) noexcept;
  void drawChar(std::int16_t x, std::int16_t y, char character, bool on = true) noexcept;
  void drawText(std::int16_t x, std::int16_t y, std::string_view text, bool on = true) noexcept;

  const std::array<std::uint8_t, kByteCount>& bytes() const noexcept { return bytes_; }

 private:
  std::array<std::uint8_t, kByteCount> bytes_{};
};

}  // namespace catamaze::render
