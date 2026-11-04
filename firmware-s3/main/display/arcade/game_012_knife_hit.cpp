#include "game_012_knife_hit.h"
namespace arcade {

void Game012KnifeHit::Setup() {
    theta = 0;
    knife_y = 14;
    angles[0] = 0;
    angles[1] = 3.14159265f;
    count = 2;
    hits = 0;
    flying = false;
}
void Game012KnifeHit::Tick(float dt, uint16_t, uint16_t pressed) {
    const float speed[] = {.8f, 1.1f, 1.5f}, gap[] = {.4f, .35f, .30f};
    const int goal[] = {8, 10, 12}, limit[] = {60, 45, 35};
    theta = B3Wrap(theta + (speed[difficulty_] + .2f * std::sin(elapsed_ * .5f)) * dt);
    if ((pressed & KEY_A) && !flying) {
        flying = true;
        knife_y = 14;
        SoundEvent(Sound::Shot);
    }
    if (flying) {
        knife_y -= 20 * dt;
        if (knife_y <= 10) {
            float local = B3Wrap(1.57079633f - theta);
            flying = false;
            for (int i = 0; i < count; ++i)
                if (B3AngleDistance(local, angles[i]) < gap[difficulty_]) {
                    SoundEvent(Sound::Collision);
                    Finish(false);
                    return;
                }
            angles[count++] = local;
            ++hits;
            Award(50);
            SoundEvent(Sound::Hit, hits);
            if (hits >= goal[difficulty_]) {
                Award(500);
                Finish(true);
            }
        }
    }
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game012KnifeHit::Progress() const {
    const int goal[] = {8, 10, 12};
    return hits * 100 / goal[difficulty_];
}
void Game012KnifeHit::Draw(uint8_t *fb) {
    B3Disc(fb, 8, 7, 2.6f, 100, 65, 35);
    for (int i = 0; i < count; ++i) {
        float a = angles[i] + theta;
        B3Line(fb, int(std::round(8 + std::cos(a) * 2.5f)), int(std::round(7 + std::sin(a) * 2.5f)),
               int(std::round(8 + std::cos(a) * 4)), int(std::round(7 + std::sin(a) * 4)), 220, 230,
               245);
    }
    if (flying)
        B3Line(fb, 8, int(std::round(knife_y)), 8, int(std::round(knife_y)) + 2, 255, 210, 55);
}

} // namespace arcade
