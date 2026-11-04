#include "game_098_lunar_lander.h"
namespace arcade {
void Game098LunarLander::Setup() {
    const float fuel[] = {45, 35, 25};
    x_ = 4;
    y_ = 2;
    vx_ = vy_ = angle_ = 0;
    fuel_ = fuel[difficulty_];
    thrusting_ = false;
}
void Game098LunarLander::Tick(float dt, uint16_t down, uint16_t pressed) {
    unsigned keys = down | pressed;
    angle_ = std::max(
        -.8f, std::min(.8f, angle_ + dt * 1.8f *
                                         ((keys & KEY_RIGHT ? 1 : 0) - (keys & KEY_LEFT ? 1 : 0))));
    bool was_thrusting = thrusting_;
    thrusting_ = (keys & (KEY_A | KEY_UP)) && fuel_ > 0;
    float thrust = thrusting_ ? 3.8f : 0;
    if (thrusting_) {
        fuel_ = std::max(0.f, fuel_ - 2 * dt);
        if (!was_thrusting)
            SoundEvent(Sound::Shot);
    }
    const float wind[] = {0, .03f, .05f}, gravity[] = {1.6f, 1.8f, 2.f};
    vx_ += (std::sin(angle_) * thrust + wind[difficulty_]) * dt;
    vy_ += (gravity[difficulty_] - std::cos(angle_) * thrust) * dt;
    x_ += vx_ * dt;
    y_ += vy_ * dt;
    const float half[] = {3, 2, 1}, vlimit[] = {1.4f, 1.1f, .8f}, hlimit[] = {.7f, .55f, .4f};
    bool onpad = x_ >= 8 - half[difficulty_] && x_ <= 8 + half[difficulty_];
    int ground = onpad ? 13 : 10 + int(std::max(0.f, std::min(15.f, x_))) % 3;
    if (y_ >= ground) {
        bool safe = onpad && vy_ >= 0 && vy_ <= vlimit[difficulty_] &&
                    std::abs(vx_) <= hlimit[difficulty_] && std::abs(angle_) <= .25f;
        if (safe)
            Award(1000 + unsigned(fuel_ * 10));
        SoundEvent(safe ? Sound::Hit : Sound::Collision);
        Finish(safe);
    } else if (x_ < .5f || x_ > 14.5f || y_ < .5f || elapsed_ > 60)
        Finish(false);
}
void Game098LunarLander::Draw(uint8_t *fb) {
    const int half[] = {3, 2, 1};
    const float fuel[] = {45, 35, 25};
    for (int x = 0; x < 16; ++x) {
        bool pad = x >= 8 - half[difficulty_] && x <= 8 + half[difficulty_];
        int ground = pad ? 13 : 10 + x % 3;
        for (int y = ground; y < 16; ++y)
            if (pad && y == 13)
                Px(fb, x, y, 40, 220, 130);
            else
                Px(fb, x, y, 45, 50, 65);
    }
    int x = int(std::round(x_)), y = int(std::round(y_));
    Px(fb, x, y, 245, 245, 255);
    Px(fb, x + (angle_ < 0 ? -1 : 1), y, 100, 160, 255);
    if (thrusting_)
        Px(fb, x, y + 1, 255, 130, 25);
    for (int i = 0; i < int(fuel_ / fuel[difficulty_] * 14); ++i)
        Px(fb, i + 1, 0, 255, 200, 40);
}
} // namespace arcade
