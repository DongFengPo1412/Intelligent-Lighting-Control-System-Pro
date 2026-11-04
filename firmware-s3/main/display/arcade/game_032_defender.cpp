#include "game_032_defender.h"
namespace arcade {

void Game032Defender::Setup() {
    x = 8;
    y = 6;
    facing = 1;
    const int h[] = {3, 2, 1};
    hp = h[difficulty_];
    kills = 0;
    shot = 0;
    for (int i = 0; i < 4; ++i) {
        ex[i] = 4 + i * 8;
        ey[i] = 2;
        enemy[i] = human[i] = true;
        carrying[i] = false;
    }
    for (auto &b : bullet)
        b = false;
}
void Game032Defender::Tick(float dt, uint16_t down, uint16_t pressed) {
    unsigned keys = down | pressed;
    int dx = (keys & KEY_RIGHT ? 1 : 0) - (keys & KEY_LEFT ? 1 : 0),
        dy = (keys & KEY_DOWN ? 1 : 0) - (keys & KEY_UP ? 1 : 0);
    x = std::fmod(x + 6 * dt * dx + 32, 32.f);
    y = B3Clamp(y + 5 * dt * dy, 1, 12);
    if (dx)
        facing = dx;
    shot = std::max(0.f, shot - dt);
    if ((keys & KEY_A) && shot <= 0)
        for (int i = 0; i < 8; ++i)
            if (!bullet[i]) {
                bullet[i] = true;
                bx[i] = x;
                by[i] = y;
                bv[i] = facing * 14;
                life[i] = 2.5f;
                shot = .2f;
                SoundEvent(Sound::Shot);
                break;
            }
    for (int b = 0; b < 8; ++b)
        if (bullet[b]) {
            life[b] -= dt;
            if (life[b] <= 0) {
                bullet[b] = false;
                continue;
            }
            bx[b] = std::fmod(bx[b] + bv[b] * dt + 32, 32.f);
            for (int i = 0; i < 4; ++i)
                if (enemy[i] && std::abs(std::remainder(bx[b] - ex[i], 32.f)) < .8f &&
                    std::abs(by[b] - ey[i]) < .8f) {
                    enemy[i] = false;
                    human[i] = true;
                    ++kills;
                    Award(200);
                    bullet[b] = false;
                    SoundEvent(Sound::Hit, i);
                }
        }
    const float speed[] = {.45f, .6f, .8f};
    bool livehuman = false, liveenemy = false;
    for (int i = 0; i < 4; ++i) {
        if (enemy[i]) {
            ey[i] += (carrying[i] ? -1.f : speed[difficulty_]) * dt;
            if (ey[i] >= 13) {
                carrying[i] = true;
                human[i] = false;
            }
            if (ey[i] < 1)
                enemy[i] = false;
            if (std::abs(std::remainder(x - ex[i], 32.f)) < .8f && std::abs(y - ey[i]) < .8f) {
                --hp;
                enemy[i] = false;
                SoundEvent(Sound::Collision);
            }
        }
        livehuman |= human[i];
        liveenemy |= enemy[i];
    }
    const int limit[] = {90, 70, 55};
    if (kills == 4 && livehuman) {
        Award(500);
        Finish(true);
    } else if (hp <= 0 || !livehuman || !liveenemy || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game032Defender::Progress() const { return kills * 25; }
void Game032Defender::Draw(uint8_t *fb) {
    for (int xx = 0; xx < 16; ++xx)
        Px(fb, xx, 14, 25, 80, 65);
    for (int i = 0; i < 4; ++i) {
        int xx = int(std::round(std::fmod(ex[i] - x + 40, 32.f)));
        if (enemy[i])
            Px(fb, xx, int(std::round(ey[i])), 255, 75, 90);
        if (human[i])
            Px(fb, xx, 13, 60, 240, 130);
    }
    for (int i = 0; i < 8; ++i)
        if (bullet[i])
            Px(fb, int(std::round(std::fmod(bx[i] - x + 40, 32.f))), int(std::round(by[i])), 255,
               210, 50);
    Px(fb, 8, int(std::round(y)), 230, 240, 255);
    Px(fb, 8 + facing, int(std::round(y)), 90, 170, 255);
}

} // namespace arcade
