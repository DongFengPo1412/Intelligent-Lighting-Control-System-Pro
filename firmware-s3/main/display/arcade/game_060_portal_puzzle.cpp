#include "game_060_portal_puzzle.h"
namespace arcade {

void Game060PortalPuzzle::Setup() {
    x = 1;
    y = 6;
    moves = teleports = 0;
    gate = false;
}
void Game060PortalPuzzle::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    int nx = x + dx, ny = y + dy;
    if ((dx || dy) && nx >= 1 && nx <= 6 && ny >= 1 && ny <= 6 && nx != 4 &&
        !(ny == 3 && nx >= 5 && !gate)) {
        x = nx;
        y = ny;
        ++moves;
        SoundEvent(Sound::Action);
    }
    if ((pressed & KEY_A) && ((x == 1 && y == 1) || (x == 6 && y == 6))) {
        if (x == 1) {
            x = y = 6;
        } else {
            x = y = 1;
        }
        ++teleports;
        ++moves;
        SoundEvent(Sound::Hit);
    }
    if (x == 5 && y == 5)
        gate = true;
    if (x == 6 && y == 1 && gate) {
        Award(1500 - moves * 10);
        Finish(true);
    } else {
        const int b[] = {60, 45, 30}, limit[] = {90, 70, 50};
        if (moves >= b[difficulty_] || elapsed_ > limit[difficulty_])
            Finish(false);
    }
}
int Game060PortalPuzzle::Progress() const {
    return state_ == STATE_VICTORY ? 100 : gate ? 50 : teleports ? 20 : 0;
}
void Game060PortalPuzzle::Draw(uint8_t *fb) {
    for (int yy = 0; yy < 8; ++yy)
        for (int xx = 0; xx < 8; ++xx)
            if (xx == 0 || xx == 4 || xx == 7 || yy == 0 || yy == 7 ||
                (yy == 3 && xx >= 5 && !gate))
                Cell(fb, xx, yy, 70, 80, 95, 2, 0);
    Cell(fb, 1, 1, 50, 120, 255, 2, 0);
    Cell(fb, 6, 6, 245, 130, 45, 2, 0);
    Cell(fb, 5, 5, gate ? 100 : 180, gate ? 220 : 60, gate ? 160 : 150, 2, 0);
    Cell(fb, 6, 1, 40, 220, 80, 2, 0);
    Cell(fb, x, y, 255, 245, 160, 2, 0);
}

} // namespace arcade
