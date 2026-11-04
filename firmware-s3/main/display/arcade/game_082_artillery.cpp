#include "game_082_artillery.h"
namespace arcade {

void Game082Artillery::Setup() {
    angle = .8;
    power = 8;
    x = 2;
    y = 10;
    vx = vy = 0;
    for (auto &v : terrain)
        v = 13;
    terrain[7] = terrain[8] = 11;
    hp = enemy_hp = 3;
    owner = shots = 0;
    flying = false;
}
void Game082Artillery::Tick(float dt, uint16_t down, uint16_t pressed) {
    double t = std::round(double(dt) * 1000000) / 1000000;
    if (!flying) {
        angle = std::max(
            .2, std::min(1.4, angle + t * (bool(down & KEY_RIGHT) - bool(down & KEY_LEFT))));
        power = std::max(
            4., std::min(11., power + 3 * t * (bool(down & KEY_UP) - bool(down & KEY_DOWN))));
        if (pressed & KEY_A) {
            x = 2;
            y = terrain[2] - 1;
            vx = std::cos(angle) * power;
            vy = -std::sin(angle) * power;
            flying = true;
            owner = 0;
            ++shots;
            SoundEvent(Sound::Action);
        }
    } else {
        vy += 5 * t;
        x += vx * t;
        y += vy * t;
        int ix = int(x);
        if (x < 0 || x >= 16 || (ix >= 0 && ix < 16 && y >= terrain[ix])) {
            int target = owner == 0 ? 13 : 2;
            if (std::abs(x - target) < 1.5) {
                if (owner == 0) {
                    --enemy_hp;
                    Award(100);
                } else
                    --hp;
                SoundEvent(Sound::Hit);
            }
            if (ix >= 0 && ix < 16)
                terrain[ix] = std::min(15, terrain[ix] + 1);
            if (!enemy_hp) {
                Award(500);
                Finish(true);
                return;
            }
            if (!hp) {
                Finish(false);
                return;
            }
            if (owner == 0) {
                owner = 1;
                x = 13;
                y = terrain[13] - 1;
                const double error[] = {2, 1, .25};
                double target = 2 + error[difficulty_], duration = 2;
                vx = (target - 13) / duration;
                vy = (terrain[2] - y - 2.5 * duration * duration) / duration;
            } else
                flying = false;
        }
    }
    const int limit[] = {120, 100, 80};
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game082Artillery::Progress() const { return (3 - enemy_hp) * 100 / 3; }
void Game082Artillery::Draw(uint8_t *fb) {
    for (int x = 0; x < 16; ++x)
        B3Line(fb, x, terrain[x], x, 15, 65, 90, 55);
    Px(fb, 2, terrain[2] - 1, 70, 190, 240);
    Px(fb, 13, terrain[13] - 1, 245, 80, 90);
    if (flying)
        Px(fb, int(x), int(y), 255, 230, 120);
}

} // namespace arcade
