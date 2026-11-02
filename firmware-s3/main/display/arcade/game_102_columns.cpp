#include "game_102_columns.h"
#include <cstring>
#include <algorithm>

namespace arcade {

Game102Columns::Game102Columns() {
    Reset();
}

void Game102Columns::Init() {
    Reset();
}

void Game102Columns::Reset() {
    score_ = 0;
    level_ = 1;
    matches_cleared_ = 0;
    chain_count_ = 0;
    state_ = STATE_FALLING;
    state_timer_ = 0.0f;
    fall_speed_ = 1.5f;
    move_cooldown_ = 0.0f;

    std::memset(board_, 0, sizeof(board_));
    std::memset(matched_mask_, 0, sizeof(matched_mask_));

    SpawnNewColumn();
}

void Game102Columns::SpawnNewColumn() {
    cur_col_ = 2; // Center-left column
    cur_y_ = 2.0f; // Bottom gem starts at row 2

    // Deterministic pseudo-random generation based on score & level
    static uint32_t seed = 0x5E6A1990;
    auto next_gem = []() -> uint8_t {
        seed = seed * 1664525u + 1013904223u;
        return static_cast<uint8_t>((seed % NUM_GEM_TYPES) + 1);
    };

    cur_gems_[0] = next_gem();
    cur_gems_[1] = next_gem();
    cur_gems_[2] = next_gem();

    // Check if spawn location is blocked -> Game Over
    if (board_[2][cur_col_] != 0 || board_[1][cur_col_] != 0 || board_[0][cur_col_] != 0) {
        state_ = STATE_GAME_OVER;
        state_timer_ = 0.0f;
    }
}

void Game102Columns::CycleCurrentColumn() {
    uint8_t temp = cur_gems_[2];
    cur_gems_[2] = cur_gems_[1];
    cur_gems_[1] = cur_gems_[0];
    cur_gems_[0] = temp;
}

void Game102Columns::ForcePlaceColumn(int col, int base_row, uint8_t g0, uint8_t g1, uint8_t g2) {
    if (col >= 0 && col < BOARD_COLS && base_row >= 2 && base_row < BOARD_ROWS) {
        board_[base_row - 2][col] = g0;
        board_[base_row - 1][col] = g1;
        board_[base_row][col] = g2;
    }
}

bool Game102Columns::CheckPlacementCollision(int col, int row_bot) const {
    if (row_bot >= BOARD_ROWS) return true;
    if (col < 0 || col >= BOARD_COLS) return true;
    if (row_bot >= 0 && board_[row_bot][col] != 0) return true;
    return false;
}

void Game102Columns::LockCurrentColumn() {
    int row_bot = static_cast<int>(cur_y_);
    // Bottom gem at row_bot, mid at row_bot - 1, top at row_bot - 2
    if (row_bot >= 0 && row_bot < BOARD_ROWS) board_[row_bot][cur_col_] = cur_gems_[2];
    if (row_bot - 1 >= 0 && row_bot - 1 < BOARD_ROWS) board_[row_bot - 1][cur_col_] = cur_gems_[1];
    if (row_bot - 2 >= 0 && row_bot - 2 < BOARD_ROWS) board_[row_bot - 2][cur_col_] = cur_gems_[0];

    chain_count_ = 0;
    if (FindMatches()) {
        state_ = STATE_FLASHING_MATCH;
        state_timer_ = 0.0f;
    } else {
        SpawnNewColumn();
    }
}

bool Game102Columns::FindMatches() {
    std::memset(matched_mask_, 0, sizeof(matched_mask_));
    bool found = false;

    // 1. Horizontal matches (r, c), (r, c+1), (r, c+2)
    for (int r = 0; r < BOARD_ROWS; ++r) {
        for (int c = 0; c < BOARD_COLS - 2; ++c) {
            uint8_t g = board_[r][c];
            if (g != 0 && board_[r][c + 1] == g && board_[r][c + 2] == g) {
                matched_mask_[r][c] = true;
                matched_mask_[r][c + 1] = true;
                matched_mask_[r][c + 2] = true;
                found = true;
            }
        }
    }

    // 2. Vertical matches (r, c), (r+1, c), (r+2, c)
    for (int r = 0; r < BOARD_ROWS - 2; ++r) {
        for (int c = 0; c < BOARD_COLS; ++c) {
            uint8_t g = board_[r][c];
            if (g != 0 && board_[r + 1][c] == g && board_[r + 2][c] == g) {
                matched_mask_[r][c] = true;
                matched_mask_[r + 1][c] = true;
                matched_mask_[r + 2][c] = true;
                found = true;
            }
        }
    }

    // 3. Diagonal Down-Right (r, c), (r+1, c+1), (r+2, c+2)
    for (int r = 0; r < BOARD_ROWS - 2; ++r) {
        for (int c = 0; c < BOARD_COLS - 2; ++c) {
            uint8_t g = board_[r][c];
            if (g != 0 && board_[r + 1][c + 1] == g && board_[r + 2][c + 2] == g) {
                matched_mask_[r][c] = true;
                matched_mask_[r + 1][c + 1] = true;
                matched_mask_[r + 2][c + 2] = true;
                found = true;
            }
        }
    }

    // 4. Diagonal Down-Left (r, c), (r+1, c-1), (r+2, c-2)
    for (int r = 0; r < BOARD_ROWS - 2; ++r) {
        for (int c = 2; c < BOARD_COLS; ++c) {
            uint8_t g = board_[r][c];
            if (g != 0 && board_[r + 1][c - 1] == g && board_[r + 2][c - 2] == g) {
                matched_mask_[r][c] = true;
                matched_mask_[r + 1][c - 1] = true;
                matched_mask_[r + 2][c - 2] = true;
                found = true;
            }
        }
    }

    return found;
}

void Game102Columns::ClearMatches() {
    int count = 0;
    for (int r = 0; r < BOARD_ROWS; ++r) {
        for (int c = 0; c < BOARD_COLS; ++c) {
            if (matched_mask_[r][c]) {
                board_[r][c] = 0;
                count++;
            }
        }
    }
    score_ += count * 100 * (chain_count_ + 1);
    matches_cleared_ += count;
    level_ = 1 + (matches_cleared_ / 15);
    fall_speed_ = 1.5f + static_cast<float>(level_) * 0.4f;
}

bool Game102Columns::ApplyGravityCollapse() {
    bool shifted = false;
    for (int c = 0; c < BOARD_COLS; ++c) {
        int write_row = BOARD_ROWS - 1;
        for (int r = BOARD_ROWS - 1; r >= 0; --r) {
            if (board_[r][c] != 0) {
                if (write_row != r) {
                    board_[write_row][c] = board_[r][c];
                    board_[r][c] = 0;
                    shifted = true;
                }
                write_row--;
            }
        }
    }
    return shifted;
}

void Game102Columns::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;
    move_cooldown_ -= dt;

