#include "game_096_ice_maze.h"
namespace arcade {

bool Game096IceMaze::Wall(int x, int y) const {
    const char *rows[] = {"#######", "#..#..#", "#.....#", "##.#..#",
                          "#..#..#", "#.....#", "#######"};
    return x < 0 || x >= 7 || y < 0 || y >= 7 || rows[y][x] == '#';
}
void Game096IceMaze::Setup() {
    x = 1;
    y = 5;
    dx = dy = moves = 0;
    clock = 0;
    sliding = false;
}
void Game096IceMaze::Tick(float dt, uint16_t down, uint16_t pressed) {
    if (!sliding) {
        int xx, yy;
        Direction(down, pressed, xx, yy);
        if ((xx || yy) && !Wall(x + xx, y + yy)) {
            dx = xx;
            dy = yy;
            sliding = true;
            ++moves;
            SoundEvent(Sound::Action);
        }
    }
    if (sliding) {
        clock += std::round(double(dt) * 1000000) / 1000000;
        if (clock >= .06) {
            clock = 0;
            if (Wall(x + dx, y + dy))
                sliding = false;
            else {
                x += dx;
                y += dy;
            }
        }
    }
    const int budget[] = {16, 12, 8}, limit[] = {90, 70, 50};
    if (!sliding && x == 5 && y == 1) {
        Award(1500 - moves * 20);
        Finish(true);
    } else if ((!sliding && moves >= budget[difficulty_]) || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game096IceMaze::Progress() const {
    return state_ == STATE_VICTORY ? 100 : std::min(80, moves * 5);
}
void Game096IceMaze::Draw(uint8_t *fb) {
    for (int yy = 0; yy < 7; ++yy)
        for (int xx = 0; xx < 7; ++xx)
            if (Wall(xx, yy))
                Cell(fb, xx, yy, 80, 95, 115, 2, 1);
            else
                Cell(fb, xx, yy, 20, 65, 95, 2, 1);
    Cell(fb, 5, 1, 65, 215, 130, 2, 1);
    Cell(fb, x, y, 245, 245, 255, 2, 1);
}

} // namespace arcade
