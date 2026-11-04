#include "game_058_program_robot.h"
namespace arcade {
void Game058ProgramRobot::Setup() {
    length_ = 0;
    attempts_ = 3;
    ResetRobot();
}
void Game058ProgramRobot::ResetRobot() {
    x_ = 1;
    y_ = 6;
    heading_ = 0;
    door_ = running_ = false;
    pc_ = 0;
    clock_ = 0;
}
bool Game058ProgramRobot::Wall(int x, int y) const {
    return x < 1 || x > 6 || y < 1 || y > 6 || (y == 2 && x != 3) || (x == 3 && y == 2 && !door_);
}
void Game058ProgramRobot::FailProgram() {
    --attempts_;
    SoundEvent(Sound::Collision);
    ResetRobot();
    if (!attempts_)
        Finish(false);
}
void Game058ProgramRobot::Tick(float dt, uint16_t, uint16_t pressed) {
    if (pressed & KEY_B) {
        if (running_)
            ResetRobot();
        else if (length_)
            --length_;
    }
    if (!running_) {
        const int bits[] = {KEY_UP, KEY_LEFT, KEY_RIGHT, KEY_DOWN}, capacity[] = {20, 17, 14};
        for (int cmd = 0; cmd < 4; ++cmd)
            if ((pressed & bits[cmd]) && length_ < capacity[difficulty_]) {
                program_[length_++] = cmd;
                SoundEvent(Sound::Action, cmd);
            }
        if ((pressed & KEY_A) && length_) {
            ResetRobot();
            running_ = true;
        }
    } else {
        const float interval[] = {.30f, .24f, .18f};
        clock_ += dt;
        if (clock_ >= interval[difficulty_]) {
            clock_ = 0;
            if (pc_ >= length_) {
                FailProgram();
                return;
            }
            int cmd = program_[pc_++];
            if (cmd == 1)
                heading_ = (heading_ + 3) % 4;
            else if (cmd == 2)
                heading_ = (heading_ + 1) % 4;
            else if (cmd == 0) {
                const int dx[] = {0, 1, 0, -1}, dy[] = {-1, 0, 1, 0};
                int nx = x_ + dx[heading_], ny = y_ + dy[heading_];
                if (Wall(nx, ny)) {
                    FailProgram();
                    return;
                }
                x_ = nx;
                y_ = ny;
                if (x_ == 3 && y_ == 4) {
                    door_ = true;
                    SoundEvent(Sound::Hit);
                }
                if (x_ == 6 && y_ == 1 && door_) {
                    Award(1000 + 50 * attempts_);
                    Finish(true);
                    return;
                }
            }
        }
    }
    const int limit[] = {100, 75, 50};
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
void Game058ProgramRobot::Draw(uint8_t *fb) {
    for (int y = 0; y < 8; ++y)
        for (int x = 0; x < 8; ++x) {
            bool wall = Wall(x, y);
            Cell(fb, x, y, wall ? 55 : 8, wall ? 65 : 16, wall ? 85 : 25, 2, 0);
        }
    Cell(fb, 3, 4, 245, 190, 20, 2, 0);
    Cell(fb, 3, 2, door_ ? 20 : 190, door_ ? 160 : 45, door_ ? 170 : 45, 2, 0);
    Cell(fb, 6, 1, 40, 220, 70, 2, 0);
    Cell(fb, x_, y_, 245, 245, 245, 2, 0);
    for (int i = 0; i < 2; ++i) {
        const int dx[] = {i, 1, i, 0}, dy[] = {0, i, 1, i};
        Px(fb, x_ * 2 + dx[heading_], y_ * 2 + dy[heading_], 60, 180, 255);
    }
    const int palette[][3] = {{40, 230, 100}, {255, 180, 20}, {40, 160, 255}, {150, 70, 200}};
    int offset = std::max(0, length_ - 16);
    for (int i = offset; i < length_; ++i) {
        auto c = palette[program_[i]];
        if (running_ && i == pc_)
            Px(fb, i - offset, 0, 255, 255, 255);
        else
            Px(fb, i - offset, 0, c[0], c[1], c[2]);
    }
}
} // namespace arcade
