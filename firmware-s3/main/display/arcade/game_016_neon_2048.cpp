// game_016_neon_2048.cpp —— 霓虹 2048 核心实现
#include "game_016_neon_2048.h"
#include <string.h>
#include <stdlib.h>

namespace arcade {

Game016Neon2048::Game016Neon2048()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      max_tile_level_(1),
      state_timer_(0.0f) {
}

void Game016Neon2048::GetTileColor(uint8_t level, uint8_t& r, uint8_t& g, uint8_t& b) const {
    switch (level) {
        case 0:  r = 25;  g = 25;  b = 30;  break; // 空槽微弱黑蓝
        case 1:  r = 41;  g = 128; b = 185; break; // 2: 冰蓝
        case 2:  r = 26;  g = 188; b = 156; break; // 4: 碧绿
        case 3:  r = 46;  g = 204; b = 113; break; // 8: 鲜翠
        case 4:  r = 241; g = 196; b = 15;  break; // 16: 明黄
        case 5:  r = 230; g = 126; b = 34;  break; // 32: 烈橙
        case 6:  r = 231; g = 76;  b = 60;  break; // 64: 猩红
        case 7:  r = 155; g = 89;  b = 182; break; // 128: 紫罗兰
        case 8:  r = 255; g = 0;   b = 128; break; // 256: 霓虹粉
        case 9:  r = 255; g = 215; b = 0;   break; // 512: 纯金辉光
        case 10: r = 127; g = 255; b = 212; break; // 1024: 碧晶白
        default: r = 255; g = 255; b = 255; break; // 2048: 终极炫白
    }
}

void Game016Neon2048::SpawnRandomTile() {
    int empty_r[16], empty_c[16];
    int empty_cnt = 0;

    for (int r = 0; r < 4; ++r) {
        for (int c = 0; c < 4; ++c) {
            if (board_[r][c] == 0) {
                empty_r[empty_cnt] = r;
                empty_c[empty_cnt] = c;
                empty_cnt++;
            }
        }
    }

    if (empty_cnt == 0) return;

    int pick = rand() % empty_cnt;
    uint8_t new_level = (rand() % 10 == 0) ? 2 : 1; // 90% 出 2, 10% 出 4
    board_[empty_r[pick]][empty_c[pick]] = new_level;

    if (new_level > max_tile_level_) {
        max_tile_level_ = new_level;
    }
}

bool Game016Neon2048::CanMove() const {
    for (int r = 0; r < 4; ++r) {
        for (int c = 0; c < 4; ++c) {
            if (board_[r][c] == 0) return true;
            if (c < 3 && board_[r][c] == board_[r][c + 1]) return true;
            if (r < 3 && board_[r][c] == board_[r + 1][c]) return true;
        }
    }
    return false;
}

void Game016Neon2048::Init() {
    Reset();
}

void Game016Neon2048::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    state_timer_ = 0.0f;
    max_tile_level_ = 1;
    memset(board_, 0, sizeof(board_));

    SpawnRandomTile();
    SpawnRandomTile();
}

static bool MergeLineLeft(uint8_t line[4], uint32_t& score_gain, uint8_t& max_lvl) {
    uint8_t non_zeros[4];
    int nz_cnt = 0;
    for (int i = 0; i < 4; ++i) {
        if (line[i] != 0) non_zeros[nz_cnt++] = line[i];
    }

    uint8_t res[4] = {0, 0, 0, 0};
    int res_cnt = 0;
    bool skip = false;

    for (int i = 0; i < nz_cnt; ++i) {
        if (skip) {
            skip = false;
            continue;
        }
        if (i + 1 < nz_cnt && non_zeros[i] == non_zeros[i + 1]) {
            uint8_t merged_lvl = non_zeros[i] + 1;
            res[res_cnt++] = merged_lvl;
            score_gain += (1 << merged_lvl);
            if (merged_lvl > max_lvl) max_lvl = merged_lvl;
            skip = true;
        } else {
            res[res_cnt++] = non_zeros[i];
            if (non_zeros[i] > max_lvl) max_lvl = non_zeros[i];
        }
    }

    bool changed = false;
    for (int i = 0; i < 4; ++i) {
        if (line[i] != res[i]) changed = true;
        line[i] = res[i];
    }
    return changed;
}

bool Game016Neon2048::Slide(int dx, int dy) {
    bool moved = false;
    uint32_t total_gain = 0;
    uint8_t max_seen = max_tile_level_;

    if (dx != 0) {
        for (int r = 0; r < 4; ++r) {
            uint8_t line[4];
            if (dx < 0) {
                for (int c = 0; c < 4; ++c) line[c] = board_[r][c];
            } else {
                for (int c = 0; c < 4; ++c) line[c] = board_[r][3 - c];
            }

            if (MergeLineLeft(line, total_gain, max_seen)) {
                moved = true;
                if (dx < 0) {
                    for (int c = 0; c < 4; ++c) board_[r][c] = line[c];
                } else {
                    for (int c = 0; c < 4; ++c) board_[r][3 - c] = line[c];
                }
            }
        }
    } else if (dy != 0) {
        for (int c = 0; c < 4; ++c) {
            uint8_t line[4];
            if (dy < 0) {
                for (int r = 0; r < 4; ++r) line[r] = board_[r][c];
            } else {
                for (int r = 0; r < 4; ++r) line[r] = board_[3 - r][c];
            }

            if (MergeLineLeft(line, total_gain, max_seen)) {
                moved = true;
                if (dy < 0) {
                    for (int r = 0; r < 4; ++r) board_[r][c] = line[r];
                } else {
                    for (int r = 0; r < 4; ++r) board_[3 - r][c] = line[r];
                }
            }
        }
    }

    score_ += total_gain;
    if (max_seen > max_tile_level_) max_tile_level_ = max_seen;
    if (score_ > high_score_) high_score_ = score_;

    if (moved) {
        SpawnRandomTile();
        if (max_tile_level_ >= 11) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
        } else if (!CanMove()) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
        }
    }

    return moved;
}

void Game016Neon2048::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
        return;
    }

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        if (keys_pressed & KEY_UP) {
            Slide(0, -1);
        } else if (keys_pressed & KEY_DOWN) {
            Slide(0, 1);
        } else if (keys_pressed & KEY_LEFT) {
            Slide(-1, 0);
        } else if (keys_pressed & KEY_RIGHT) {
            Slide(1, 0);
        }
    }
}

void Game016Neon2048::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 渲染 4x4 大网格 (每个槽位占 3x3 像素，间隔 1 像素黑色缝隙)
    for (int r = 0; r < 4; ++r) {
        int y0 = r * 4;
        for (int c = 0; c < 4; ++c) {
            int x0 = c * 4;
            uint8_t cr, cg, cb;
            GetTileColor(board_[r][c], cr, cg, cb);

            for (int dy = 0; dy < 3; ++dy) {
                int y = y0 + dy;
                if (y < 16) {
                    for (int dx = 0; dx < 3; ++dx) {
                        int x = x0 + dx;
                        if (x < 16) {
                            int idx = (y * 16 + x) * 3;
                            fb_rgb24[idx + 0] = cr;
                            fb_rgb24[idx + 1] = cg;
                            fb_rgb24[idx + 2] = cb;
                        }
                    }
                }
            }
        }
    }

    if (state_ == STATE_VICTORY) {
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
        }
    } else if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
        }
    }
}

CartridgeStatus Game016Neon2048::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((max_tile_level_ * 100) / 11);
    return st;
}

} // namespace arcade
