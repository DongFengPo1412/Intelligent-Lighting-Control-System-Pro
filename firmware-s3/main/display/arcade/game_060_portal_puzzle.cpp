#include "game_060_portal_puzzle.h"
namespace arcade {
static const int portals[3][4] = {{1, 1, 6, 6}, {3, 2, 5, 6}, {2, 5, 6, 4}},
                 switches[3][2] = {{5, 5}, {6, 5}, {5, 4}}, exits[3][2] = {{6, 1}, {5, 1}, {6, 1}},
                 blocks[3][2] = {{-1, -1}, {5, 4}, {6, 5}};
void Game060PortalPuzzle::LoadStage() {
    x = 1;
    y = 6;
    gate = false;
    stage_moves = 0;
}
void Game060PortalPuzzle::Setup() {
    stage = moves = teleports = 0;
    LoadStage();
}
bool Game060PortalPuzzle::Wall(int xx, int yy) const {
    return xx < 1 || xx > 6 || yy < 1 || yy > 6 || xx == 4 || (yy == 3 && xx >= 5 && !gate) ||
           (xx == blocks[std::min(stage, 2)][0] && yy == blocks[std::min(stage, 2)][1]);
}
void Game060PortalPuzzle::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    int nx = x + dx, ny = y + dy;
    if ((dx || dy) && !Wall(nx, ny)) {
        x = nx;
        y = ny;
        ++moves;
        ++stage_moves;
        SoundEvent(Sound::Action);
    }
    auto p = portals[stage];
    if ((pressed & KEY_A) && ((x == p[0] && y == p[1]) || (x == p[2] && y == p[3]))) {
        if (x == p[0] && y == p[1]) {
            x = p[2];
            y = p[3];
        } else {
            x = p[0];
            y = p[1];
        }
        ++moves;
        ++stage_moves;
        ++teleports;
        SoundEvent(Sound::Hit);
    }
    if (x == switches[stage][0] && y == switches[stage][1])
        gate = true;
    if (x == exits[stage][0] && y == exits[stage][1] && gate) {
        Award(std::max(100, 1500 - stage_moves * 10));
        ++stage;
        if (stage == 3)
            Finish(true);
        else
            LoadStage();
    } else {
        const int b[] = {60, 45, 30}, limit[] = {270, 210, 150};
        if (stage_moves >= b[difficulty_] || elapsed_ > limit[difficulty_])
            Finish(false);
    }
}
int Game060PortalPuzzle::Progress() const {
    return std::min(100, stage * 100 / 3 + (gate ? 16 : 0));
}
void Game060PortalPuzzle::Draw(uint8_t *fb) {
    int shown = std::min(stage, 2);
    for (int yy = 0; yy < 8; ++yy)
        for (int xx = 0; xx < 8; ++xx)
            if (Wall(xx, yy))
                Cell(fb, xx, yy, 70, 80, 95, 2, 0);
    auto p = portals[shown];
    Cell(fb, p[0], p[1], 50, 120, 255, 2, 0);
    Cell(fb, p[2], p[3], 245, 130, 45, 2, 0);
    Cell(fb, switches[shown][0], switches[shown][1], gate ? 100 : 180, gate ? 220 : 60,
         gate ? 160 : 150, 2, 0);
    Cell(fb, exits[shown][0], exits[shown][1], 40, 220, 80, 2, 0);
    Cell(fb, x, y, 255, 245, 160, 2, 0);
}
} // namespace arcade
