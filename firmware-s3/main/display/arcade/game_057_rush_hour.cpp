#include "game_057_rush_hour.h"
namespace arcade {
void Game057RushHour::Setup() {
    const int initial[7][4] = {{0, 2, 2, 0}, {2, 0, 3, 1}, {3, 0, 3, 0}, {5, 2, 2, 1},
                               {1, 4, 2, 0}, {0, 4, 2, 1}, {3, 5, 2, 0}};
    memcpy(cars_, initial, sizeof(cars_));
    selected_ = moves_ = 0;
}
bool Game057RushHour::Occupied(int x, int y, int ignore) const {
    for (int i = 0; i < 7; ++i)
        if (i != ignore) {
            auto c = cars_[i];
            for (int k = 0; k < c[2]; ++k)
                if (c[0] + (c[3] ? 0 : k) == x && c[1] + (c[3] ? k : 0) == y)
                    return true;
        }
    return false;
}
void Game057RushHour::Tick(float, uint16_t down, uint16_t pressed) {
    if (pressed & KEY_A) {
        selected_ = (selected_ + 1) % 7;
        SoundEvent(Sound::Action, selected_);
    } else if (pressed & KEY_B) {
        selected_ = (selected_ + 6) % 7;
        SoundEvent(Sound::Action, selected_);
    }
    int dx, dy;
    Direction(down, pressed, dx, dy);
    auto c = cars_[selected_];
    int delta = c[3] ? dy : dx;
    if (delta) {
        int nx = c[0] + (c[3] ? 0 : delta), ny = c[1] + (c[3] ? delta : 0);
        bool valid = true;
        for (int k = 0; k < c[2]; ++k) {
            int x = nx + (c[3] ? 0 : k), y = ny + (c[3] ? k : 0);
            if (x < 0 || x >= 6 || y < 0 || y >= 6 || Occupied(x, y, selected_))
                valid = false;
        }
        if (valid) {
            c[0] = nx;
            c[1] = ny;
            ++moves_;
            SoundEvent(Sound::Hit, selected_);
            if (cars_[0][0] == 4) {
                Award(std::max(100, 1200 - moves_ * 20));
                Finish(true);
                return;
            }
        }
    }
    const int budget[] = {50, 30, 16}, limit[] = {120, 90, 60};
    if (moves_ >= budget[difficulty_] || elapsed_ > limit[difficulty_])
        Finish(false);
}
void Game057RushHour::Draw(uint8_t *fb) {
    const int colors[][3] = {{245, 55, 55},  {40, 180, 255}, {245, 200, 35}, {140, 70, 230},
                             {40, 220, 120}, {230, 100, 40}, {200, 80, 160}};
    for (int y = 0; y < 6; ++y)
        for (int x = 0; x < 6; ++x)
            Cell(fb, x, y, 20, 25, 32);
    for (int i = 0; i < 7; ++i) {
        auto c = cars_[i];
        auto color = colors[i];
        for (int k = 0; k < c[2]; ++k)
            Cell(fb, c[0] + (c[3] ? 0 : k), c[1] + (c[3] ? k : 0), color[0], color[1], color[2]);
    }
    auto c = cars_[selected_];
    Px(fb, 2 + c[0] * 2, 2 + c[1] * 2, 255, 255, 255);
    Px(fb, 15, 6, 30, 255, 70);
    Px(fb, 15, 7, 30, 255, 70);
}
} // namespace arcade
