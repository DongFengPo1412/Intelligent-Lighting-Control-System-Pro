// game_014_sokoban.cpp —— 经典推箱子 1982 核心实现
#include "game_014_sokoban.h"
#include <string.h>

namespace arcade {

Game014Sokoban::Game014Sokoban()
    : state_(STATE_TITLE),
      player_x_(7),
      player_y_(8),
      moves_(0),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      boxes_on_goal_(0) {
}

int Game014Sokoban::FindBoxAt(int x, int y) const {
    for (int i = 0; i < kNumBoxes; ++i) {
        if (boxes_[i].x == x && boxes_[i].y == y) {
            return i;
        }
    }
    return -1;
}

bool Game014Sokoban::IsGoal(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return false;
    return map_[y][x] == SOKOBAN_GOAL;
}

void Game014Sokoban::ResetLevel() {
    // 1. 初始化 16x16 仓库地图
    memset(map_, SOKOBAN_FLOOR, sizeof(map_));

    // 外围黑色虚空不可通行 (设为墙壁)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x < 2 || x > 13 || y < 2 || y > 13) {
                map_[y][x] = SOKOBAN_WALL;
            }
        }
    }

    // 仓库内部围墙轮廓 (y=2..13, x=2..13)
    for (int x = 2; x <= 13; ++x) {
        map_[2][x] = SOKOBAN_WALL;
        map_[13][x] = SOKOBAN_WALL;
    }
    for (int y = 2; y <= 13; ++y) {
        map_[y][2] = SOKOBAN_WALL;
        map_[y][13] = SOKOBAN_WALL;
    }

    // 内部结构柱 (增加仓库格局几何深度)
    map_[5][8] = SOKOBAN_WALL;
    map_[6][8] = SOKOBAN_WALL;
    map_[9][7] = SOKOBAN_WALL;
    map_[10][7] = SOKOBAN_WALL;

    // 4 个目标槽位 (点阵发光)
    map_[4][4] = SOKOBAN_GOAL;
    map_[4][5] = SOKOBAN_GOAL;
    map_[11][10] = SOKOBAN_GOAL;
    map_[11][11] = SOKOBAN_GOAL;

    // 4 个箱子初始摆放
    boxes_[0] = {5, 6};
    boxes_[1] = {6, 6};
    boxes_[2] = {9, 9};
    boxes_[3] = {10, 9};

    // 玩家初始站位
    player_x_ = 7;
    player_y_ = 8;
    moves_ = 0;

    CheckVictory();
}

void Game014Sokoban::Init() {
    Reset();
}

void Game014Sokoban::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    state_timer_ = 0.0f;
    ResetLevel();
}

void Game014Sokoban::CheckVictory() {
    int on_goal = 0;
    for (int i = 0; i < kNumBoxes; ++i) {
        if (IsGoal(boxes_[i].x, boxes_[i].y)) {
            on_goal++;
        }
    }
    boxes_on_goal_ = on_goal;

    if (boxes_on_goal_ == kNumBoxes) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ = 1000 - (moves_ * 5);
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game014Sokoban::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        // 按 A 或 B 键快速重置死锁局面
        if (keys_pressed & (KEY_A | KEY_B)) {
            ResetLevel();
            return;
        }

        int dx = 0, dy = 0;
        if (keys_pressed & KEY_UP) dy = -1;
        else if (keys_pressed & KEY_DOWN) dy = 1;
        else if (keys_pressed & KEY_LEFT) dx = -1;
        else if (keys_pressed & KEY_RIGHT) dx = 1;

        if (dx != 0 || dy != 0) {
            int nx = player_x_ + dx;
            int ny = player_y_ + dy;

            // 检查前方是否有箱子
            int box_idx = FindBoxAt(nx, ny);
            if (box_idx != -1) {
                // 箱子前方目标点
                int bx2 = nx + dx;
                int by2 = ny + dy;

                // 目标点不可为墙壁，且不可有另一只箱子 (禁止推两只箱子)
                if (map_[by2][bx2] != SOKOBAN_WALL && FindBoxAt(bx2, by2) == -1) {
                    boxes_[box_idx].x = bx2;
                    boxes_[box_idx].y = by2;
                    player_x_ = nx;
                    player_y_ = ny;
                    moves_++;
                    CheckVictory();
                }
            } else if (map_[ny][nx] != SOKOBAN_WALL) {
                // 自由行走入空地或目标点
                player_x_ = nx;
                player_y_ = ny;
                moves_++;
            }
        }
    }
}

void Game014Sokoban::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 绘制地面与仓库墙壁
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (map_[y][x] == SOKOBAN_WALL) {
                // 坚固砖墙 (暗蓝灰)
                fb_rgb24[idx + 0] = 52; fb_rgb24[idx + 1] = 73; fb_rgb24[idx + 2] = 94;
            } else if (map_[y][x] == SOKOBAN_GOAL) {
                // 目标槽位 (明亮金色星点)
                fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;
            } else if (x >= 2 && x <= 13 && y >= 2 && y <= 13) {
                // 仓库木地板 (深褐微亮)
                fb_rgb24[idx + 0] = 30; fb_rgb24[idx + 1] = 30; fb_rgb24[idx + 2] = 30;
            }
        }
    }

    // 2. 绘制 4 个箱子 (未归位: 橙色木箱; 归位: 耀眼翠绿翡翠箱)
    for (int i = 0; i < kNumBoxes; ++i) {
        int bx = boxes_[i].x;
        int by = boxes_[i].y;
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            if (IsGoal(bx, by)) {
                fb_rgb24[idx + 0] = 46;  fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113; // 归位绿
            } else {
                fb_rgb24[idx + 0] = 230; fb_rgb24[idx + 1] = 126; fb_rgb24[idx + 2] = 34;  // 木箱橙
            }
        }
    }

    // 3. 绘制搬运工玩家 (炫彩青蓝)
    int px = player_x_;
    int py = player_y_;
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb_rgb24[idx + 0] = 0;
        fb_rgb24[idx + 1] = 255;
        fb_rgb24[idx + 2] = 255;
    }

    // 4. 顶部状态栏: 归位进度 (y=0 绿色点阵)
    for (int i = 0; i < boxes_on_goal_; ++i) {
        int idx = (0 * 16 + (i * 2 + 1)) * 3;
        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
    }

    // 5. 胜负特效
    if (state_ == STATE_VICTORY) {
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
        }
    }
}

CartridgeStatus Game014Sokoban::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((boxes_on_goal_ * 100) / kNumBoxes);
    return st;
}

} // namespace arcade
