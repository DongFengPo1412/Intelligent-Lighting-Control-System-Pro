// Compile with C++14 or newer (-fsyntax-only is sufficient).
#include "../firmware-s3/main/display/matrix_layout.h"

constexpr bool TestEntirePanel() {
    bool visited[256] = {};
    int physical = 0;
    // Follow the declared wire path independently of PixelIndex's formula.
    for (int y = 0; y < 16; ++y) {
        for (int step = 0; step < 16; ++step) {
            int x = (y % 2 == 0) ? step : 15 - step;
            int index = MatrixLayout::PixelIndex(x, y);
            if (index != physical++ || index < 0 || index >= 256 || visited[index]) return false;
            visited[index] = true;
        }
    }
    for (bool pixel : visited) if (!pixel) return false;
    return true;
}

static_assert(MatrixLayout::kPixelCount == 256, "Panel must contain 256 LEDs");
static_assert(TestEntirePanel(), "Wire path must visit every pixel exactly once in order");
static_assert(MatrixLayout::PixelIndex(0, 0) == 0, "Top-left DIN");
static_assert(MatrixLayout::PixelIndex(15, 0) == 15, "First row ends at right");
static_assert(MatrixLayout::PixelIndex(15, 1) == 16, "Second row starts at right");
static_assert(MatrixLayout::PixelIndex(0, 1) == 31, "Second row ends at left");
static_assert(MatrixLayout::PixelIndex(15, 15) == 240, "Last row starts at right");
static_assert(MatrixLayout::PixelIndex(0, 15) == 255, "Last LED is bottom-left");
static_assert(MatrixLayout::PixelIndex(-1, 0) == -1, "Reject negative x");
static_assert(MatrixLayout::PixelIndex(0, -1) == -1, "Reject negative y");
static_assert(MatrixLayout::PixelIndex(16, 0) == -1, "Reject x overflow");
static_assert(MatrixLayout::PixelIndex(0, 16) == -1, "Reject y overflow");
