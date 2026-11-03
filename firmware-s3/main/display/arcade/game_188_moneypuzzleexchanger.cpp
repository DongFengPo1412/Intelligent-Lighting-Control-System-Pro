#include "game_188_moneypuzzleexchanger.h"
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_LEFT  = 1 << 2;
static constexpr uint16_t BTN_RIGHT = 1 << 3;
static constexpr uint16_t BTN_A     = 1 << 4; // Suction / Grab
static constexpr uint16_t BTN_B     = 1 << 5; // Toss / Shoot

Game188MoneyPuzzleExchanger::Game188MoneyPuzzleExchanger() {
    Init();
}

void Game188MoneyPuzzleExchanger::Init() {
    Reset();
}

void Game188MoneyPuzzleExchanger::Reset() {
    score_ = 0;
    stage_ = 1;
    InitStage();
}

void Game188MoneyPuzzleExchanger::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    cursor_col_ = 3;
    cursor_cooldown_ = 0.0f;
    held_denom_ = 0;
    held_count_ = 0;
    max_drop_timer_ = std::max(4.0f, 12.0f - stage_ * 1.5f);
    drop_timer_ = max_drop_timer_;

    for (int c = 0; c < COLS; ++c) {
        col_len_[c] = 0;
    }

    uint16_t preset[3][COLS] = {
        {1, 5, 1, 5, 1, 5, 1},
        {10, 50, 10, 50, 10, 50, 10},
        {100, 500, 100, 500, 100, 500, 100}
    };

    for (int r = 0; r < 3; ++r) {
        for (int c = 0; c < COLS; ++c) {
            grid_[c][col_len_[c]++] = preset[r][c];
        }
    }
}

void Game188MoneyPuzzleExchanger::PushCeilingRow() {
    static const uint16_t denoms[] = {1, 5, 10, 50, 100};
    for (int c = 0; c < COLS; ++c) {
        uint16_t new_coin = denoms[(c + (score_ / 50) + stage_) % 5];
        // Shift existing down
        for (int r = col_len_[c]; r > 0; --r) {
            grid_[c][r] = grid_[c][r - 1];
        }
        grid_[c][0] = new_coin;
        col_len_[c]++;

        if (col_len_[c] >= 13) {
            state_ = STATE_GAME_OVER;
            return;
        }
    }
}

bool Game188MoneyPuzzleExchanger::ResolveExchanges() {
    bool changed = false;

    for (int c = 0; c < COLS; ++c) {
        int len = col_len_[c];
        int i = 0;
        while (i < len) {
            uint16_t val = grid_[c][i];
            int run = 1;
            while (i + run < len && grid_[c][i + run] == val) {
                run++;
            }

            int req = (val == 1 || val == 10 || val == 100) ? 5 : 2;
            if (run >= req) {
                changed = true;
                // Delete merged coins
                int shift = req;
                if (val == 500) {
                    score_ += 10000;
                    // Simply delete
                    for (int k = i; k < len - shift; ++k) {
                        grid_[c][k] = grid_[c][k + shift];
                    }
                    col_len_[c] -= shift;
                } else {
                    uint16_t next_val = 5;
                    if (val == 1)   { next_val = 5;   score_ += 50; }
                    if (val == 5)   { next_val = 10;  score_ += 100; }
                    if (val == 10)  { next_val = 50;  score_ += 500; }
                    if (val == 50)  { next_val = 100; score_ += 1000; }
                    if (val == 100) { next_val = 500; score_ += 5000; }

                    grid_[c][i] = next_val;
                    for (int k = i + 1; k < len - (shift - 1); ++k) {
                        grid_[c][k] = grid_[c][k + (shift - 1)];
                    }
                    col_len_[c] -= (shift - 1);
                }
                break;
            } else {
                i += run;
            }
        }
    }

    int total_coins = 0;
    for (int c = 0; c < COLS; ++c) total_coins += col_len_[c];
    if (total_coins == 0) {
        if (state_ != STATE_STAGE_CLEAR) {
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 2.0f;
            score_ += 20000;
        }
        return false;
    }

    return changed;
}

