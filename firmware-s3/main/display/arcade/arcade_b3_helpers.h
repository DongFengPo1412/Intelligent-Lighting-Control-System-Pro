#pragma once
#include "arcade_batch_cartridge.h"
namespace arcade {
inline double B3Quantize(double v) { return std::floor(v * 1000000.0 + .5) / 1000000.0; }
inline float B3Clamp(float v, float lo, float hi) { return std::max(lo, std::min(hi, v)); }
inline float B3Wrap(float a) {
    while (a < 0)
        a += 6.28318530718f;
    while (a >= 6.28318530718f)
        a -= 6.28318530718f;
    return a;
}
inline float B3AngleDistance(float a, float b) {
    return std::abs(std::remainder(a - b, 6.28318530718f));
}
inline uint32_t B3Random(uint32_t &seed) {
    seed = seed * 1664525u + 1013904223u;
    return seed;
}
inline void B3Pixel(uint8_t *fb, int x, int y, int r, int g, int b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int i = (y * 16 + x) * 3;
        fb[i] = r;
        fb[i + 1] = g;
        fb[i + 2] = b;
    }
}
inline void B3Line(uint8_t *fb, int x0, int y0, int x1, int y1, int r, int g, int b) {
    int dx = std::abs(x1 - x0), sx = x0 < x1 ? 1 : -1, dy = -std::abs(y1 - y0),
        sy = y0 < y1 ? 1 : -1, err = dx + dy;
    for (;;) {
        B3Pixel(fb, x0, y0, r, g, b);
        if (x0 == x1 && y0 == y1)
            break;
        int e = 2 * err;
        if (e >= dy) {
            err += dy;
            x0 += sx;
        }
        if (e <= dx) {
            err += dx;
            y0 += sy;
        }
    }
}
inline void B3Disc(uint8_t *fb, float x, float y, float radius, int r, int g, int b) {
    for (int yy = 0; yy < 16; ++yy)
        for (int xx = 0; xx < 16; ++xx)
            if ((xx - x) * (xx - x) + (yy - y) * (yy - y) <= radius * radius)
                B3Pixel(fb, xx, yy, r, g, b);
}
} // namespace arcade

namespace arcade {
inline int B3BowlingTotal(const int *rolls, int nroll) {
    int score = 0, i = 0;
    for (int f = 0; f < 10 && i < nroll; ++f) {
        int a = rolls[i];
        if (a == 10) {
            for (int j = i; j < std::min(nroll, i + 3); ++j)
                score += rolls[j];
            ++i;
        } else if (i + 1 < nroll) {
            int b = rolls[i + 1];
            score += a + b;
            if (a + b == 10 && i + 2 < nroll)
                score += rolls[i + 2];
            i += 2;
        } else {
            score += a;
            break;
        }
    }
    return score;
}
} // namespace arcade
