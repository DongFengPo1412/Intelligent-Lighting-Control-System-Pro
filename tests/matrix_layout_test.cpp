// Compile with C++14 or newer (-fsyntax-only is sufficient).
#include "../firmware-s3/main/display/matrix_layout.h"

constexpr bool TestEntirePanel(bool serpentine) {
    bool visited[256] = {};
    int physical = 0;
    // Follow the declared wire path independently of PixelIndex's formula.
    for (int y = 0; y < 16; ++y) {
        for (int step = 0; step < 16; ++step) {
            int x = (serpentine && y % 2 != 0) ? 15 - step : step;
            int index = MatrixLayout::PixelIndexForWiring(x, y, serpentine);
            if (index != physical++ || index < 0 || index >= 256 || visited[index]) return false;
            visited[index] = true;
        }
    }
    for (bool pixel : visited) if (!pixel) return false;
    return true;
}

static_assert(MatrixLayout::kPixelCount == 256, "Panel must contain 256 LEDs");
static_assert(TestEntirePanel(false), "Straight rows must visit every pixel in wire order");
static_assert(TestEntirePanel(true), "Serpentine rows must visit every pixel in wire order");
static_assert(MatrixLayout::PixelIndex(0, 0) == 0, "Top-left DIN");
static_assert(MatrixLayout::PixelIndex(15, 0) == 15, "First row ends at right");
static_assert(MatrixLayout::PixelIndex(0, 1) == (MatrixLayout::kSerpentine ? 31 : 16), "Selected second row start");
static_assert(MatrixLayout::PixelIndex(15, 15) == (MatrixLayout::kSerpentine ? 240 : 255), "Selected bottom-right");
static_assert(MatrixLayout::PixelIndexForWiring(15, 1, true) == 16, "Serpentine second row starts at right");
static_assert(MatrixLayout::PixelIndexForWiring(0, 15, true) == 255, "Serpentine last LED is bottom-left");
static_assert(MatrixLayout::PixelIndex(-1, 0) == -1, "Reject negative x");
static_assert(MatrixLayout::PixelIndex(0, -1) == -1, "Reject negative y");
static_assert(MatrixLayout::PixelIndex(16, 0) == -1, "Reject x overflow");
static_assert(MatrixLayout::PixelIndex(0, 16) == -1, "Reject y overflow");
