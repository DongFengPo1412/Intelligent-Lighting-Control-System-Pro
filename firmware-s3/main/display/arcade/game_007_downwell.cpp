#include "game_007_downwell.h"
namespace arcade {

void Game007Downwell::Setup() {
    x = 8;
    y = 2;
    vy = 0;
    const int a[] = {4, 3, 2}, h[] = {3, 2, 1};
    ammo = a[difficulty_];
    hp = h[difficulty_];
    kills = 0;
    grounded = false;
    for (auto &b : bullet)
        b = false;
    for (auto &e : enemy)
        e = true;
}
void Game007Downwell::Tick(float dt, uint16_t down, uint16_t pressed) {
    unsigned keys = down | pressed;
    x = B3Clamp(x + dt * 4 * ((keys & KEY_RIGHT ? 1 : 0) - (keys & KEY_LEFT ? 1 : 0)), 1, 14);
    if ((pressed & KEY_A) && ammo)
        for (int i = 0; i < 8; ++i)
            if (!bullet[i]) {
                --ammo;
                bullet[i] = true;
                bx[i] = x;
                by[i] = y + 1;
                vy -= 1.2f;
                SoundEvent(Sound::Shot);
                break;
            }
    for (int b = 0; b < 8; ++b)
        if (bullet[b]) {
            by[b] += 14 * dt;
            for (int i = 0; i < 3; ++i) {
                int ey = 10 + i * 12;
                if (enemy[i] && std::abs(bx[b] - 8) < .8f && by[b] >= ey && by[b] <= ey + 1) {
                    enemy[i] = false;
                    ++kills;
                    Award(100);
                    by[b] = 100;
                    SoundEvent(Sound::Hit, i);
                }
            }
            if (by[b] >= 48)
                bullet[b] = false;
        }
    float old = y;
    const int g[] = {7, 8, 9}, a[] = {4, 3, 2};
    vy = std::min(6.f, vy + g[difficulty_] * dt);
    y += vy * dt;
    grounded = false;
    const int shelves[][3] = {{12, 2, 6}, {24, 9, 13}, {36, 2, 6}, {46, 1, 14}};
    for (auto &p : shelves)
        if (vy >= 0 && x >= p[1] && x <= p[2] && old <= p[0] - 1 && y >= p[0] - 1) {
            y = p[0] - 1;
            vy = 0;
            ammo = a[difficulty_];
            grounded = true;
        }
    for (int i = 0; i < 3; ++i)
        if (enemy[i] && std::abs(x - 8) < .8f && std::abs(y - (10 + i * 12)) < .8f) {
            enemy[i] = false;
            --hp;
            SoundEvent(Sound::Collision);
        }
    if (hp <= 0 || elapsed_ > 60)
        Finish(false);
    else if (y >= 45) {
        if (kills == 3)
            Award(500);
        Finish(kills == 3);
    }
}
int Game007Downwell::Progress() const { return int((y - 2) / 43 * 100); }
void Game007Downwell::Draw(uint8_t *fb) {
    int cam = std::max(0, int(y) - 7);
    for (int yy = 0; yy < 16; ++yy) {
        Px(fb, 0, yy, 40, 45, 60);
        Px(fb, 15, yy, 40, 45, 60);
    }
    const int shelves[][3] = {{12, 2, 6}, {24, 9, 13}, {36, 2, 6}, {46, 1, 14}};
    for (auto &p : shelves)
        B3Line(fb, p[1], p[0] - cam, p[2], p[0] - cam, 55, 190, 180);
    for (int i = 0; i < 3; ++i)
        if (enemy[i])
            Px(fb, 8, 10 + i * 12 - cam, 255, 60, 80);
    for (int i = 0; i < 8; ++i)
        if (bullet[i])
            Px(fb, int(std::round(bx[i])), int(std::round(by[i])) - cam, 255, 210, 40);
    Px(fb, int(std::round(x)), int(std::round(y)) - cam, 240, 245, 255);
    for (int i = 0; i < ammo; ++i)
        Px(fb, i + 1, 0, 240, 195, 30);
}

} // namespace arcade
