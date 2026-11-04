#include "game_008_jump_king.h"
namespace arcade {

void Game008JumpKing::Setup() {
    x = 3.5f;
    y = 46;
    vx = vy = charge = 0;
    facing = 1;
    grounded = true;
    charging = false;
}
void Game008JumpKing::Tick(float dt, uint16_t down, uint16_t pressed) {
    unsigned keys = down | pressed;
    if (grounded) {
        if (keys & KEY_LEFT)
            facing = -1;
        else if (keys & KEY_RIGHT)
            facing = 1;
        if (keys & KEY_A) {
            charge = std::min(1.2f, charge + dt);
            charging = true;
        } else if (charging) {
            vx = facing * (2 + 1.2f * charge);
            vy = -(7 + 8 * charge);
            charging = false;
            charge = 0;
            grounded = false;
            SoundEvent(Sound::Jump);
        }
    }
    float old = y;
    const float g[] = {8, 8.5f, 9};
    vy += g[difficulty_] * dt;
    x += vx * dt;
    y += vy * dt;
    if (x < .5f || x > 14.5f) {
        x = B3Clamp(x, .5f, 14.5f);
        vx = -vx * .5f;
    }
    grounded = false;
    const int platforms[][3] = {{47, 2, 6}, {37, 8, 13}, {27, 2, 7}, {17, 8, 13}, {7, 2, 7}};
    for (auto &p : platforms)
        if (vy >= 0 && x >= p[1] && x <= p[2] && old <= p[0] - 1 && y >= p[0] - 1) {
            y = p[0] - 1;
            vx = vy = 0;
            grounded = true;
        }
    const int limit[] = {100, 80, 65};
    if (grounded && y <= 6) {
        Award(1000);
        Finish(true);
    } else if (y > 51 || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game008JumpKing::Progress() const { return int((46 - y) / 40 * 100); }
void Game008JumpKing::Draw(uint8_t *fb) {
    int cam = std::max(0, std::min(36, int(y) - 8));
    const int platforms[][3] = {{47, 2, 6}, {37, 8, 13}, {27, 2, 7}, {17, 8, 13}, {7, 2, 7}};
    for (auto &p : platforms)
        B3Line(fb, p[1], p[0] - cam, p[2], p[0] - cam, 70, 185, 125);
    Px(fb, int(std::round(x)), int(std::round(y)) - cam, 255, 235, 90);
    for (int i = 0; i < int(charge / 1.2f * 14); ++i)
        Px(fb, i + 1, 0, 80, 170, 255);
}

} // namespace arcade
