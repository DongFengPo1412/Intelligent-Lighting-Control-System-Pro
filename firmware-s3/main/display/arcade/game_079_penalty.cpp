#include "game_079_penalty.h"
namespace arcade {

void Game079Penalty::Setup() {
    aim = impact = keeper = 8;
    power = flight = 0;
    charging = flying = false;
    shots = goals = 0;
}
void Game079Penalty::Tick(float dt, uint16_t down, uint16_t) {
    double t = std::round(double(dt) * 1000000) / 1000000;
    const int speed[] = {2, 3, 4}, limit[] = {90, 75, 60};
    const double width[] = {2, 2.5, 3};
    keeper = 8 + 4 * std::sin(elapsed_ * speed[difficulty_]);
    if (!flying) {
        aim = std::max(
            3., std::min(12., aim + 5 * t * (bool(down & KEY_RIGHT) - bool(down & KEY_LEFT))));
        if (down & KEY_A) {
            charging = true;
            power = std::min(1.2, power + t);
        } else if (charging) {
            charging = false;
            flying = true;
            impact = aim + (power > 1 ? 3 : 0);
            flight = .5;
            power = 0;
            SoundEvent(Sound::Action);
        }
    } else {
        flight -= t;
        if (flight <= 0) {
            ++shots;
            flying = false;
            if (impact >= 3 && impact <= 12 && std::abs(impact - keeper) > width[difficulty_]) {
                ++goals;
                Award(100);
                SoundEvent(Sound::Hit);
            } else
                SoundEvent(Sound::Collision);
            if (shots == 5)
                Finish(goals >= 3);
        }
    }
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game079Penalty::Progress() const { return shots * 20; }
void Game079Penalty::Draw(uint8_t *fb) {
    B3Line(fb, 2, 1, 13, 1, 220, 220, 220);
    B3Line(fb, 2, 1, 2, 5, 220, 220, 220);
    B3Line(fb, 13, 1, 13, 5, 220, 220, 220);
    B3Line(fb, int(keeper) - 1, 3, int(keeper) + 1, 3, 245, 90, 80);
    B3Disc(fb, flying ? impact : aim, flying ? 4 + flight * 18 : 13, .7, 245, 230, 170);
}

} // namespace arcade
