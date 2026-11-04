#include "game_091_wire_maze.h"
namespace arcade {

void Game091WireMaze::Setup() {
    memset(wire, 0, sizeof(wire));
    x = 2;
    y = 13;
    steps = 0;
    const int px[] = {2, 2, 7, 7, 12, 12, 5, 5, 3, 3, 13},
              py[] = {13, 9, 9, 12, 12, 3, 3, 6, 6, 1, 1};
    for (int i = 0; i < 10; ++i) {
        int xx = px[i], yy = py[i];
        while (xx != px[i + 1] || yy != py[i + 1]) {
            wire[yy * 16 + xx] = true;
            xx += (px[i + 1] > xx) - (px[i + 1] < xx);
            yy += (py[i + 1] > yy) - (py[i + 1] < yy);
        }
        wire[yy * 16 + xx] = true;
    }
}
void Game091WireMaze::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    if (dx || dy) {
        int nx = x + dx, ny = y + dy;
        if (nx < 0 || nx >= 16 || ny < 0 || ny >= 16 || !wire[ny * 16 + nx]) {
            SoundEvent(Sound::Collision);
            Finish(false);
            return;
        }
        x = nx;
        y = ny;
        ++steps;
        Award(2);
        SoundEvent(Sound::Action);
    }
    const int limit[] = {60, 40, 25};
    if (x == 13 && y == 1) {
        Award(1000);
        Finish(true);
    } else if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game091WireMaze::Progress() const {
    return state_ == STATE_VICTORY ? 100 : std::min(90, steps);
}
void Game091WireMaze::Draw(uint8_t *fb) {
    for (int p = 0; p < 256; ++p)
        if (wire[p])
            Px(fb, p % 16, p / 16, 65, 135, 170);
    Px(fb, 13, 1, 60, 245, 100);
    Px(fb, x, y, 255, 245, 120);
}

} // namespace arcade
