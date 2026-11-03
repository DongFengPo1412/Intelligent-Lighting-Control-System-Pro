#include "game_139_amidar.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = (1 << 0);
static constexpr uint16_t BTN_DOWN  = (1 << 1);
static constexpr uint16_t BTN_LEFT  = (1 << 2);
static constexpr uint16_t BTN_RIGHT = (1 << 3);
static constexpr uint16_t BTN_A     = (1 << 4);
static constexpr uint16_t BTN_B     = (1 << 5);

static constexpr int GRID_COLS[4] = {2, 6, 10, 14};
static constexpr int GRID_ROWS[4] = {2, 6, 10, 14};

Game139Amidar::Game139Amidar()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      px_(2.0f),
      py_(2.0f),
      jumps_left_(3),
      jump_timer_(0.0f) {
    Reset();
}

void Game139Amidar::Init() {
    Reset();
}

void Game139Amidar::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game139Amidar::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 2.0f;
    py_ = 2.0f;
    jumps_left_ = 3;
    jump_timer_ = 0.0f;

    std::memset(traced_, 0, sizeof(traced_));
    std::memset(boxes_, 0, sizeof(boxes_));

    traced_[2][2] = true;

    enemies_[0] = {14.0f, 2.0f, 0.0f, 1.0f, 3.0f};
    enemies_[1] = {14.0f, 14.0f, -1.0f, 0.0f, 3.2f};
    enemies_[2] = {2.0f, 14.0f, 0.0f, -1.0f, 3.5f};
}

bool Game139Amidar::IsOnGrid(float x, float y) {
    int ix = static_cast<int>(std::round(x));
    int iy = static_cast<int>(std::round(y));
    if (ix < 2 || ix > 14 || iy < 2 || iy > 14) return false;

    bool on_col = false;
    for (int c : GRID_COLS) {
        if (std::abs(x - c) < 0.2f) { on_col = true; break; }
    }
    bool on_row = false;
    for (int r : GRID_ROWS) {
        if (std::abs(y - r) < 0.2f) { on_row = true; break; }
    }
    return on_col || on_row;
}