    if (state_ == STATE_FLASHING_MATCH) {
        if (state_timer_ > 0.45f) {
            ClearMatches();
            ApplyGravityCollapse();
            state_ = STATE_COLLAPSING;
            state_timer_ = 0.0f;
        }
        return;
    }

    if (state_ == STATE_COLLAPSING) {
        if (state_timer_ > 0.25f) {
            if (FindMatches()) {
                chain_count_++;
                state_ = STATE_FLASHING_MATCH;
                state_timer_ = 0.0f;
            } else {
                SpawnNewColumn();
                state_ = STATE_FALLING;
                state_timer_ = 0.0f;
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    // Input: Lateral movement
    if (move_cooldown_ <= 0.0f) {
        if (buttons & BTN_LEFT) {
            if (cur_col_ > 0 && !CheckPlacementCollision(cur_col_ - 1, static_cast<int>(cur_y_))) {
                cur_col_--;
                move_cooldown_ = 0.12f;
            }
        } else if (buttons & BTN_RIGHT) {
            if (cur_col_ < BOARD_COLS - 1 && !CheckPlacementCollision(cur_col_ + 1, static_cast<int>(cur_y_))) {
                cur_col_++;
                move_cooldown_ = 0.12f;
            }
        }
    }

    // Button A: Cycle gems in column
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        CycleCurrentColumn();
    }

    // Button B or Down: Drop speed
    float speed = fall_speed_;
    if (buttons & BTN_DOWN) {
        speed = 12.0f;
        score_ += 1;
    } else if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        // Hard drop to lowest open row
        while (!CheckPlacementCollision(cur_col_, static_cast<int>(cur_y_ + 1.0f))) {
            cur_y_ += 1.0f;
            score_ += 2;
        }
        LockCurrentColumn();
        return;
    }

    // Descend
    float next_y = cur_y_ + speed * dt;
    if (CheckPlacementCollision(cur_col_, static_cast<int>(next_y))) {
        // Landed!
        LockCurrentColumn();
    } else {
        cur_y_ = next_y;
    }
}

void Game102Columns::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Color palette for 5 Ancient Jewels:
    // 1: Red Ruby, 2: Green Emerald, 3: Blue Sapphire, 4: Yellow Topaz, 5: Purple Amethyst
    auto get_gem_color = [](uint8_t gem, uint8_t& r, uint8_t& g, uint8_t& b) {
        switch (gem) {
            case 1: r = 255; g = 30;  b = 30;  break; // Ruby
            case 2: r = 30;  g = 220; b = 50;  break; // Emerald
            case 3: r = 30;  g = 100; b = 255; break; // Sapphire
            case 4: r = 255; g = 220; b = 20;  break; // Topaz
            case 5: r = 180; g = 40;  b = 220; break; // Amethyst
            default: r = 0;  g = 0;   b = 0;   break;
        }
    };

