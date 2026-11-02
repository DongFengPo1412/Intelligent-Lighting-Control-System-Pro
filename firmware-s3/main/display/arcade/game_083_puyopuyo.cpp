#include "game_083_puyopuyo.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <queue>

namespace arcade {

Game083PuyoPuyo::Game083PuyoPuyo() {
    Reset();
}

void Game083PuyoPuyo::Init() {
    Reset();
}

void Game083PuyoPuyo::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    drop_timer_ = 0.0f;
    drop_interval_ = 0.75f;
    score_ = 0;
    current_chain_ = 0;
    max_chain_ = 0;

    ClearBoard();
    SpawnPair();
}

void Game083PuyoPuyo::ClearBoard() {
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            grid_[r][c] = PUYO_EMPTY;
        }
    }
}

Game083PuyoPuyo::PuyoColor Game083PuyoPuyo::GetCell(int col, int row) const {
    if (col >= 0 && col < COLS && row >= 0 && row < ROWS) {
        return grid_[row][col];
    }
    return PUYO_EMPTY;
}

void Game083PuyoPuyo::SpawnPair() {
    cur_col_ = 2;
    cur_row_ = 1.0f;
    sub_offset_x_ = 0;
    sub_offset_y_ = -1;

    PuyoColor colors[] = {PUYO_RED, PUYO_GREEN, PUYO_BLUE, PUYO_YELLOW};
    puyo_main_ = colors[std::rand() % 4];
    puyo_sub_ = colors[std::rand() % 4];

    // Check game over at spawn point (col 2, top row 1)
    if (grid_[1][2] != PUYO_EMPTY) {
        state_ = STATE_GAME_OVER;
        state_timer_ = 0.0f;
    }
}

void Game083PuyoPuyo::RotatePair(int dir) {
    int old_ox = sub_offset_x_;
    int old_oy = sub_offset_y_;

    int new_ox = 0;
    int new_oy = 0;

    if (dir > 0) { // Clockwise: (0,-1) -> (1,0) -> (0,1) -> (-1,0)
        new_ox = -old_oy;
        new_oy = old_ox;
    } else { // Counter-clockwise
        new_ox = old_oy;
        new_oy = -old_ox;
    }

    int test_col = cur_col_ + new_ox;
    int test_row = static_cast<int>(cur_row_) + new_oy;

    // Boundary & collision kick
    if (test_col < 0) {
        if (cur_col_ + 1 < COLS && grid_[static_cast<int>(cur_row_)][cur_col_ + 1] == PUYO_EMPTY) {
            cur_col_++;
        } else {
            return;
        }
    } else if (test_col >= COLS) {
        if (cur_col_ - 1 >= 0 && grid_[static_cast<int>(cur_row_)][cur_col_ - 1] == PUYO_EMPTY) {
            cur_col_--;
        } else {
            return;
        }
    }

    test_col = cur_col_ + new_ox;
    if (test_row >= 0 && test_row < ROWS && test_col >= 0 && test_col < COLS) {
        if (grid_[test_row][test_col] == PUYO_EMPTY) {
            sub_offset_x_ = new_ox;
            sub_offset_y_ = new_oy;
        }
    }
}

