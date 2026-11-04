#include "game_081_qix.h"
namespace arcade {
void Game081Qix::Setup() {
    for (int y = 0; y < 16; ++y)
        for (int x = 0; x < 16; ++x)
            grid_[y][x] = (x == 1 || x == 14 || y == 1 || y == 14) ? 1 : 0;
    x_ = 1;
    y_ = 8;
    ex_ = 10;
    ey_ = 8;
    vx_ = -1;
    vy_ = 1;
    claimed_ = 0;
    armed_ = drawing_ = false;
    enemy_clock_ = 0;
}
void Game081Qix::Capture() {
    bool seen[16][16]{};
    int queue[144], read = 0, write = 0;
    queue[write++] = ey_ * 16 + ex_;
    seen[ey_][ex_] = true;
    const int dx[] = {1, -1, 0, 0}, dy[] = {0, 0, 1, -1};
    while (read < write) {
        int cell = queue[read++], x = cell % 16, y = cell / 16;
        for (int d = 0; d < 4; ++d) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx >= 2 && nx <= 13 && ny >= 2 && ny <= 13 && !grid_[ny][nx] && !seen[ny][nx]) {
                seen[ny][nx] = true;
                queue[write++] = ny * 16 + nx;
            }
        }
    }
    claimed_ = 0;
    for (int y = 2; y < 14; ++y)
        for (int x = 2; x < 14; ++x) {
            if (grid_[y][x] == 2 || (!grid_[y][x] && !seen[y][x]))
                grid_[y][x] = 1;
            if (grid_[y][x] == 1)
                ++claimed_;
        }
    Award(10);
    SoundEvent(Sound::Hit);
    drawing_ = armed_ = false;
    const int goal[] = {50, 60, 70};
    if (claimed_ * 100 >= 144 * goal[difficulty_]) {
        Award(1000);
        Finish(true);
    }
}
void Game081Qix::Tick(float dt, uint16_t down, uint16_t pressed) {
    if ((pressed & KEY_A) && !drawing_) {
        armed_ = !armed_;
        SoundEvent(Sound::Action);
    }
    int dx, dy;
    Direction(down, pressed, dx, dy);
    int nx = x_ + dx, ny = y_ + dy;
    if ((dx || dy) && nx >= 1 && nx <= 14 && ny >= 1 && ny <= 14) {
        int tile = grid_[ny][nx];
        if (tile == 2) {
            Finish(false);
            SoundEvent(Sound::Collision);
            return;
        }
        if (tile == 1) {
            x_ = nx;
            y_ = ny;
            if (drawing_)
                Capture();
        } else if (armed_) {
            grid_[ny][nx] = 2;
            x_ = nx;
            y_ = ny;
            drawing_ = true;
        }
    }
    if (state_ != STATE_PLAYING)
        return;
    const float interval[] = {.10f, .08f, .06f};
    enemy_clock_ += dt;
    if (enemy_clock_ >= interval[difficulty_]) {
        enemy_clock_ = 0;
        if (grid_[ey_][ex_ + vx_] == 1)
            vx_ = -vx_;
        if (grid_[ey_ + vy_][ex_] == 1)
            vy_ = -vy_;
        nx = ex_ + vx_;
        ny = ey_ + vy_;
        if (grid_[ny][nx] == 2) {
            SoundEvent(Sound::Collision);
            Finish(false);
            return;
        }
        if (grid_[ny][nx] == 0) {
            ex_ = nx;
            ey_ = ny;
        }
    }
    const int limit[] = {90, 70, 55};
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
void Game081Qix::Draw(uint8_t *fb) {
    const int colors[][3] = {{7, 12, 25}, {25, 90, 150}, {245, 190, 30}};
    for (int y = 1; y < 15; ++y)
        for (int x = 1; x < 15; ++x) {
            auto c = colors[grid_[y][x]];
            Px(fb, x, y, c[0], c[1], c[2]);
        }
    Px(fb, ex_, ey_, 255, 50, 130);
    Px(fb, x_, y_, armed_ ? 255 : 230, armed_ ? 210 : 255, armed_ ? 60 : 255);
}
} // namespace arcade
