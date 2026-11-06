#pragma once
#include <cstdint>

// Mid main/led/single_led.cc: raw RGB levels and toggle intervals.
namespace mid_led {
constexpr uint8_t kDefault = 4;
constexpr uint8_t kLow = 2;
constexpr uint8_t kHigh = 16;
constexpr bool BlinkOn(uint64_t elapsed_us, unsigned interval_ms) {
    return ((elapsed_us / (uint64_t(interval_ms) * 1000)) & 1u) == 0;
}
}