void Game083PuyoPuyo::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if (state_timer_ > 2.5f && (buttons & (BUTTON_A | BUTTON_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_CHAIN_RESOLVE) {
        if (state_timer_ > 0.35f) {
            state_timer_ = 0.0f;
            bool fell = ApplyGravity();
            if (fell) return; // Allow falling animation tick

            bool matched = CheckMatches();
            if (matched) {
                current_chain_++;
                if (current_chain_ > max_chain_) max_chain_ = current_chain_;
                score_ += 100 * (1 << current_chain_);
            } else {
                // Done chaining, return to play or game over
                current_chain_ = 0;
                if (grid_[1][2] != PUYO_EMPTY) {
                    state_ = STATE_GAME_OVER;
                } else {
                    state_ = STATE_PLAYING;
                    SpawnPair();
                }
            }
        }
        return;
    }

    // STATE_PLAYING
    // Lateral controls
    if ((buttons & BUTTON_LEFT) && !(prev_buttons & BUTTON_LEFT)) {
        if (cur_col_ > 0 && grid_[static_cast<int>(cur_row_)][cur_col_ - 1] == PUYO_EMPTY) {
            int sub_c = cur_col_ - 1 + sub_offset_x_;
            int sub_r = static_cast<int>(cur_row_) + sub_offset_y_;
            if (sub_c >= 0 && (sub_r < 0 || grid_[sub_r][sub_c] == PUYO_EMPTY)) {
                cur_col_--;
            }
        }
    }
    if ((buttons & BUTTON_RIGHT) && !(prev_buttons & BUTTON_RIGHT)) {
        if (cur_col_ + 1 < COLS && grid_[static_cast<int>(cur_row_)][cur_col_ + 1] == PUYO_EMPTY) {
            int sub_c = cur_col_ + 1 + sub_offset_x_;
            int sub_r = static_cast<int>(cur_row_) + sub_offset_y_;
            if (sub_c < COLS && (sub_r < 0 || grid_[sub_r][sub_c] == PUYO_EMPTY)) {
                cur_col_++;
            }
        }
    }

    // Rotations
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        RotatePair(1);
    }
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        RotatePair(-1);
    }

    // Soft Drop
    float speed = (buttons & BUTTON_DOWN) ? 12.0f : 1.5f;
    cur_row_ += speed * dt;

    int r_main = static_cast<int>(cur_row_);
    int r_sub = r_main + sub_offset_y_;
    int c_sub = cur_col_ + sub_offset_x_;

    bool hit_ground = false;
    if (r_main >= ROWS - 1 || r_sub >= ROWS - 1) {
        hit_ground = true;
    } else {
        if (r_main + 1 < ROWS && grid_[r_main + 1][cur_col_] != PUYO_EMPTY) hit_ground = true;
        if (r_sub + 1 < ROWS && r_sub >= 0 && grid_[r_sub + 1][c_sub] != PUYO_EMPTY) hit_ground = true;
    }

    if (hit_ground) {
        DropPair();
    }
}

void Game083PuyoPuyo::DropPair() {
    int r_main = std::min(ROWS - 1, std::max(0, static_cast<int>(cur_row_)));
    int r_sub = std::min(ROWS - 1, std::max(0, r_main + sub_offset_y_));
    int c_sub = cur_col_ + sub_offset_x_;

    grid_[r_main][cur_col_] = puyo_main_;
    grid_[r_sub][c_sub] = puyo_sub_;

    ApplyGravity();

    state_ = STATE_CHAIN_RESOLVE;
    state_timer_ = 0.0f;
    current_chain_ = 0;
}

bool Game083PuyoPuyo::ApplyGravity() {
    bool moved = false;
    for (int c = 0; c < COLS; ++c) {
        for (int r = ROWS - 2; r >= 0; --r) {
            if (grid_[r][c] != PUYO_EMPTY && grid_[r + 1][c] == PUYO_EMPTY) {
                // Drop down
                int fall_to = r;
                while (fall_to + 1 < ROWS && grid_[fall_to + 1][c] == PUYO_EMPTY) {
                    fall_to++;
                }
                grid_[fall_to][c] = grid_[r][c];
                grid_[r][c] = PUYO_EMPTY;
                moved = true;
            }
        }
    }
    return moved;
}

