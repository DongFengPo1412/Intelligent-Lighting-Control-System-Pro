#include "game_143_plotting.h"
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

Game143Plotting::Game143Plotting()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      time_left_(45.0f),
      blocks_cleared_(0),
      target_blocks_(12),
      py_(6.0f),
      hand_block_(COLOR_RED),
      wildcards_left_(2) {
    projectile_.active = false;
    Reset();
}

void Game143Plotting::Init() {
    Reset();
}

void Game143Plotting::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game143Plotting::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    time_left_ = 45.0f;
    blocks_cleared_ = 0;
    target_blocks_ = 12 + (level_ - 1) * 3;
    py_ = 6.0f;
    hand_block_ = COLOR_RED;
    wildcards_left_ = 2;
    projectile_.active = false;

    std::memset(board_, 0, sizeof(board_));

    uint8_t pattern[6][6] = {
        {1, 1, 2, 2, 3, 3},
        {2, 2, 3, 3, 1, 1},
        {3, 3, 1, 1, 2, 2},
        {1, 2, 3, 1, 2, 3},
        {2, 3, 1, 2, 3, 1},
        {3, 1, 2, 3, 1, 2}
    };

    for (int r = 0; r < 6; ++r) {
        int y = 5 + r;
        for (int c = 0; c < 6; ++c) {
            int x = 7 + c;
            board_[y][x] = pattern[r][c];
        }
    }
}

void Game143Plotting::ApplyGravity() {
    for (int x = 6; x < 15; ++x) {
        int write_y = 13;
        for (int y = 13; y >= 3; --y) {
            if (board_[y][x] != 0) {
                uint8_t val = board_[y][x];
                board_[y][x] = 0;
                board_[write_y][x] = val;
                write_y--;
            }
        }
    }
}

void Game143Plotting::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        time_left_ -= dt;
        if (time_left_ <= 0.0f) {
            time_left_ = 0.0f;
            if (lives_ > 0) lives_--;
            state_ = STATE_NO_MOVES;
            state_timer_ = 0.0f;
            return;
        }

        // Paddle movement
        float rail_speed = 8.0f;
        if (buttons & BTN_UP)   py_ = std::max(3.0f, py_ - rail_speed * dt);
        if (buttons & BTN_DOWN) py_ = std::min(12.0f, py_ + rail_speed * dt);

        // Fire normal (BTN_A)
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            if (!projectile_.active) {
                int row_y = static_cast<int>(std::round(py_));
                projectile_.x = 2.0f;
                projectile_.y = static_cast<float>(row_y);
                projectile_.color = hand_block_;
                projectile_.is_wildcard = false;
                projectile_.active = true;
            }
        }

        // Fire wildcard (BTN_B)
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            if (!projectile_.active && wildcards_left_ > 0) {
                wildcards_left_--;
                int row_y = static_cast<int>(std::round(py_));
                projectile_.x = 2.0f;
                projectile_.y = static_cast<float>(row_y);
                projectile_.color = 99;
                projectile_.is_wildcard = true;
                projectile_.active = true;
            }
        }

        // Update projectile
        if (projectile_.active) {
            projectile_.x += 20.0f * dt;
            int tx = static_cast<int>(std::round(projectile_.x));
            int ty = static_cast<int>(std::round(projectile_.y));

            if (tx >= 14) {
                projectile_.active = false;
            } else if (tx >= 6) {
                if (board_[ty][tx] != 0) {
                    uint8_t hit_color = board_[ty][tx];
                    if (projectile_.is_wildcard) {
                        for (int x = tx; x < 14; ++x) {
                            if (board_[ty][x] != 0) {
                                board_[ty][x] = 0;
                                blocks_cleared_++;
                                score_ += 100;
                            }
                        }
                        ApplyGravity();
                        projectile_.active = false;
                    } else if (projectile_.color == hit_color) {
                        int cur_x = tx;
                        while (cur_x < 14 && board_[ty][cur_x] == hit_color) {
                            board_[ty][cur_x] = 0;
                            blocks_cleared_++;
                            score_ += 50;
                            cur_x++;
                        }
                        if (cur_x < 14 && board_[ty][cur_x] != 0) {
                            hand_block_ = board_[ty][cur_x];
                        }
                        ApplyGravity();
                        projectile_.active = false;
                    } else {
                        board_[ty][tx] = projectile_.color;
                        hand_block_ = hit_color;
                        score_ += 20;
                        projectile_.active = false;
                    }

                    if (blocks_cleared_ >= target_blocks_) {
                        score_ += 1000;
                        state_ = STATE_STAGE_CLEAR;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            }
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_NO_MOVES) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_NO_MOVES) {
                if (lives_ > 0) {
                    InitLevel();
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

void Game143Plotting::Render(uint8_t* fb) {
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

    auto get_color_rgb = [](uint8_t c, uint8_t& r, uint8_t& g, uint8_t& b) {
        if (c == COLOR_RED) { r = 240; g = 40; b = 40; }
        else if (c == COLOR_BLUE) { r = 40; g = 120; b = 240; }
        else if (c == COLOR_GREEN) { r = 40; g = 220; b = 60; }
        else if (c == COLOR_YELLOW) { r = 240; g = 220; b = 40; }
        else if (c == 99) { r = 255; g = 255; b = 255; }
        else { r = 0; g = 0; b = 0; }
    };

    // Rail
    for (int y = 2; y <= 13; ++y) set_pixel(0, y, 60, 60, 80);

    // Paddle & Hand
    int py_i = static_cast<int>(std::round(py_));
    set_pixel(1, py_i, 220, 220, 240);
    set_pixel(1, py_i - 1, 160, 160, 180);
    set_pixel(1, py_i + 1, 160, 160, 180);

    uint8_t hr = 0, hg = 0, hb = 0;
    get_color_rgb(hand_block_, hr, hg, hb);
    set_pixel(2, py_i, hr, hg, hb);

    // Projectile
    if (projectile_.active) {
        int px = static_cast<int>(std::round(projectile_.x));
        int py = static_cast<int>(std::round(projectile_.y));
        uint8_t pr = 0, pg = 0, pb = 0;
        get_color_rgb(projectile_.color, pr, pg, pb);
        set_pixel(px, py, pr, pg, pb);
        set_pixel(px - 1, py, 255, 255, 255);
    }

    // Board
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (board_[y][x] != 0) {
                uint8_t br = 0, bg = 0, bb = 0;
                get_color_rgb(board_[y][x], br, bg, bb);
                set_pixel(x, y, br, bg, bb);
            }
        }
    }

    // Right wall
    for (int y = 2; y <= 13; ++y) set_pixel(14, y, 90, 70, 60);

    // Wildcards
    for (int w = 0; w < std::min(static_cast<int>(wildcards_left_), 3); ++w) {
        set_pixel(2 + w * 2, 15, 255, 255, 255);
    }

    // Progress
    int quota_p = static_cast<int>(std::round((static_cast<float>(blocks_cleared_) / target_blocks_) * 15.0f));
    for (int x = 0; x <= quota_p && x < 16; ++x) {
        set_pixel(x, 0, 50, 220, 60);
    }
}

} // namespace arcade

