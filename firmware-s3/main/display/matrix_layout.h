#pragma once

// One 16x16 panel, viewed from the front, with DIN at the top-left.
// The current board was optically verified as left-to-right on every row.
// Set PRO_MATRIX_SERPENTINE=1 for panels whose odd rows run right-to-left.
#ifndef PRO_MATRIX_SERPENTINE
#define PRO_MATRIX_SERPENTINE 0
#endif
namespace MatrixLayout {
constexpr int kWidth = 16;
constexpr int kHeight = 16;
constexpr int kPixelCount = kWidth * kHeight;

constexpr bool kSerpentine = PRO_MATRIX_SERPENTINE != 0;

constexpr int PixelIndexForWiring(int x, int y, bool serpentine) {
    return (x < 0 || x >= kWidth || y < 0 || y >= kHeight)
        ? -1
        : y * kWidth + ((serpentine && (y & 1)) ? kWidth - 1 - x : x);
}

constexpr int PixelIndex(int x, int y) {
    return PixelIndexForWiring(x, y, kSerpentine);
}
}  // namespace MatrixLayout
