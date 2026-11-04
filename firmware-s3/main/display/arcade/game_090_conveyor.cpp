#include "game_090_conveyor.h"
namespace arcade {

void Game090Conveyor::Setup() {
    memset(belt, 0, sizeof(belt));
    for (auto &p : item)
        p = -1;
    memset(processed, 0, sizeof(processed));
    x = y = delivered = waste = 0;
    clock = spawn = 0;
}
void Game090Conveyor::Tick(float dt, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    x = std::max(0, std::min(6, x + dx));
    y = std::max(0, std::min(6, y + dy));
    if (pressed & KEY_A) {
        belt[y * 7 + x] = (belt[y * 7 + x] + 1) % 4;
        SoundEvent(Sound::Action);
    }
    double t = std::round(double(dt) * 1000000) / 1000000;
    spawn += t;
    clock += t;
    const double sp[] = {1.2, .9, .6}, period[] = {.3, .24, .18};
    int free = -1;
    bool occupied = false;
    for (int i = 0; i < 4; ++i) {
        if (item[i] < 0 && free < 0)
            free = i;
        occupied |= item[i] == 21;
    }
    if (spawn >= sp[difficulty_] && free >= 0 && !occupied) {
        item[free] = 21;
        processed[free] = 0;
        spawn = 0;
    }
    if (clock >= period[difficulty_]) {
        clock = 0;
        int old[4];
        memcpy(old, item, sizeof(old));
        const int xx[] = {1, 0, -1, 0}, yy[] = {0, 1, 0, -1};
        for (int i = 0; i < 4; ++i) {
            int p = old[i];
            if (p < 0)
                continue;
            if (p == 10)
                processed[i] = 1;
            if (p == 27) {
                if (processed[i]) {
                    ++delivered;
                    Award(100);
                    SoundEvent(Sound::Hit);
                } else {
                    ++waste;
                    SoundEvent(Sound::Collision);
                }
                item[i] = -1;
                continue;
            }
            int nx = p % 7 + xx[belt[p]], ny = p / 7 + yy[belt[p]];
            if (nx < 0 || nx >= 7 || ny < 0 || ny >= 7) {
                item[i] = -1;
                ++waste;
            } else {
                bool blocked = false;
                for (auto pos : item)
                    blocked |= pos == ny * 7 + nx;
                if (!blocked)
                    item[i] = ny * 7 + nx;
            }
        }
    }
    const int goal[] = {3, 4, 5};
    if (delivered >= goal[difficulty_]) {
        Award(500);
        Finish(true);
    } else if (waste >= 3 || elapsed_ > 60)
        Finish(false);
}
int Game090Conveyor::Progress() const {
    const int goal[] = {3, 4, 5};
    return delivered * 100 / goal[difficulty_];
}
void Game090Conveyor::Draw(uint8_t *fb) {
    const int dx[] = {1, 0, -1, 0}, dy[] = {0, 1, 0, -1};
    for (int p = 0; p < 49; ++p) {
        int d = belt[p];
        Cell(fb, p % 7, p / 7, 20 + d * 10, 45, 65, 2, 0);
        Px(fb, p % 7 * 2 + (dx[d] > 0), p / 7 * 2 + (dy[d] > 0), 90, 120, 140);
    }
    Cell(fb, 3, 1, 140, 70, 190, 2, 0);
    Cell(fb, 6, 3, 50, 190, 100, 2, 0);
    for (int i = 0; i < 4; ++i)
        if (item[i] >= 0)
            Cell(fb, item[i] % 7, item[i] / 7, processed[i] ? 65 : 245, processed[i] ? 185 : 170,
                 processed[i] ? 245 : 55, 2, 0);
    Px(fb, x * 2, y * 2, 255, 255, 255);
}

} // namespace arcade
