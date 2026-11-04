#include "game_059_cut_rope.h"
namespace arcade {

void Game059CutRope::Setup() {
    x = y = 8;
    vx = vy = theta = 0;
    cut = false;
    const int n[] = {3, 2, 1};
    tries = n[difficulty_];
}
void Game059CutRope::Tick(float dt, uint16_t, uint16_t pressed) {
    const double speed[] = {1.2, 1.5, 1.8}, width[] = {1.8, 1.3, .9};
    const int limit[] = {60, 45, 30};
    double t = std::round(double(dt) * 1000000) / 1000000,
           a = std::sin(elapsed_ * speed[difficulty_]) * 1.1,
           rate = std::cos(elapsed_ * speed[difficulty_]) * 1.1 * speed[difficulty_];
    if (!cut) {
        theta = a;
        x = 8 + 5 * std::sin(a);
        y = 2 + 5 * std::cos(a);
        vx = 5 * std::cos(a) * rate;
        vy = -5 * std::sin(a) * rate;
        if (pressed & KEY_A) {
            cut = true;
            SoundEvent(Sound::Action);
        }
    } else {
        vy += 5 * t;
        x += vx * t;
        y += vy * t;
        if (y >= 13) {
            if (std::abs(x - 12) < width[difficulty_]) {
                Award(1000 + tries * 50);
                Finish(true);
            } else {
                --tries;
                cut = false;
                SoundEvent(Sound::Collision);
            }
        }
    }
    if (tries <= 0 || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game059CutRope::Progress() const { return state_ == STATE_VICTORY ? 100 : 0; }
void Game059CutRope::Draw(uint8_t *fb) {
    B3Line(fb, 10, 14, 14, 14, 70, 220, 100);
    B3Disc(fb, 12, 14, 1, 70, 220, 100);
    if (!cut)
        B3Line(fb, 8, 2, int(x), int(y), 100, 110, 130);
    B3Disc(fb, x, y, .8, 245, 180, 65);
}

} // namespace arcade
