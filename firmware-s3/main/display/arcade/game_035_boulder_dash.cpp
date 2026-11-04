#include "game_035_boulder_dash.h"
namespace arcade {
void Game035BoulderDash::Setup() {
    for (int y = 0; y < 16; ++y)
        for (int x = 0; x < 16; ++x)
            grid_[y][x] = (x == 0 || x == 15 || y == 0 || y == 15) ? 1 : 2;
    for (int x = 1; x < 15; ++x)
        grid_[2][x] = 0;
    for (auto p : {std::pair<int, int>{5, 3}, {9, 3}, {5, 8}, {9, 8}})
        grid_[p.second][p.first] = 3;
    for (auto p :
         {std::pair<int, int>{3, 2}, {12, 2}, {3, 5}, {12, 5}, {3, 9}, {12, 9}, {3, 12}, {12, 12}})
        grid_[p.second][p.first] = 4;
    grid_[13][13] = 5;
    x_ = y_ = 2;
    gems_ = 0;
    fall_ = 0;
}
void Game035BoulderDash::Tick(float dt, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    int nx = x_ + dx, ny = y_ + dy, tile = grid_[ny][nx];
    if ((dx || dy) && tile == 3 && dx && grid_[ny][nx + dx] == 0) {
        grid_[ny][nx + dx] = 3;
        grid_[ny][nx] = 0;
        tile = 0;
        SoundEvent(Sound::Action);
    }
    if ((dx || dy) && tile != 1 && tile != 3) {
        if (tile == 4) {
            ++gems_;
            Award(100);
            SoundEvent(Sound::Hit, gems_);
        }
        if (tile != 5)
            grid_[ny][nx] = 0;
        x_ = nx;
        y_ = ny;
        if (tile == 5 && gems_ == 8) {
            Award(500);
            Finish(true);
            return;
        }
    }
    const float interval[] = {.18f, .14f, .10f};
    fall_ += dt;
    if (fall_ >= interval[difficulty_]) {
        fall_ = 0;
        for (int y = 14; y > 0; --y)
            for (int x = 1; x < 15; ++x)
                if (grid_[y][x] == 3) {
                    nx = x;
                    ny = y + 1;
                    if (grid_[ny][nx] == 3)
                        for (int d : {-1, 1})
                            if (grid_[y][x + d] == 0 && grid_[y + 1][x + d] == 0) {
                                nx = x + d;
                                break;
                            }
                    if (grid_[ny][nx] == 0) {
                        grid_[y][x] = 0;
                        grid_[ny][nx] = 3;
                        if (x_ == nx && y_ == ny) {
                            SoundEvent(Sound::Collision);
                            Finish(false);
                            return;
                        }
                    }
                }
    }
    const float limit[] = {90, 65, 45};
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
void Game035BoulderDash::Draw(uint8_t *fb) {
    const int colors[][3] = {{8, 10, 16},     {65, 80, 100},  {65, 40, 16},
                             {150, 155, 170}, {25, 230, 255}, {30, 65, 35}};
    for (int y = 0; y < 16; ++y)
        for (int x = 0; x < 16; ++x) {
            auto c = colors[grid_[y][x]];
            if (grid_[y][x] == 5 && gems_ == 8)
                Px(fb, x, y, 40, 220, 70);
            else
                Px(fb, x, y, c[0], c[1], c[2]);
        }
    Px(fb, x_, y_, 255, 200, 40);
    for (int x = 0; x < gems_; ++x)
        Px(fb, x + 1, 0, 20, 255, 255);
}
} // namespace arcade
