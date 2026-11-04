#include "game_047_blockudoku.h"
namespace arcade {

void Game047Blockudoku::Setup() {
    board = 0;
    x = y = selected = placed = cleared = 0;
    rack = 7;
}
void Game047Blockudoku::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    x = std::max(0, std::min(5, x + dx));
    y = std::max(0, std::min(5, y + dy));
    auto shape = [](int k, int xx, int yy) {
        uint64_t m = 0;
        int count = k == 2 ? 1 : 3;
        for (int i = 0; i < count; ++i) {
            int nx = xx + (k == 0 ? i : 0), ny = yy + (k == 1 ? i : 0);
            if (nx >= 6 || ny >= 6)
                return uint64_t(0);
            m |= 1ull << (ny * 6 + nx);
        }
        return m;
    };
    if (pressed & KEY_B)
        for (int n = 1; n <= 3; ++n)
            if (rack & (1 << ((selected + n) % 3))) {
                selected = (selected + n) % 3;
                break;
            }
    if (pressed & KEY_A) {
        uint64_t m = shape(selected, x, y);
        if (m && !(m & board)) {
            board |= m;
            ++placed;
            rack &= ~(1 << selected);
            uint64_t remove = 0;
            int count = 0;
            for (int r = 0; r < 6; ++r) {
                uint64_t a = 0, b = 0;
                for (int c = 0; c < 6; ++c) {
                    a |= 1ull << (r * 6 + c);
                    b |= 1ull << (c * 6 + r);
                }
                if ((board & a) == a) {
                    remove |= a;
                    ++count;
                }
                if ((board & b) == b) {
                    remove |= b;
                    ++count;
                }
            }
            for (int by : {0, 3})
                for (int bx : {0, 3}) {
                    uint64_t a = 0;
                    for (int yy = 0; yy < 3; ++yy)
                        for (int xx = 0; xx < 3; ++xx)
                            a |= 1ull << ((by + yy) * 6 + bx + xx);
                    if ((board & a) == a) {
                        remove |= a;
                        ++count;
                    }
                }
            board &= ~remove;
            cleared += count;
            Award(10 + count * 50);
            SoundEvent(count ? Sound::Hit : Sound::Action);
            if (!rack)
                rack = 7;
            if (!(rack & (1 << selected)))
                for (int i = 0; i < 3; ++i)
                    if (rack & (1 << i)) {
                        selected = i;
                        break;
                    }
        }
    }
    bool legal = false;
    for (int k = 0; k < 3; ++k)
        if (rack & (1 << k))
            for (int yy = 0; yy < 6; ++yy)
                for (int xx = 0; xx < 6; ++xx) {
                    uint64_t m = shape(k, xx, yy);
                    if (m && !(m & board))
                        legal = true;
                }
    const int goal[] = {4, 5, 6}, budget[] = {36, 30, 24}, limit[] = {120, 100, 80};
    if (cleared >= goal[difficulty_]) {
        Award(500);
        Finish(true);
    } else if (placed >= budget[difficulty_] || elapsed_ > limit[difficulty_] || !legal)
        Finish(false);
}
int Game047Blockudoku::Progress() const {
    const int goal[] = {4, 5, 6};
    return cleared * 100 / goal[difficulty_];
}
void Game047Blockudoku::Draw(uint8_t *fb) {
    for (int yy = 0; yy < 6; ++yy)
        for (int xx = 0; xx < 6; ++xx)
            if (board & (1ull << (yy * 6 + xx)))
                Cell(fb, xx, yy, 60, 180, 225);
            else
                Cell(fb, xx, yy, 15, 25, 40);
    Px(fb, 2 + x * 2, 2 + y * 2, 255, 255, 255);
    for (int i = 0; i < 3; ++i)
        if (i == selected)
            Px(fb, 3 + i * 4, 0, 255, 210, 50);
        else if (rack & (1 << i))
            Px(fb, 3 + i * 4, 0, 70, 200, 120);
        else
            Px(fb, 3 + i * 4, 0, 25, 25, 30);
}

} // namespace arcade