void Game139Amidar::CheckBoxes() {
    bool all_cleared = true;
    for (int by = 0; by < 3; ++by) {
        for (int bx = 0; bx < 3; ++bx) {
            if (!boxes_[by][bx]) {
                int x1 = GRID_COLS[bx];
                int x2 = GRID_COLS[bx + 1];
                int y1 = GRID_ROWS[by];
                int y2 = GRID_ROWS[by + 1];

                bool top_t = true, bot_t = true, left_t = true, right_t = true;
                for (int x = x1; x <= x2; ++x) {
                    if (!traced_[y1][x]) top_t = false;
                    if (!traced_[y2][x]) bot_t = false;
                }
                for (int y = y1; y <= y2; ++y) {
                    if (!traced_[y][x1]) left_t = false;
                    if (!traced_[y][x2]) right_t = false;
                }

                if (top_t && bot_t && left_t && right_t) {
                    boxes_[by][bx] = true;
                    score_ += 200;
                } else {
                    all_cleared = false;
                }
            }
        }
    }

    if (all_cleared) {
        score_ += 1000;
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game139Amidar::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // Jump
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            if (jumps_left_ > 0 && jump_timer_ <= 0.0f) {
                jump_timer_ = 0.6f;
                jumps_left_--;
            }
        }
        if (jump_timer_ > 0.0f) {
            jump_timer_ -= dt;
            if (jump_timer_ < 0.0f) jump_timer_ = 0.0f;
        }

        // Movement
        float move_speed = (buttons & BTN_A) ? 8.5f : 6.0f;
        int on_col_idx = -1;
        for (int i = 0; i < 4; ++i) {
            if (std::abs(px_ - GRID_COLS[i]) < 0.2f) { on_col_idx = i; break; }
        }
        int on_row_idx = -1;
        for (int i = 0; i < 4; ++i) {
            if (std::abs(py_ - GRID_ROWS[i]) < 0.2f) { on_row_idx = i; break; }
        }

        float dx = 0.0f;
        float dy = 0.0f;
        if ((buttons & BTN_LEFT) && on_row_idx != -1) {
            dx = -move_speed * dt;
            py_ = static_cast<float>(GRID_ROWS[on_row_idx]);
        } else if ((buttons & BTN_RIGHT) && on_row_idx != -1) {
            dx = move_speed * dt;
            py_ = static_cast<float>(GRID_ROWS[on_row_idx]);
        } else if ((buttons & BTN_UP) && on_col_idx != -1) {
            dy = -move_speed * dt;
            px_ = static_cast<float>(GRID_COLS[on_col_idx]);
        } else if ((buttons & BTN_DOWN) && on_col_idx != -1) {
            dy = move_speed * dt;
            px_ = static_cast<float>(GRID_COLS[on_col_idx]);
        }

        float new_x = std::max(2.0f, std::min(14.0f, px_ + dx));
        float new_y = std::max(2.0f, std::min(14.0f, py_ + dy));

        if (IsOnGrid(new_x, new_y)) {
            px_ = new_x;
            py_ = new_y;

            int ix = static_cast<int>(std::round(px_));
            int iy = static_cast<int>(std::round(py_));
            if (!traced_[iy][ix]) {
                traced_[iy][ix] = true;
                score_ += 5;
                CheckBoxes();
            }
        }

        // Enemies
        for (int i = 0; i < NUM_ENEMIES; ++i) {
            if (jump_timer_ > 0.0f) continue;

            float ex = enemies_[i].x + enemies_[i].dir_x * enemies_[i].speed * dt;
            float ey = enemies_[i].y + enemies_[i].dir_y * enemies_[i].speed * dt;

            if (ex <= 2.0f || ex >= 14.0f || ey <= 2.0f || ey >= 14.0f) {
                ex = std::max(2.0f, std::min(14.0f, ex));
                ey = std::max(2.0f, std::min(14.0f, ey));
                float old_dx = enemies_[i].dir_x;
                enemies_[i].dir_x = -enemies_[i].dir_y;
                enemies_[i].dir_y = old_dx;
            }

            enemies_[i].x = ex;
            enemies_[i].y = ey;

            if (std::abs(px_ - ex) < 0.8f && std::abs(py_ - ey) < 0.8f) {
                if (jump_timer_ <= 0.0f) {
                    if (lives_ > 0) lives_--;
                    state_ = STATE_CAUGHT;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_CAUGHT) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_CAUGHT) {
                if (lives_ > 0) {
                    px_ = 2.0f;
                    py_ = 2.0f;
                    state_ = STATE_PLAYING;
                    state_timer_ = 0.0f;
                } else {
                    state_ = STATE_GAME_OVER;
                    state_timer_ = 0.0f;
                }
            }
        }
    } else if (state_ == STATE_GAME_OVER) {
        state_timer_ += dt;
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
    }
}

void Game139Amidar::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Filled boxes
    for (int by = 0; by < 3; ++by) {
        for (int bx = 0; bx < 3; ++bx) {
            if (boxes_[by][bx]) {
                int x1 = GRID_COLS[bx] + 1;
                int x2 = GRID_COLS[bx + 1] - 1;
                int y1 = GRID_ROWS[by] + 1;
                int y2 = GRID_ROWS[by + 1] - 1;
                for (int y = y1; y <= y2; ++y) {
                    for (int x = x1; x <= x2; ++x) {
                        set_pixel(x, y, 40, 160, 80);
                    }
                }
            }
        }
    }

    // Grid lines
    for (int c : GRID_COLS) {
        for (int y = 2; y <= 14; ++y) {
            if (traced_[y][c]) set_pixel(c, y, 255, 230, 50);
            else set_pixel(c, y, 30, 40, 90);
        }
    }
    for (int r : GRID_ROWS) {
        for (int x = 2; x <= 14; ++x) {
            if (traced_[r][x]) set_pixel(x, r, 255, 230, 50);
            else set_pixel(x, r, 30, 40, 90);
        }
    }

    // Enemies
    for (int i = 0; i < NUM_ENEMIES; ++i) {
        set_pixel(static_cast<int>(std::round(enemies_[i].x)),
                  static_cast<int>(std::round(enemies_[i].y)), 255, 50, 60);
    }

    // Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        if (jump_timer_ > 0.0f) set_pixel(px, py, 255, 255, 255);
        else set_pixel(px, py, 50, 220, 255);
    } else if (state_ == STATE_CAUGHT) {
        set_pixel(px, py, 255, 40, 40);
    }

    // Jumps
    for (int j = 0; j < std::min(static_cast<int>(jumps_left_), 3); ++j) {
        set_pixel(2 + j * 2, 15, 255, 255, 255);
    }
}

} // namespace arcade

