// game_018_minesweeper.cpp —— 像素扫雷 1990 核心实现
#include "game_018_minesweeper.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

namespace arcade {

Game018Minesweeper::Game018Minesweeper()
    : state_(STATE_TITLE),
      cursor_x_(7),
      cursor_y_(7),
      first_click_(true),
      remaining_hidden_safe_(256 - kTotalMines),
      flags_placed_(0),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      cursor_blink_timer_(0.0f) {
}

void Game018Minesweeper::GenerateMines(int safe_x, int safe_y) {
    // 随机播撒 25 颗地雷，避开 safe_x, safe_y 及其 8 邻域
    int mines_to_place = kTotalMines;
    while (mines_to_place > 0) {
        int rx = rand() % 16;
        int ry = rand() % 16;

        if (abs(rx - safe_x) <= 1 && abs(ry - safe_y) <= 1) {
            continue; // 保护首按区
        }

        if (!grid_[ry][rx].has_mine) {
            grid_[ry][rx].has_mine = true;
            mines_to_place--;
        }
    }

    // 预计算所有格子的八邻域地雷数
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (grid_[y][x].has_mine) continue;
            uint8_t count = 0;
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    int nx = x + dx;
                    int ny = y + dy;
                    if (nx >= 0 && nx < 16 && ny >= 0 && ny < 16) {
                        if (grid_[ny][nx].has_mine) count++;
                    }
                }
            }
            grid_[y][x].neighbor_mines = count;
        }
    }
}

void Game018Minesweeper::Init() {
    Reset();
}

void Game018Minesweeper::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    state_timer_ = 0.0f;
    cursor_x_ = 7;
    cursor_y_ = 7;
    first_click_ = true;
    flags_placed_ = 0;
    remaining_hidden_safe_ = 256 - kTotalMines;
    cursor_blink_timer_ = 0.0f;

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            grid_[y][x].has_mine = false;
            grid_[y][x].revealed = false;
            grid_[y][x].flagged = false;
            grid_[y][x].neighbor_mines = 0;
        }
    }
}

void Game018Minesweeper::Reveal(int x, int y) {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return;
    if (grid_[y][x].revealed || grid_[y][x].flagged) return;

    if (grid_[y][x].has_mine) {
        // 踩雷触发大爆炸
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
        // 翻开全图地雷
        for (int ry = 0; ry < 16; ++ry) {
            for (int rx = 0; rx < 16; ++rx) {
                if (grid_[ry][rx].has_mine) grid_[ry][rx].revealed = true;
            }
        }
        return;
    }

    grid_[y][x].revealed = true;
    remaining_hidden_safe_--;
    score_ += 10;
    if (score_ > high_score_) high_score_ = score_;

    // 零雷区洪水填充蔓延
    if (grid_[y][x].neighbor_mines == 0) {
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dx = -1; dx <= 1; ++dx) {
                if (dx != 0 || dy != 0) {
                    Reveal(x + dx, y + dy);
                }
            }
        }
    }

    CheckVictory();
}

void Game018Minesweeper::ToggleFlag(int x, int y) {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return;
    if (grid_[y][x].revealed) return;

    grid_[y][x].flagged = !grid_[y][x].flagged;
    if (grid_[y][x].flagged) flags_placed_++;
    else flags_placed_--;
}

void Game018Minesweeper::CheckVictory() {
    if (remaining_hidden_safe_ <= 0) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 500;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game018Minesweeper::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    cursor_blink_timer_ += dt;
    if (cursor_blink_timer_ >= 0.6f) cursor_blink_timer_ -= 0.6f;

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

        // 1. 光标四向移动
        if (keys_pressed & KEY_UP) {
            if (cursor_y_ > 0) cursor_y_--;
        } else if (keys_pressed & KEY_DOWN) {
            if (cursor_y_ < 15) cursor_y_++;
        } else if (keys_pressed & KEY_LEFT) {
            if (cursor_x_ > 0) cursor_x_--;
        } else if (keys_pressed & KEY_RIGHT) {
            if (cursor_x_ < 15) cursor_x_++;
        }

        // 2. 翻开操作 (KEY_A)
        if (keys_pressed & KEY_A) {
            if (first_click_) {
                GenerateMines(cursor_x_, cursor_y_);
                first_click_ = false;
            }
            Reveal(cursor_x_, cursor_y_);
        }

        // 3. 插旗操作 (KEY_B)
        if (keys_pressed & KEY_B) {
            ToggleFlag(cursor_x_, cursor_y_);
        }
    }
}

void Game018Minesweeper::Render(uint8_t* fb_rgb24) {
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            const MineCell& cell = grid_[y][x];

            if (!cell.revealed) {
                if (cell.flagged) {
                    // 插旗黄标
                    fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;
                } else {
                    // 未翻开凹凸蓝灰方块
                    fb_rgb24[idx + 0] = 70;  fb_rgb24[idx + 1] = 80;  fb_rgb24[idx + 2] = 95;
                }
            } else {
                if (cell.has_mine) {
                    // 地雷引爆大红火球
                    fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76;  fb_rgb24[idx + 2] = 60;
                } else {
                    // 翻开数字区域色彩映射
                    switch (cell.neighbor_mines) {
                        case 0:  fb_rgb24[idx + 0] = 35;  fb_rgb24[idx + 1] = 35;  fb_rgb24[idx + 2] = 40;  break;
                        case 1:  fb_rgb24[idx + 0] = 52;  fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219; break; // 蓝
                        case 2:  fb_rgb24[idx + 0] = 46;  fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113; break; // 绿
                        case 3:  fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76;  fb_rgb24[idx + 2] = 60;  break; // 红
                        case 4:  fb_rgb24[idx + 0] = 155; fb_rgb24[idx + 1] = 89;  fb_rgb24[idx + 2] = 182; break; // 紫
                        default: fb_rgb24[idx + 0] = 243; fb_rgb24[idx + 1] = 156; fb_rgb24[idx + 2] = 18;  break; // 橙红
                    }
                }
            }
        }
    }

    // 绘制闪烁光标 (耀眼纯白十字准星/方格)
    if (cursor_blink_timer_ < 0.35f && state_ == STATE_PLAYING) {
        int idx = (cursor_y_ * 16 + cursor_x_) * 3;
        fb_rgb24[idx + 0] = 255;
        fb_rgb24[idx + 1] = 255;
        fb_rgb24[idx + 2] = 255;
    }

    // 特效渲染
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

CartridgeStatus Game018Minesweeper::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    int total_safe = 256 - kTotalMines;
    st.progress = (uint8_t)(((total_safe - remaining_hidden_safe_) * 100) / total_safe);
    return st;
}

} // namespace arcade
