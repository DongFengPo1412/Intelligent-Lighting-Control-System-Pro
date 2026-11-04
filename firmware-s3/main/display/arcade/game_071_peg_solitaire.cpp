#include "game_071_peg_solitaire.h"
namespace arcade {

void Game071PegSolitaire::Setup() {
    mask = 32766;
    x = y = dir = moves = 0;
}
void Game071PegSolitaire::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    y = std::max(0, std::min(4, y + dy));
    x = std::max(0, std::min(y, x + dx));
    auto jump = [&](int xx, int yy, int d, bool apply) {
        const int ax[] = {1, -1, 0, 0, 1, -1}, ay[] = {0, 0, 1, -1, 1, -1};
        int mx = xx + ax[d], my = yy + ay[d], tx = xx + 2 * ax[d], ty = yy + 2 * ay[d];
        if (my < 0 || my >= 5 || mx < 0 || mx > my || ty < 0 || ty >= 5 || tx < 0 || tx > ty)
            return false;
        int a = yy * (yy + 1) / 2 + xx, b = my * (my + 1) / 2 + mx, c = ty * (ty + 1) / 2 + tx;
        if (!(mask & (1 << a)) || !(mask & (1 << b)) || (mask & (1 << c)))
            return false;
        if (apply)
            mask ^= (1 << a) | (1 << b) | (1 << c);
        return true;
    };
    if (pressed & KEY_B)
        dir = (dir + 1) % 6;
    if ((pressed & KEY_A) && jump(x, y, dir, true)) {
        ++moves;
        Award(50);
        SoundEvent(Sound::Hit);
    }
    int count = 0;
    bool legal = false;
    for (int p = 0; p < 15; ++p)
        count += (mask >> p) & 1;
    for (int yy = 0; yy < 5; ++yy)
        for (int xx = 0; xx <= yy; ++xx)
            for (int d = 0; d < 6; ++d)
                legal |= jump(xx, yy, d, false);
    const int limit[] = {240, 180, 120};
    if (count == 1) {
        Award(1000);
        Finish(true);
    } else if (!legal || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game071PegSolitaire::Progress() const { return moves * 100 / 13; }
void Game071PegSolitaire::Draw(uint8_t *fb) {
    for (int yy = 0; yy < 5; ++yy)
        for (int xx = 0; xx <= yy; ++xx)
            if (mask & (1 << (yy * (yy + 1) / 2 + xx)))
                Cell(fb, xx, yy, 70, 190, 225);
            else
                Cell(fb, xx, yy, 35, 40, 50);
    Px(fb, 2 + x * 2, 2 + y * 2, 255, 255, 255);
    Px(fb, 2 + dir * 2, 14, 245, 160, 50);
}

} // namespace arcade
