#include "game_036_dig_dug.h"
namespace arcade {

void Game036DigDug::Setup() {
    x = y = 7;
    face = 0;
    const int h[] = {3, 2, 1}, xx[] = {3, 12, 13}, yy[] = {3, 2, 13};
    hp = h[difficulty_];
    kills = 0;
    enemy_clock = 0;
    memset(dirt, 1, sizeof(dirt));
    dirt[7][7] = 0;
    for (int i = 0; i < 3; ++i) {
        ex[i] = xx[i];
        ey[i] = yy[i];
        inflate[i] = 0;
        enemy[i] = true;
    }
}
void Game036DigDug::Tick(float dt, uint16_t down, uint16_t pressed) {
    unsigned keys = down | pressed;
    int dx, dy;
    Direction(down, pressed, dx, dy);
    if (dx || dy) {
        face = dy < 0 ? 0 : dx > 0 ? 1 : dy > 0 ? 2 : 3;
        if (!(keys & KEY_A)) {
            x = std::max(1, std::min(14, x + dx));
            y = std::max(1, std::min(14, y + dy));
            dirt[y][x] = 0;
        }
    }
    const int fx[] = {0, 1, 0, -1}, fy[] = {-1, 0, 1, 0};
    int target = -1;
    if (keys & KEY_A)
        for (int i = 0; i < 3; ++i) {
            int d = (ex[i] - x) * fx[face] + (ey[i] - y) * fy[face];
            if (enemy[i] && d > 0 && d <= 4 && (ex[i] - x) * fy[face] == (ey[i] - y) * fx[face]) {
                target = i;
                break;
            }
        }
    const float pump[] = {.30f, .40f, .50f}, interval[] = {.65f, .55f, .45f};
    for (int i = 0; i < 3; ++i) {
        inflate[i] = i == target ? inflate[i] + dt / pump[difficulty_]
                                 : std::max(0.f, inflate[i] - dt * .5f);
        if (enemy[i] && inflate[i] >= 1) {
            enemy[i] = false;
            ++kills;
            Award(200);
            SoundEvent(Sound::Hit, i);
        }
    }
    enemy_clock += dt;
    if (enemy_clock >= interval[difficulty_]) {
        enemy_clock = 0;
        for (int i = 0; i < 3; ++i)
            if (enemy[i] && i != target) {
                dx = x - ex[i];
                dy = y - ey[i];
                if (std::abs(dx) >= std::abs(dy) && dx)
                    ex[i] += dx > 0 ? 1 : -1;
                else if (dy)
                    ey[i] += dy > 0 ? 1 : -1;
                if (ex[i] == x && ey[i] == y) {
                    --hp;
                    enemy[i] = false;
                    SoundEvent(Sound::Collision);
                }
            }
    }
    if (kills == 3) {
        Award(500);
        Finish(true);
    } else if (hp <= 0 || elapsed_ > 60)
        Finish(false);
}
int Game036DigDug::Progress() const { return kills * 100 / 3; }
void Game036DigDug::Draw(uint8_t *fb) {
    for (int yy = 1; yy < 15; ++yy)
        for (int xx = 1; xx < 15; ++xx)
            if (dirt[yy][xx])
                Px(fb, xx, yy, 70, 38, 18);
            else
                Px(fb, xx, yy, 8, 12, 20);
    for (int i = 0; i < 3; ++i)
        if (enemy[i])
            Px(fb, ex[i], ey[i], 255, int(60 + 150 * inflate[i]), 80);
    Px(fb, x, y, 245, 245, 255);
}

} // namespace arcade
