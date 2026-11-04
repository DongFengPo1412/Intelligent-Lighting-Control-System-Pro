#include "game_049_lights_out.h"
namespace arcade {

void Game049LightsOut::Setup() {
    mask = 0;
    x = y = 2;
    moves = 0;
    const int count[] = {5, 9, 13}, pos[] = {0, 6, 12, 18, 24, 2, 10, 14, 22, 4, 8, 16, 20};
    for (int i = 0; i < count[difficulty_]; ++i) {
        int xx = pos[i] % 5, yy = pos[i] / 5;
        const int dx[] = {0, -1, 1, 0, 0}, dy[] = {0, 0, 0, -1, 1};
        for (int d = 0; d < 5; ++d) {
            int nx = xx + dx[d], ny = yy + dy[d];
            if (nx >= 0 && nx < 5 && ny >= 0 && ny < 5)
                mask ^= 1u << (ny * 5 + nx);
        }
    }
}
void Game049LightsOut::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    x = std::max(0, std::min(4, x + dx));
    y = std::max(0, std::min(4, y + dy));
    if (pressed & KEY_A) {
        const int xx[] = {0, -1, 1, 0, 0}, yy[] = {0, 0, 0, -1, 1};
        for (int d = 0; d < 5; ++d) {
            int nx = x + xx[d], ny = y + yy[d];
            if (nx >= 0 && nx < 5 && ny >= 0 && ny < 5)
                mask ^= 1u << (ny * 5 + nx);
        }
        ++moves;
        SoundEvent(Sound::Action);
    }
    const int budget[] = {30, 24, 20}, limit[] = {90, 75, 60};
    if (!mask) {
        Award(1000 + std::max(0, budget[difficulty_] - moves) * 10);
        Finish(true);
    } else if (moves >= budget[difficulty_] || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game049LightsOut::Progress() const {
    int n = 0;
    for (int i = 0; i < 25; ++i)
        if (mask & (1u << i))
            ++n;
    return (25 - n) * 4;
}
void Game049LightsOut::Draw(uint8_t *fb) {
    for (int yy = 0; yy < 5; ++yy)
        for (int xx = 0; xx < 5; ++xx)
            if (mask & (1u << (yy * 5 + xx)))
                Cell(fb, xx, yy, 245, 190, 45, 3, 0);
            else
                Cell(fb, xx, yy, 15, 25, 40, 3, 0);
    Px(fb, x * 3 + 1, y * 3 + 1, 255, 255, 255);
}

} // namespace arcade
