#include "game_011_dino_runner.h"
namespace arcade {

void Game011DinoRunner::Setup() {
    y = 12;
    vy = distance = 0;
    for (int i = 0; i < 3; ++i)
        ob[i] = 20 + i * 16;
    cleared = 0;
}
void Game011DinoRunner::Tick(float dt, uint16_t, uint16_t pressed) {
    if ((pressed & (KEY_A | KEY_UP)) && y >= 11.999f) {
        vy = -9;
        SoundEvent(Sound::Jump);
    }
    const int g[] = {8, 9, 10}, base[] = {3, 4, 5}, height[] = {1, 2, 3};
    vy += g[difficulty_] * dt;
    y = std::min(12.f, y + vy * dt);
    if (y >= 12)
        vy = 0;
    float speed = std::min(8.0, base[difficulty_] + elapsed_ * .04);
    distance += speed * dt;
    for (int i = 0; i < 3; ++i) {
        ob[i] -= speed * dt;
        if (std::abs(ob[i] - 3) < .85f && y > 12 - height[difficulty_]) {
            SoundEvent(Sound::Collision);
            Finish(false);
            return;
        }
        if (ob[i] < 0) {
            ob[i] += 48;
            ++cleared;
            Award(10);
        }
    }
    if (cleared >= 12) {
        Award(500);
        Finish(true);
    }
}
int Game011DinoRunner::Progress() const { return cleared * 100 / 12; }
void Game011DinoRunner::Draw(uint8_t *fb) {
    B3Line(fb, 0, 13, 15, 13, 60, 100, 65);
    Px(fb, 3, int(std::round(y)), 220, 240, 230);
    Px(fb, 3, int(std::round(y)) - 1, 220, 240, 230);
    for (auto x : ob)
        for (unsigned h = 0; h < difficulty_ + 1; ++h)
            Px(fb, int(std::round(x)), 12 - h, 110, 220, 90);
}

} // namespace arcade
