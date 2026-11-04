#include "game_070_flood_it.h"
namespace arcade {

void Game070FloodIt::Setup() {
    uint32_t seed = 0x70a;
    for (auto &v : board)
        v = (B3Random(seed) >> 16) % 4;
    color = board[0];
    selected = moves = 0;
    flooded = 1;
    count = 0;
    for (int n = 0; n < 36; ++n)
        for (int p = 0; p < 36; ++p)
            if (board[p] == color) {
                int a[] = {p % 6 ? p - 1 : -1, p % 6 < 5 ? p + 1 : -1, p - 6, p + 6};
                for (auto q : a)
                    if (q >= 0 && q < 36 && (flooded & (1ull << q)))
                        flooded |= 1ull << p;
            }
    for (int p = 0; p < 36; ++p)
        count += (flooded >> p) & 1;
}
void Game070FloodIt::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    selected = (selected + dx + 4) % 4;
    if ((pressed & KEY_A) && selected != color) {
        color = selected;
        ++moves;
        for (int n = 0; n < 36; ++n)
            for (int p = 0; p < 36; ++p)
                if (board[p] == color) {
                    int a[] = {p % 6 ? p - 1 : -1, p % 6 < 5 ? p + 1 : -1, p - 6, p + 6};
                    for (auto q : a)
                        if (q >= 0 && q < 36 && (flooded & (1ull << q)))
                            flooded |= 1ull << p;
                }
        count = 0;
        for (int p = 0; p < 36; ++p)
            count += (flooded >> p) & 1;
        Award(5);
        SoundEvent(Sound::Action);
    }
    const int b[] = {20, 16, 12}, limit[] = {120, 100, 80};
    if (count == 36) {
        Award(1500 - moves * 20);
        Finish(true);
    } else if (moves >= b[difficulty_] || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game070FloodIt::Progress() const { return count * 100 / 36; }
void Game070FloodIt::Draw(uint8_t *fb) {
    const int colors[][3] = {{235, 75, 90}, {70, 170, 235}, {80, 220, 110}, {240, 200, 50}};
    for (int y = 0; y < 6; ++y)
        for (int x = 0; x < 6; ++x) {
            int p = y * 6 + x;
            auto c = colors[(flooded & (1ull << p)) ? color : board[p]];
            Cell(fb, x, y, c[0], c[1], c[2]);
        }
    for (int i = 0; i < 4; ++i) {
        auto c = colors[i];
        Px(fb, 2 + i * 3, 0, selected == i ? 255 : c[0], selected == i ? 255 : c[1],
           selected == i ? 255 : c[2]);
    }
}

} // namespace arcade
