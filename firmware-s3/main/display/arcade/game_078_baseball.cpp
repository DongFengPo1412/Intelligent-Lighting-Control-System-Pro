#include "game_078_baseball.h"
namespace arcade {

void Game078Baseball::Setup() {
    ball_y = 1;
    wait = .5;
    pitches = runs = strikes = 0;
    active = false;
}
void Game078Baseball::Tick(float dt, uint16_t, uint16_t pressed) {
    double t = std::round(double(dt) * 1000000) / 1000000;
    const double speed[] = {5, 6, 7}, window[] = {1.1, .8, .55};
    if (!active) {
        wait -= t;
        if (wait <= 0) {
            active = true;
            ball_y = 1;
            ++pitches;
        }
    } else {
        ball_y += speed[difficulty_] * t;
        if (pressed & KEY_A) {
            if (std::abs(ball_y - 12) < window[difficulty_]) {
                runs += std::abs(ball_y - 12) < .25 ? 2 : 1;
                Award(100);
                SoundEvent(Sound::Hit);
            } else {
                ++strikes;
                SoundEvent(Sound::Collision);
            }
            active = false;
            wait = .5;
        } else if (ball_y > 14) {
            ++strikes;
            active = false;
            wait = .5;
            SoundEvent(Sound::Collision);
        }
    }
    if (runs >= 6) {
        Award(500);
        Finish(true);
    } else if (strikes >= 3 || (pitches >= 10 && !active) || elapsed_ > 60)
        Finish(false);
}
int Game078Baseball::Progress() const { return runs * 100 / 6; }
void Game078Baseball::Draw(uint8_t *fb) {
    B3Line(fb, 8, 1, 8, 14, 30, 55, 60);
    B3Line(fb, 5, 13, 11, 13, 230, 190, 70);
    Px(fb, 8, int(ball_y), 255, 255, 255);
    for (int i = 0; i < runs; ++i)
        Px(fb, i + 1, 0, 60, 220, 110);
    for (int i = 0; i < strikes; ++i)
        Px(fb, i + 1, 15, 245, 60, 80);
}

} // namespace arcade
