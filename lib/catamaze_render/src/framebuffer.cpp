// Created at: 2026-11-14 02:34 EST
// Created by: Codex
// Last Modified at: 2026-11-14 07:09 EST
// Last Modified by: Codex
// Implements page-order pixel storage and the fixed five-by-seven product font.

#include "catamaze/render/framebuffer.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace catamaze::render {
namespace {

using Glyph = std::array<std::uint8_t, 5>;

Glyph glyphFor(char character) noexcept {
  switch (character) {
    case '0':
      return {0x3e, 0x51, 0x49, 0x45, 0x3e};
    case '1':
      return {0x00, 0x42, 0x7f, 0x40, 0x00};
    case '2':
      return {0x42, 0x61, 0x51, 0x49, 0x46};
    case '3':
      return {0x21, 0x41, 0x45, 0x4b, 0x31};
    case '4':
      return {0x18, 0x14, 0x12, 0x7f, 0x10};
    case '5':
      return {0x27, 0x45, 0x45, 0x45, 0x39};
    case '6':
      return {0x3c, 0x4a, 0x49, 0x49, 0x30};
    case '7':
      return {0x01, 0x71, 0x09, 0x05, 0x03};
    case '8':
      return {0x36, 0x49, 0x49, 0x49, 0x36};
    case '9':
      return {0x06, 0x49, 0x49, 0x29, 0x1e};
    case 'A':
      return {0x7e, 0x11, 0x11, 0x11, 0x7e};
    case 'B':
      return {0x7f, 0x49, 0x49, 0x49, 0x36};
    case 'C':
      return {0x3e, 0x41, 0x41, 0x41, 0x22};
    case 'D':
      return {0x7f, 0x41, 0x41, 0x22, 0x1c};
    case 'E':
      return {0x7f, 0x49, 0x49, 0x49, 0x41};
    case 'F':
      return {0x7f, 0x09, 0x09, 0x09, 0x01};
    case 'G':
      return {0x3e, 0x41, 0x49, 0x49, 0x7a};
    case 'H':
      return {0x7f, 0x08, 0x08, 0x08, 0x7f};
    case 'I':
      return {0x00, 0x41, 0x7f, 0x41, 0x00};
    case 'J':
      return {0x20, 0x40, 0x41, 0x3f, 0x01};
    case 'K':
      return {0x7f, 0x08, 0x14, 0x22, 0x41};
    case 'L':
      return {0x7f, 0x40, 0x40, 0x40, 0x40};
    case 'M':
      return {0x7f, 0x02, 0x0c, 0x02, 0x7f};
    case 'N':
      return {0x7f, 0x04, 0x08, 0x10, 0x7f};
    case 'O':
      return {0x3e, 0x41, 0x41, 0x41, 0x3e};
    case 'P':
      return {0x7f, 0x09, 0x09, 0x09, 0x06};
    case 'Q':
      return {0x3e, 0x41, 0x51, 0x21, 0x5e};
    case 'R':
      return {0x7f, 0x09, 0x19, 0x29, 0x46};
    case 'S':
      return {0x46, 0x49, 0x49, 0x49, 0x31};
    case 'T':
      return {0x01, 0x01, 0x7f, 0x01, 0x01};
    case 'U':
      return {0x3f, 0x40, 0x40, 0x40, 0x3f};
    case 'V':
      return {0x1f, 0x20, 0x40, 0x20, 0x1f};
    case 'W':
      return {0x3f, 0x40, 0x38, 0x40, 0x3f};
    case 'X':
      return {0x63, 0x14, 0x08, 0x14, 0x63};
    case 'Y':
      return {0x07, 0x08, 0x70, 0x08, 0x07};
    case 'Z':
      return {0x61, 0x51, 0x49, 0x45, 0x43};
    case '/':
      return {0x20, 0x10, 0x08, 0x04, 0x02};
    case ',':
      return {0x00, 0x50, 0x30, 0x00, 0x00};
    case '-':
      return {0x08, 0x08, 0x08, 0x08, 0x08};
    case ':':
      return {0x00, 0x36, 0x36, 0x00, 0x00};
    case '.':
      return {0x00, 0x60, 0x60, 0x00, 0x00};
    case '>':
      return {0x00, 0x41, 0x22, 0x14, 0x08};
    case '<':
      return {0x08, 0x14, 0x22, 0x41, 0x00};
    case ' ':
      return {0x00, 0x00, 0x00, 0x00, 0x00};
    default:
      return {0x02, 0x01, 0x51, 0x09, 0x06};
  }
}

}  // namespace

void Framebuffer::clear(bool on) noexcept { bytes_.fill(on ? 0xffU : 0x00U); }

void Framebuffer::setPixel(std::int16_t x, std::int16_t y, bool on) noexcept {
  if (x < 0 || x >= kWidth || y < 0 || y >= kHeight) {
    return;
  }
  const std::size_t index = static_cast<std::size_t>(x) + static_cast<std::size_t>(y / 8) * kWidth;
  const std::uint8_t mask = static_cast<std::uint8_t>(1U << (y & 7));
  if (on) {
    bytes_[index] = static_cast<std::uint8_t>(bytes_[index] | mask);
  } else {
    bytes_[index] = static_cast<std::uint8_t>(bytes_[index] & ~mask);
  }
}

bool Framebuffer::pixel(std::int16_t x, std::int16_t y) const noexcept {
  if (x < 0 || x >= kWidth || y < 0 || y >= kHeight) {
    return false;
  }
  const std::size_t index = static_cast<std::size_t>(x) + static_cast<std::size_t>(y / 8) * kWidth;
  return (bytes_[index] & static_cast<std::uint8_t>(1U << (y & 7))) != 0U;
}

void Framebuffer::fillRect(std::int16_t x, std::int16_t y, std::int16_t width, std::int16_t height,
                           bool on) noexcept {
  for (std::int16_t row = 0; row < height; ++row) {
    for (std::int16_t column = 0; column < width; ++column) {
      setPixel(static_cast<std::int16_t>(x + column), static_cast<std::int16_t>(y + row), on);
    }
  }
}

void Framebuffer::drawRect(std::int16_t x, std::int16_t y, std::int16_t width, std::int16_t height,
                           bool on) noexcept {
  if (width <= 0 || height <= 0) {
    return;
  }
  fillRect(x, y, width, 1, on);
  fillRect(x, static_cast<std::int16_t>(y + height - 1), width, 1, on);
  fillRect(x, y, 1, height, on);
  fillRect(static_cast<std::int16_t>(x + width - 1), y, 1, height, on);
}

void Framebuffer::drawChar(std::int16_t x, std::int16_t y, char character, bool on) noexcept {
  const Glyph glyph = glyphFor(character);
  for (std::size_t column = 0; column < glyph.size(); ++column) {
    for (std::uint8_t row = 0; row < 7U; ++row) {
      if ((glyph[column] & static_cast<std::uint8_t>(1U << row)) != 0U) {
        setPixel(static_cast<std::int16_t>(x + column), static_cast<std::int16_t>(y + row), on);
      }
    }
  }
}

void Framebuffer::drawText(std::int16_t x, std::int16_t y, std::string_view text,
                           bool on) noexcept {
  for (char character : text) {
    drawChar(x, y, character, on);
    x = static_cast<std::int16_t>(x + 6);
  }
}

}  // namespace catamaze::render