    // Classical Greek Temple Marble Columns on sides:
    // Left pillar at x=3, 4; Right pillar at x=11, 12
    for (int y = 0; y < 16; ++y) {
        uint8_t pr = (y % 2 == 0) ? 180 : 150;
        uint8_t pg = (y % 2 == 0) ? 170 : 140;
        uint8_t pb = (y % 2 == 0) ? 140 : 110;
        set_pixel(3, y, pr, pg, pb);
        set_pixel(4, y, pr - 30, pg - 30, pb - 30);
        set_pixel(11, y, pr - 30, pg - 30, pb - 30);
        set_pixel(12, y, pr, pg, pb);
    }
    // Floor pediment at y=15
    for (int x = 3; x <= 12; ++x) {
        set_pixel(x, 15, 200, 190, 160);
    }

    // Playfield Board: x in [5, 10], y in [2, 14]
    for (int r = 0; r < BOARD_ROWS; ++r) {
        for (int c = 0; c < BOARD_COLS; ++c) {
            uint8_t g = board_[r][c];
            if (g != 0) {
                int px = 5 + c;
                int py = 2 + r;
                if (state_ == STATE_FLASHING_MATCH && matched_mask_[r][c]) {
                    // Flash pure white sparkling
                    set_pixel(px, py, 255, 255, 255);
                } else {
                    uint8_t cr, cg, cb;
                    get_gem_color(g, cr, cg, cb);
                    set_pixel(px, py, cr, cg, cb);
                }
            }
        }
    }

    // Falling Column (if in falling state)
    if (state_ == STATE_FALLING) {
        int col_x = 5 + cur_col_;
        int bot_y = 2 + static_cast<int>(cur_y_);

        for (int i = 0; i < 3; ++i) {
            int gem_y = bot_y - (2 - i);
            if (gem_y >= 2 && gem_y <= 14) {
                uint8_t cr, cg, cb;
                get_gem_color(cur_gems_[i], cr, cg, cb);
                set_pixel(col_x, gem_y, cr, cg, cb);
            }
        }
    }

    // Level & Chain indicator on left border (x=0, 1)
    for (int l = 0; l < std::min(level_, 5); ++l) {
        set_pixel(0, 14 - l * 2, 255, 200, 0);
    }
    if (chain_count_ > 0) {
        for (int ch = 0; ch < std::min(chain_count_, 4); ++ch) {
            set_pixel(1, 14 - ch * 2, 255, 60, 200);
        }
    }
}

} // namespace arcade
