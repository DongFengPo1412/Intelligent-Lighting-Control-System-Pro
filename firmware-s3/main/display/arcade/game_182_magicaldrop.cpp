#include "game_182_magicaldrop.h"
#include <cstring>
#include <cmath>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = (1 << 0);
static constexpr uint16_t BTN_DOWN  = (1 << 1);
static constexpr uint16_t BTN_LEFT  = (1 << 2);
static constexpr uint16_t BTN_RIGHT = (1 << 3);
static constexpr uint16_t BTN_A     = (1 << 4);
static constexpr uint16_t BTN_B     = (1 << 5);

Game182MagicalDrop::Game182MagicalDrop() {
    Reset();
}

void Game182MagicalDrop::Init() {
    Reset();
}

void Game182MagicalDrop::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game182MagicalDrop::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    col_ = 7;
    held_color_ = COLOR_NONE;
    held_count_ = 0;
    drop_timer_ = std::max(3.5f, 6.0f - stage_ * 0.4f);
    cleared_target_ = 25 + stage_ * 5;
    bubbles_cleared_ = 0;

    std::memset(grid_, 0, sizeof(grid_));

    static const uint8_t pattern[] = {COLOR_RED, COLOR_BLUE, COLOR_GREEN, COLOR_YELLOW};
    for (int y = 1; y <= 5; ++y) {
        for (int x = 3; x <= 12; ++x) {
            grid_[y][x] = pattern[(x * 2 + y * 3 + stage_) % 4];
        }
    }
}

void Game182MagicalDrop::PullBubbles(int x) {
    int lowest_y = -1;
    for (int y = 13; y >= 0; --y) {
        if (grid_[y][x] != COLOR_NONE) {
            lowest_y = y;
            break;
        }
    }

    if (lowest_y == -1) return;

    uint8_t bubble_col = grid_[lowest_y][x];
    if (held_color_ == COLOR_NONE || held_color_ == bubble_col) {
        held_color_ = bubble_col;
        while (lowest_y >= 0 && grid_[lowest_y][x] == held_color_ && held_count_ < 4) {
            grid_[lowest_y][x] = COLOR_NONE;
            held_count_++;
            lowest_y--;
        }
    }
}

void Game182MagicalDrop::FlingBubbles(int x) {
    if (held_count_ == 0 || held_color_ == COLOR_NONE) return;

    int insert_y = -1;
    for (int y = 0; y < 14; ++y) {
        if (grid_[y][x] == COLOR_NONE) {
            insert_y = y;
            break;
        }
    }

    if (insert_y == -1) return;

    while (held_count_ > 0 && insert_y < 14) {
        grid_[insert_y][x] = held_color_;
        held_count_--;
        insert_y++;
    }

    held_color_ = COLOR_NONE;
    held_count_ = 0;

    CheckColumnMatches(x);
}

void Game182MagicalDrop::CheckColumnMatches(int x) {
    int y = 0;
    while (y < 14) {
        uint8_t c = grid_[y][x];
        if (c != COLOR_NONE) {
            int run_start = y;
            while (y < 14 && grid_[y][x] == c) {
                y++;
            }
            int run_len = y - run_start;
            if (run_len >= 3) {
                for (int ry = run_start; ry < y; ++ry) {
                    grid_[ry][x] = COLOR_NONE;
                }
                score_ += run_len * 100;
                bubbles_cleared_ += run_len;

                if (bubbles_cleared_ >= cleared_target_) {
                    state_ = STATE_STAGE_CLEAR;
                    state_timer_ = 2.0f;
                    score_ += 2500;
                    return;
                }
            }
        } else {
            y++;
        }
    }
}

void Game182MagicalDrop::DropCeilingRow() {
    for (int y = 13; y > 0; --y) {
        for (int x = 3; x <= 12; ++x) {
            grid_[y][x] = grid_[y - 1][x];
        }
    }

    for (int x = 3; x <= 12; ++x) {
        if (grid_[13][x] != COLOR_NONE) {
            lives_--;
            state_ = STATE_FLOOR_CRUSHED;
            state_timer_ = 1.2f;
            return;
        }
    }

    static const uint8_t pattern[] = {COLOR_RED, COLOR_BLUE, COLOR_GREEN, COLOR_YELLOW};
    for (int x = 3; x <= 12; ++x) {
        grid_[0][x] = pattern[(x + score_ / 100) % 4];
    }
}

void Game182MagicalDrop::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_FLOOR_CRUSHED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                held_color_ = COLOR_NONE;
                held_count_ = 0;
                InitStage();
            } else {
                state_ = STATE_GAME_OVER;
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if (((buttons & BTN_A) && !(prev_buttons & BTN_A)) ||
            ((buttons & BTN_B) && !(prev_buttons & BTN_B))) {
            Reset();
        }
        return;
    }

    if ((buttons & BTN_LEFT) && !(prev_buttons & BTN_LEFT)) {
        col_ = std::max(3, col_ - 1);
    } else if ((buttons & BTN_RIGHT) && !(prev_buttons & BTN_RIGHT)) {
        col_ = std::min(12, col_ + 1);
    }

    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        PullBubbles(col_);
    }

    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        FlingBubbles(col_);
    }

    drop_timer_ -= dt;
    if (drop_timer_ <= 0.0f) {
        drop_timer_ = std::max(3.5f, 6.0f - stage_ * 0.4f);
        DropCeilingRow();
    }
}

void Game182MagicalDrop::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    auto get_color = [](uint8_t c, uint8_t& r, uint8_t& g, uint8_t& b) {
        switch (c) {
            case COLOR_RED:    r = 255; g = 30;  b = 40;  break;
            case COLOR_BLUE:   r = 40;  g = 120; b = 255; break;
            case COLOR_GREEN:  r = 40;  g = 220; b = 50;  break;
            case COLOR_YELLOW: r = 255; g = 220; b = 30;  break;
            default:           r = 200; g = 200; b = 200; break;
        }
    };

    for (int y = 0; y < 16; ++y) {
        set_pixel(2, y, 60, 40, 80);
        set_pixel(13, y, 60, 40, 80);
    }
    for (int x = 2; x <= 13; ++x) set_pixel(x, 13, 80, 20, 40);

    for (int y = 0; y < 13; ++y) {
        for (int x = 3; x <= 12; ++x) {
            uint8_t c = grid_[y][x];
            if (c != COLOR_NONE) {
                uint8_t r, g, b;
                get_color(c, r, g, b);
                set_pixel(x, y, r, g, b);
            }
        }
    }

    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(col_, 14, 255, 255, 255);
        set_pixel(col_, 15, 255, 60, 60);
        if (held_count_ > 0) {
            uint8_t hr, hg, hb;
            get_color(held_color_, hr, hg, hb);
            set_pixel(col_, 13, hr, hg, hb);
            if (held_count_ > 1) set_pixel(col_ - 1, 14, hr, hg, hb);
            if (held_count_ > 2) set_pixel(col_ + 1, 14, hr, hg, hb);
        }
    } else if (state_ == STATE_FLOOR_CRUSHED) {
        set_pixel(col_, 14, 255, 80, 0);
    }
}

} // namespace arcade
