#include "game_013_pendulum_toss.h"
namespace arcade {

void Game013PendulumToss::Setup() {
    x = 8;
    y = 6;
    vx = vy = phase = 0;
    flying = false;
    hits = 0;
    const int b[] = {6, 5, 4};
    balls = b[difficulty_];
}
void Game013PendulumToss::Tick(float dt, uint16_t, uint16_t pressed) {
    const float speed[] = {1.3f, 1.7f, 2.1f}, width[] = {2.5f, 2.f, 1.5f};
    const int target[] = {4, 11, 7}, limit[] = {45, 35, 30};
    phase += speed[difficulty_] * dt;
    float angle = .9f * std::sin(phase), omega = .9f * speed[difficulty_] * std::cos(phase);
    if (!flying) {
        x = 8 + 5 * std::sin(angle);
        y = 1 + 5 * std::cos(angle);
        if (pressed & KEY_A) {
            vx = 5 * std::cos(angle) * omega;
            vy = -5 * std::sin(angle) * omega;
            flying = true;
            --balls;
            SoundEvent(Sound::Action);
        }
    } else {
        vy += 5 * dt;
        x += vx * dt;
        y += vy * dt;
        if (y >= 13 || x < 0 || x > 15) {
            bool good = y >= 13 && std::abs(x - target[hits % 3]) < width[difficulty_];
            flying = false;
            if (good) {
                ++hits;
                Award(100);
                SoundEvent(Sound::Hit);
            } else
                SoundEvent(Sound::Collision);
            if (hits >= 3)
                Finish(true);
            else if (balls <= 0)
                Finish(false);
        }
    }
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game013PendulumToss::Progress() const { return hits * 100 / 3; }
void Game013PendulumToss::Draw(uint8_t *fb) {
    if (!flying)
        B3Line(fb, 8, 1, int(std::round(x)), int(std::round(y)), 90, 110, 150);
    Px(fb, int(std::round(x)), int(std::round(y)), 255, 220, 55);
    const int target[] = {4, 11, 7};
    const float width[] = {2.5f, 2.f, 1.5f};
    for (int xx = 0; xx < 16; ++xx)
        if (std::abs(float(xx - target[hits % 3])) < width[difficulty_])
            Px(fb, xx, 14, 40, 220, 130);
    for (int i = 0; i < balls; ++i)
        Px(fb, i + 1, 0, 120, 180, 255);
}

} // namespace arcade
