#include "game_025_marble_maze.h"
namespace arcade {

void Game025MarbleMaze::Setup() {
    x = y = 2;
    vx = vy = 0;
    for (int yy = 0; yy < 16; ++yy)
        for (int xx = 0; xx < 16; ++xx)
            grid[yy][xx] = (xx == 0 || xx == 15 || yy == 0 || yy == 15) ? 1 : 0;
    for (int yy = 1; yy < 12; ++yy)
        grid[yy][5] = yy == 7 ? 0 : 1;
    for (int yy = 4; yy < 15; ++yy)
        grid[yy][10] = yy == 10 ? 0 : 1;
}
void Game025MarbleMaze::Tick(float dt, uint16_t down, uint16_t pressed) {
    unsigned keys = down | pressed;
    const int acc[] = {4, 5, 6}, limit[] = {100, 80, 60};
    int drag = keys & KEY_A ? 10 : 2;
    vx = (vx + acc[difficulty_] * dt * ((keys & KEY_RIGHT ? 1 : 0) - (keys & KEY_LEFT ? 1 : 0))) *
         std::max(0.f, 1 - drag * dt);
    vy = (vy + acc[difficulty_] * dt * ((keys & KEY_DOWN ? 1 : 0) - (keys & KEY_UP ? 1 : 0))) *
         std::max(0.f, 1 - drag * dt);
    float nx = B3Clamp(x + vx * dt, .5f, 14.5f), ny = B3Clamp(y + vy * dt, .5f, 14.5f);
    if (grid[int(std::round(y))][int(std::round(nx))]) {
        vx = -vx * .35f;
        SoundEvent(Sound::Collision);
    } else
        x = nx;
    if (grid[int(std::round(ny))][int(std::round(x))])
        vy = -vy * .35f;
    else
        y = ny;
    const int pits[][2] = {{3, 10}, {8, 4}, {12, 7}};
    for (auto &p : pits)
        if (std::hypot(x - p[0], y - p[1]) < .55f) {
            Finish(false);
            return;
        }
    if (std::hypot(x - 13, y - 13) < .7f && std::hypot(vx, vy) < 1.2f) {
        Award(1000);
        Finish(true);
    } else if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game025MarbleMaze::Progress() const { return int((x + y - 4) / 22 * 100); }
void Game025MarbleMaze::Draw(uint8_t *fb) {
    for (int yy = 0; yy < 16; ++yy)
        for (int xx = 0; xx < 16; ++xx)
            if (grid[yy][xx])
                Px(fb, xx, yy, 70, 95, 120);
    const int pits[][2] = {{3, 10}, {8, 4}, {12, 7}};
    for (auto &p : pits)
        Px(fb, p[0], p[1], 230, 45, 75);
    Px(fb, 13, 13, 40, 230, 100);
    Px(fb, int(std::round(x)), int(std::round(y)), 245, 245, 255);
}

} // namespace arcade