void Game188MoneyPuzzleExchanger::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
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

    // Cursor move
    uint16_t pressed = buttons & ~prev_buttons;
    if ((pressed & BTN_LEFT) || ((buttons & BTN_LEFT) && cursor_cooldown_ <= 0.0f)) {
        if (cursor_col_ > 0) {
            cursor_col_--;
            cursor_cooldown_ = 0.18f;
        }
    } else if ((pressed & BTN_RIGHT) || ((buttons & BTN_RIGHT) && cursor_cooldown_ <= 0.0f)) {
        if (cursor_col_ < COLS - 1) {
            cursor_col_++;
            cursor_cooldown_ = 0.18f;
        }
    }

    if (cursor_cooldown_ > 0.0f) {
        cursor_cooldown_ -= dt;
    }

    // Suction (Button A)
    if ((pressed & BTN_A) && held_count_ == 0) {
        int len = col_len_[cursor_col_];
        if (len > 0) {
            uint16_t denom = grid_[cursor_col_][len - 1];
            uint8_t count = 0;
            while (col_len_[cursor_col_] > 0 && grid_[cursor_col_][col_len_[cursor_col_] - 1] == denom) {
                col_len_[cursor_col_]--;
                count++;
            }
            held_denom_ = denom;
            held_count_ = count;
        }
    }
    // Toss (Button B)
    else if ((pressed & BTN_B) && held_count_ > 0) {
        for (int k = 0; k < held_count_; ++k) {
            if (col_len_[cursor_col_] < MAX_ROWS) {
                grid_[cursor_col_][col_len_[cursor_col_]++] = held_denom_;
            }
        }
        held_denom_ = 0;
        held_count_ = 0;

        while (ResolveExchanges()) {}

        if (col_len_[cursor_col_] >= 13) {
            state_ = STATE_GAME_OVER;
            return;
        }
    }

    // Ceiling push
    drop_timer_ -= dt;
    if (drop_timer_ <= 0.0f) {
        drop_timer_ = max_drop_timer_;
        PushCeilingRow();
    }
}

void Game188MoneyPuzzleExchanger::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    auto get_coin_rgb = [](uint16_t denom, uint8_t& r, uint8_t& g, uint8_t& b) {
        switch (denom) {
            case 1:   r = 180; g = 180; b = 190; break;
            case 5:   r = 220; g = 160; b = 40;  break;
            case 10:  r = 180; g = 80;  b = 30;  break;
            case 50:  r = 200; g = 200; b = 220; break;
            case 100: r = 240; g = 240; b = 255; break;
            case 500: r = 255; g = 215; b = 0;   break;
            default:  r = 100; g = 100; b = 100; break;
        }
    };

    // Red hazard line at y = 13
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 13, 180, 20, 20);
    }

    // Coins
    for (int c = 0; c < COLS; ++c) {
        int x = 1 + c * 2;
        for (int row = 0; row < col_len_[c] && row < 13; ++row) {
            uint8_t cr, cg, cb;
            get_coin_rgb(grid_[c][row], cr, cg, cb);
            set_pixel(x, row, cr, cg, cb);
            set_pixel(x + 1, row, (cr > 40 ? cr - 40 : 0), (cg > 40 ? cg - 40 : 0), (cb > 40 ? cb - 40 : 0));
        }
    }

    // Cursor at y = 14..15
    int cx = 1 + cursor_col_ * 2;
    set_pixel(cx, 14, 40, 120, 240);
    set_pixel(cx + 1, 14, 40, 120, 240);
    set_pixel(cx, 15, 220, 40, 40);
    set_pixel(cx + 1, 15, 220, 40, 40);

    if (held_count_ > 0) {
        uint8_t hr, hg, hb;
        get_coin_rgb(held_denom_, hr, hg, hb);
        set_pixel(cx, 14, hr, hg, hb);
        set_pixel(cx + 1, 14, hr, hg, hb);
    }
}

} // namespace arcade
