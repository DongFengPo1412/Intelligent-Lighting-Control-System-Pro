#include "game_099_auto_survivor.h"
namespace arcade {

void Game099AutoSurvivor::Setup() {
    x = y = 8;
    memset(ex, 0, sizeof(ex));
    memset(ey, 0, sizeof(ey));
    memset(ehp, 0, sizeof(ehp));
    ex[0] = 8;
    ey[0] = 3;
    ehp[0] = 1;
    spawn = attack = invul = 0;
    const int n[] = {5, 4, 3};
    hp = n[difficulty_];
    kills = upgrades = rate_bonus = 0;
    damage = 1;
    seed = 0x99ab;
}
void Game099AutoSurvivor::Tick(float dt, uint16_t down, uint16_t pressed) {
    double t = std::round(double(dt) * 1000000) / 1000000;
    x = std::max(1., std::min(14., x + 3 * t * (bool(down & KEY_RIGHT) - bool(down & KEY_LEFT))));
    y = std::max(1., std::min(14., y + 3 * t * (bool(down & KEY_DOWN) - bool(down & KEY_UP))));
    if (kills >= 3 * (upgrades + 1) && upgrades < 2 && (pressed & (KEY_A | KEY_B))) {
        ++upgrades;
        if (pressed & KEY_A)
            ++damage;
        else
            ++rate_bonus;
        SoundEvent(Sound::Hit, upgrades);
    }
    spawn += t;
    attack -= t;
    invul = std::max(0., invul - t);
    const double sp[] = {.9, .7, .5}, speed[] = {.8, 1., 1.2};
    int free = -1;
    for (int i = 0; i < 12; ++i)
        if (!ehp[i]) {
            free = i;
            break;
        }
    if (spawn >= sp[difficulty_] && free >= 0) {
        int side = (B3Random(seed) >> 16) % 4, p = 1 + (B3Random(seed) >> 16) % 14;
        ex[free] = side == 0 ? 1 : side == 1 ? 14 : p;
        ey[free] = side == 2 ? 1 : side == 3 ? 14 : p;
        ehp[free] = difficulty_ == 2 ? 3 : 2;
        spawn = 0;
    }
    for (int i = 0; i < 12; ++i)
        if (ehp[i]) {
            double dx = x - ex[i], dy = y - ey[i], distance = std::hypot(dx, dy);
            if (distance > .001) {
                ex[i] += dx / distance * speed[difficulty_] * t;
                ey[i] += dy / distance * speed[difficulty_] * t;
            }
            if (distance < .65 && invul == 0) {
                --hp;
                invul = .6;
                SoundEvent(Sound::Collision);
            }
        }
    int target = -1;
    double best = 1e30;
    for (int i = 0; i < 12; ++i)
        if (ehp[i]) {
            double d = std::hypot(x - ex[i], y - ey[i]);
            if (d < best) {
                best = d;
                target = i;
            }
        }
    if (attack <= 0 && target >= 0 && best <= 4) {
        ehp[target] = std::max(0, ehp[target] - damage);
        attack = std::max(.18, .65 - .1 * upgrades - .1 * rate_bonus);
        SoundEvent(Sound::Action);
        if (!ehp[target]) {
            ++kills;
            Award(25);
        }
    }
    const int goal[] = {30, 40, 50}, limit[] = {60, 70, 80};
    if (hp <= 0)
        Finish(false);
    else if (elapsed_ >= goal[difficulty_] && kills >= 8) {
        Award(1000);
        Finish(true);
    } else if (elapsed_ >= limit[difficulty_])
        Finish(false);
}
int Game099AutoSurvivor::Progress() const {
    const int goal[] = {30, 40, 50};
    return std::min(100, int(elapsed_ * 100 / goal[difficulty_]));
}
void Game099AutoSurvivor::Draw(uint8_t *fb) {
    for (int i = 0; i < 12; ++i)
        if (ehp[i])
            Px(fb, int(ex[i]), int(ey[i]), 235, 70, 95);
    Px(fb, int(x), int(y), 95, 220, 240);
    for (int i = 0; i < std::max(0, hp); ++i)
        Px(fb, i, 0, 65, 220, 100);
    if (kills >= 3 * (upgrades + 1) && upgrades < 2)
        Px(fb, 15, 0, 245, 215, 55);
}

} // namespace arcade
