#include "game_089_firefighter.h"
namespace arcade {

void Game089Firefighter::Setup() {
    memset(fire, 0, sizeof(fire));
    fire[14] = fire[21] = fire[46] = 2;
    x = 1;
    y = 6;
    face = 0;
    const int n[] = {8, 6, 4};
    water = n[difficulty_];
    burned = extinguished = 0;
    spread = 0;
}
void Game089Firefighter::Tick(float dt, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    if (dx || dy) {
        face = dx > 0 ? 0 : dx < 0 ? 1 : dy > 0 ? 2 : 3;
        x = std::max(0, std::min(7, x + dx));
        y = std::max(0, std::min(7, y + dy));
    }
    const int water_max[] = {8, 6, 4};
    if ((pressed & KEY_B) && x == 1 && y == 6) {
        water = water_max[difficulty_];
        SoundEvent(Sound::Action);
    }
    if ((pressed & KEY_A) && water) {
        --water;
        const int xx[] = {1, -1, 0, 0}, yy[] = {0, 0, 1, -1};
        for (int d = 1; d <= 3; ++d) {
            int nx = x + xx[face] * d, ny = y + yy[face] * d;
            if (nx >= 0 && nx < 8 && ny >= 0 && ny < 8) {
                int p = ny * 8 + nx;
                if (fire[p]) {
                    fire[p] = std::max(0, fire[p] - 2);
                    if (!fire[p])
                        ++extinguished;
                }
            }
        }
        SoundEvent(Sound::Hit);
    }
    spread += std::round(double(dt) * 1000000) / 1000000;
    const double period[] = {1.5, 1., .7};
    if (spread >= period[difficulty_]) {
        spread = 0;
        int old[64];
        memcpy(old, fire, sizeof(old));
        for (int p = 0; p < 64; ++p)
            if (old[p]) {
                fire[p] = std::min(3, fire[p] + 1);
                int n[] = {p % 8 < 7 ? p + 1 : -1, p - 8, p + 8, p % 8 ? p - 1 : -1};
                for (auto q : n)
                    if (q >= 0 && q < 64 && !old[q]) {
                        fire[q] = 1;
                        break;
                    }
            }
    }
    burned = 0;
    for (auto v : fire)
        burned += v > 0;
    const int limit[] = {120, 90, 60};
    if (!burned) {
        Award(1000 + water * 20);
        Finish(true);
    } else if (fire[49] || burned >= 24 || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game089Firefighter::Progress() const { return std::min(100, extinguished * 100 / 3); }
void Game089Firefighter::Draw(uint8_t *fb) {
    for (int p = 0; p < 64; ++p)
        if (fire[p])
            Cell(fb, p % 8, p / 8, 245, 150 - fire[p] * 35, 30, 2, 0);
    Cell(fb, 1, 6, 50, 160, 235, 2, 0);
    Px(fb, x * 2, y * 2, 245, 245, 245);
    for (int i = 0; i < water; ++i)
        Px(fb, i, 15, 70, 180, 245);
}

} // namespace arcade