bool Game083PuyoPuyo::CheckMatches() {
    bool visited[ROWS][COLS] = {false};
    bool to_clear[ROWS][COLS] = {false};
    bool any_cleared = false;

    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};

    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            PuyoColor col = grid_[r][c];
            if (col == PUYO_EMPTY || col == PUYO_GARBAGE || visited[r][c]) continue;

            // BFS flood fill
            std::vector<std::pair<int, int>> group;
            std::queue<std::pair<int, int>> q;
            q.push({r, c});
            visited[r][c] = true;

            while (!q.empty()) {
                auto [cr, cc] = q.front();
                q.pop();
                group.push_back({cr, cc});

                for (int d = 0; d < 4; ++d) {
                    int nr = cr + dr[d];
                    int nc = cc + dc[d];
                    if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) {
                        if (!visited[nr][nc] && grid_[nr][nc] == col) {
                            visited[nr][nc] = true;
                            q.push({nr, nc});
                        }
                    }
                }
            }

            // 4+ Connected Puyo group matches!
            if (group.size() >= 4) {
                any_cleared = true;
                for (auto& pt : group) {
                    to_clear[pt.first][pt.second] = true;
                    // Also clear neighboring garbage
                    for (int d = 0; d < 4; ++d) {
                        int gr = pt.first + dr[d];
                        int gc = pt.second + dc[d];
                        if (gr >= 0 && gr < ROWS && gc >= 0 && gc < COLS) {
                            if (grid_[gr][gc] == PUYO_GARBAGE) {
                                to_clear[gr][gc] = true;
                            }
                        }
                    }
                }
            }
        }
    }

    if (any_cleared) {
        for (int r = 0; r < ROWS; ++r) {
            for (int c = 0; c < COLS; ++c) {
                if (to_clear[r][c]) {
                    grid_[r][c] = PUYO_EMPTY;
                }
            }
        }
    }

    return any_cleared;
}

void Game083PuyoPuyo::Render(uint8_t* fb) {
    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Dark Magic Forest Backdrop
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 15, 20, 35);
        }
    }

    // 2. Playfield Well Borders (Columns x = 4..9, Left wall x=3, Right wall x=10, Floor y=15)
    for (int y = 2; y < 16; ++y) {
        set_pixel(3, y, 100, 100, 150);
        set_pixel(10, y, 100, 100, 150);
    }
    for (int x = 3; x <= 10; ++x) {
        set_pixel(x, 15, 100, 100, 150);
    }

    auto get_puyo_color = [](PuyoColor c, uint8_t& r, uint8_t& g, uint8_t& b) {
        switch (c) {
            case PUYO_RED:     r = 255; g = 40;  b = 40;  break;
            case PUYO_GREEN:   r = 30;  g = 220; b = 40;  break;
            case PUYO_BLUE:    r = 40;  g = 120; b = 255; break;
            case PUYO_YELLOW:  r = 255; g = 220; b = 20;  break;
            case PUYO_GARBAGE: r = 180; g = 180; b = 180; break;
            default:           r = 0;   g = 0;   b = 0;   break;
        }
    };

    // 3. Grid Puyos
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            if (grid_[r][c] != PUYO_EMPTY) {
                uint8_t pr, pg, pb;
                get_puyo_color(grid_[r][c], pr, pg, pb);
                set_pixel(4 + c, 2 + r, pr, pg, pb);
            }
        }
    }

    // 4. Current Falling Pair
    if (state_ == STATE_PLAYING) {
        int r_main = static_cast<int>(cur_row_);
        int r_sub = r_main + sub_offset_y_;
        int c_sub = cur_col_ + sub_offset_x_;

        uint8_t mr, mg, mb, sr, sg, sb;
        get_puyo_color(puyo_main_, mr, mg, mb);
        get_puyo_color(puyo_sub_, sr, sg, sb);

        if (r_main >= 0 && r_main < ROWS) set_pixel(4 + cur_col_, 2 + r_main, mr, mg, mb);
        if (r_sub >= 0 && r_sub < ROWS) set_pixel(4 + c_sub, 2 + r_sub, sr, sg, sb);
    }

    // 5. Chain Gauge / Combo Sparkle (Left border indicator)
    if (current_chain_ > 0) {
        for (int i = 0; i < std::min(10, current_chain_ * 2); ++i) {
            set_pixel(1, 14 - i, 255, 200, 0); // Golden chain bars
        }
    }

    // 6. Score Bar (y = 0)
    int score_dots = std::min(15, score_ / 500);
    for (int s = 0; s < score_dots; ++s) {
        set_pixel(s, 0, 50, 200, 255);
    }
}

} // namespace arcade
