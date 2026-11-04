#include "game_023_air_hockey.h"
namespace arcade {

void Game023AirHockey::Setup() {
    paddle_x = 8;
    paddle_y = 13;
    ax = 8;
    x = y = 8;
    vx = 1;
    vy = 3;
    cooldown = 0;
    goals = against = 0;
}
void Game023AirHockey::Tick(float dt, uint16_t down, uint16_t pressed) {
    unsigned keys = down | pressed;
    paddle_x = B3Clamp(paddle_x + 5 * dt * ((keys & KEY_RIGHT ? 1 : 0) - (keys & KEY_LEFT ? 1 : 0)),
                       2, 14);
    paddle_y =
        B3Clamp(paddle_y + 5 * dt * ((keys & KEY_DOWN ? 1 : 0) - (keys & KEY_UP ? 1 : 0)), 8, 14);
    const float speed[] = {.8f, 1.3f, 1.8f};
    ax += B3Clamp(x - ax, -speed[difficulty_] * dt, speed[difficulty_] * dt);
    cooldown = std::max(0.f, cooldown - dt);
    if ((keys & KEY_A) && cooldown <= 0 && std::hypot(x - paddle_x, y - paddle_y) < 3) {
        vy = -9;
        vx = ax < 8 ? 4 : -4;
        cooldown = .3f;
        SoundEvent(Sound::Shot);
    }
    x += vx * dt;
    y += vy * dt;
    if (x < 1 || x > 14) {
        x = B3Clamp(x, 1, 14);
        vx = -vx;
        SoundEvent(Sound::Collision);
    }
    if (vy > 0 && std::hypot(x - paddle_x, y - paddle_y) < 1.5f) {
        vy = -5;
        vx = (x - paddle_x) * 3;
        SoundEvent(Sound::Hit);
    }
    if (vy < 0 && std::hypot(x - ax, y - 3) < 1.4f) {
        vy = 5 + difficulty_;
        vx = (x - ax) * 3;
        SoundEvent(Sound::Hit);
    }
    if (y < 1 || y > 15) {
        if (x >= 2 && x <= 14) {
            if (y < 1) {
                ++goals;
                Award(100);
            } else
                ++against;
            x = y = 8;
            vx = goals % 2 ? -1 : 1;
            vy = 3;
        } else {
            y = B3Clamp(y, 1, 15);
            vy = -vy;
        }
    }
    const int limit[] = {80, 65, 50};
    if (goals >= 3)
        Finish(true);
    else if (against >= 3 || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game023AirHockey::Progress() const { return goals * 100 / 3; }
void Game023AirHockey::Draw(uint8_t *fb) {
    B3Line(fb, 1, 1, 14, 1, 35, 70, 70);
    B3Line(fb, 1, 15, 14, 15, 35, 70, 70);
    B3Line(fb, 1, 8, 14, 8, 15, 35, 40);
    B3Disc(fb, paddle_x, paddle_y, 1.1f, 60, 170, 255);
    B3Disc(fb, ax, 3, 1.1f, 255, 80, 95);
    Px(fb, int(std::round(x)), int(std::round(y)), 245, 245, 245);
}

} // namespace arcade
