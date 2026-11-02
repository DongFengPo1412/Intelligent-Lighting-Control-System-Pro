// game_010_pacman.cpp —— 像素吃豆人 1980 核心实现
#include "game_010_pacman.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

static const uint8_t kWallMap[16][16] = {
    {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1},
    {1,0,0,0,0,0,1,1,1,1,0,0,0,0,0,1},
    {1,0,1,1,0,1,0,0,0,0,1,0,1,1,0,1},
    {1,0,1,1,0,1,0,1,1,0,1,0,1,1,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1},
    {1,0,1,1,0,1,1,0,0,1,1,0,1,1,0,1},
    {1,0,0,1,0,1,0,0,0,0,1,0,1,0,0,1},
    {0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,0}, // 左右穿梭隧道 (Row 7)
    {1,0,0,1,0,1,0,0,0,0,1,0,1,0,0,1},
    {1,0,1,1,0,1,1,1,1,1,1,0,1,1,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1},
    {1,0,1,1,0,1,1,0,0,1,1,0,1,1,0,1},
    {1,0,0,1,0,0,0,1,1,0,0,0,1,0,0,1},
    {1,1,0,1,0,1,0,0,0,0,1,0,1,0,1,1},
    {1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1},
    {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}
};

Game010Pacman::Game010Pacman()
    : state_(STATE_TITLE),
      pac_x_(8.0f),
      pac_y_(10.0f),
      pac_dir_x_(0),
      pac_dir_y_(0),
      desired_dir_x_(0),
      desired_dir_y_(0),
      frightened_timer_(0.0f),
      remaining_dots_(0),
      lives_(3),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

bool Game010Pacman::IsWall(int x, int y) const {
    if (y == 7 && (x < 0 || x >= 16)) return false; // 隧道通畅
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return true;
    return kWallMap[y][x] == 1;
}

void Game010Pacman::ResetPositions() {
    pac_x_ = 8.0f;
    pac_y_ = 10.0f;
    pac_dir_x_ = 0;
    pac_dir_y_ = 0;
    desired_dir_x_ = 0;
    desired_dir_y_ = 0;

    // 幽灵 1 (Blinky, 红)
    ghosts_[0].x = 7.0f;
    ghosts_[0].y = 6.0f;
    ghosts_[0].dir_x = 1;
    ghosts_[0].dir_y = 0;
    ghosts_[0].state = GHOST_CHASE;
    ghosts_[0].r = 231; ghosts_[0].g = 76; ghosts_[0].b = 60;
    ghosts_[0].speed = 4.0f;

    // 幽灵 2 (Pinky, 粉)
    ghosts_[1].x = 8.0f;
    ghosts_[1].y = 7.0f;
    ghosts_[1].dir_x = -1;
    ghosts_[1].dir_y = 0;
    ghosts_[1].state = GHOST_CHASE;
    ghosts_[1].r = 255; ghosts_[1].g = 105; ghosts_[1].b = 180;
    ghosts_[1].speed = 3.8f;

    // 幽灵 3 (Inky, 青)
    ghosts_[2].x = 7.0f;
    ghosts_[2].y = 8.0f;
    ghosts_[2].dir_x = 0;
    ghosts_[2].dir_y = 1;
    ghosts_[2].state = GHOST_CHASE;
    ghosts_[2].r = 0; ghosts_[2].g = 255; ghosts_[2].b = 255;
    ghosts_[2].speed = 3.6f;

    frightened_timer_ = 0.0f;
}

void Game010Pacman::Init() {
    Reset();
}

void Game010Pacman::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    remaining_dots_ = 0;

    // 初始化迷宫豆子
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (kWallMap[y][x] == 0) {
                // 幽灵房中心与吃豆人初始位不刷豆
                if ((x >= 6 && x <= 9 && y >= 6 && y <= 8) || (x == 8 && y == 10)) {
                    grid_[y][x] = 0;
                } else if ((x == 1 && y == 1) || (x == 14 && y == 1) ||
                           (x == 1 && y == 14) || (x == 14 && y == 14)) {
                    grid_[y][x] = 2; // 四角大力丸
                    remaining_dots_++;
                } else {
                    grid_[y][x] = 1; // 普通豆
                    remaining_dots_++;
                }
            } else {
                grid_[y][x] = 0;
            }
        }
    }

    ResetPositions();
}

void Game010Pacman::MoveGhost(Ghost& g, float dt) {
    float move_step = g.speed * dt;
    if (g.state == GHOST_FRIGHTENED) {
        move_step *= 0.55f; // 惊恐逃跑减速
    }

    // 居中网格对齐检测 (当接近格子整数中心时做拐弯决策)
    int cur_gx = (int)roundf(g.x);
    int cur_gy = (int)roundf(g.y);
    float dist_to_center = fabsf(g.x - (float)cur_gx) + fabsf(g.y - (float)cur_gy);

    if (dist_to_center < 0.12f) {
        // 对齐中心
        g.x = (float)cur_gx;
        g.y = (float)cur_gy;

        // 寻找可行方向 (上下左右，且不立即掉头)
        const int dxs[4] = {0, 0, -1, 1};
        const int dys[4] = {-1, 1, 0, 0};
        int best_dir = -1;
        float best_metric = (g.state == GHOST_FRIGHTENED) ? -1e9f : 1e9f;

        for (int i = 0; i < 4; ++i) {
            // 禁止 180 度直接掉头
            if (dxs[i] == -g.dir_x && dys[i] == -g.dir_y && (g.dir_x != 0 || g.dir_y != 0)) {
                continue;
            }

            int nx = cur_gx + dxs[i];
            int ny = cur_gy + dys[i];

            if (!IsWall(nx, ny)) {
                // 计算目标距离启发式
                float target_x = pac_x_;
                float target_y = pac_y_;
                float dist = (nx - target_x) * (nx - target_x) + (ny - target_y) * (ny - target_y);

                if (g.state == GHOST_FRIGHTENED) {
                    // 逃跑：选距离吃豆人最远的方向
                    if (dist > best_metric) {
                        best_metric = dist;
                        best_dir = i;
                    }
                } else {
                    // 追逐：选距离吃豆人最近的方向
                    if (dist < best_metric) {
                        best_metric = dist;
                        best_dir = i;
                    }
                }
            }
        }

        if (best_dir != -1) {
            g.dir_x = dxs[best_dir];
            g.dir_y = dys[best_dir];
        } else {
            // 死胡同允许掉头
            g.dir_x = -g.dir_x;
            g.dir_y = -g.dir_y;
        }
    }

    g.x += g.dir_x * move_step;
    g.y += g.dir_y * move_step;

    // 穿梭隧道循环
    if (g.x < 0.0f) g.x = 15.0f;
    else if (g.x > 15.0f) g.x = 0.0f;
}

void Game010Pacman::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        // 1. 输入缓冲解析
        if (keys_down & KEY_UP) {
            desired_dir_x_ = 0; desired_dir_y_ = -1;
        } else if (keys_down & KEY_DOWN) {
            desired_dir_x_ = 0; desired_dir_y_ = 1;
        } else if (keys_down & KEY_LEFT) {
            desired_dir_x_ = -1; desired_dir_y_ = 0;
        } else if (keys_down & KEY_RIGHT) {
            desired_dir_x_ = 1; desired_dir_y_ = 0;
        }

        // 2. 吃豆人拐弯与移动
        int cur_px = (int)roundf(pac_x_);
        int cur_py = (int)roundf(pac_y_);
        float p_dist = fabsf(pac_x_ - (float)cur_px) + fabsf(pac_y_ - (float)cur_py);

        // 如果想反向掉头，随时可转
        if (desired_dir_x_ == -pac_dir_x_ && desired_dir_y_ == -pac_dir_y_ &&
            (desired_dir_x_ != 0 || desired_dir_y_ != 0)) {
            pac_dir_x_ = desired_dir_x_;
            pac_dir_y_ = desired_dir_y_;
        } else if (p_dist < 0.2f && (desired_dir_x_ != pac_dir_x_ || desired_dir_y_ != pac_dir_y_)) {
            // 尝试转向
            int next_x = cur_px + desired_dir_x_;
            int next_y = cur_py + desired_dir_y_;
            if (!IsWall(next_x, next_y)) {
                pac_x_ = (float)cur_px;
                pac_y_ = (float)cur_py;
                pac_dir_x_ = desired_dir_x_;
                pac_dir_y_ = desired_dir_y_;
            }
        }

        // 前方撞墙检测
        int fwd_x = cur_px + pac_dir_x_;
        int fwd_y = cur_py + pac_dir_y_;
        if (IsWall(fwd_x, fwd_y) && p_dist < 0.1f) {
            pac_x_ = (float)cur_px;
            pac_y_ = (float)cur_py;
            pac_dir_x_ = 0;
            pac_dir_y_ = 0;
        }

        const float pac_speed = 4.8f;
        pac_x_ += pac_dir_x_ * pac_speed * dt;
        pac_y_ += pac_dir_y_ * pac_speed * dt;

        // 穿梭隧道循环
        if (pac_x_ < 0.0f) pac_x_ = 15.0f;
        else if (pac_x_ > 15.0f) pac_x_ = 0.0f;

        // 3. 吞吃豆子判定
        int eat_x = (int)roundf(pac_x_);
        int eat_y = (int)roundf(pac_y_);
        if (eat_x >= 0 && eat_x < 16 && eat_y >= 0 && eat_y < 16) {
            if (grid_[eat_y][eat_x] == 1) { // 普通豆
                grid_[eat_y][eat_x] = 0;
                remaining_dots_--;
                score_ += 10;
                if (score_ > high_score_) high_score_ = score_;
            } else if (grid_[eat_y][eat_x] == 2) { // 大力丸
                grid_[eat_y][eat_x] = 0;
                remaining_dots_--;
                score_ += 50;
                if (score_ > high_score_) high_score_ = score_;
                frightened_timer_ = 6.0f; // 触发惊恐态
                for (int i = 0; i < kNumGhosts; ++i) {
                    ghosts_[i].state = GHOST_FRIGHTENED;
                }
            }
        }

        // 通关判定
        if (remaining_dots_ <= 0) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            return;
        }

        // 4. 惊恐计时器倒数
        if (frightened_timer_ > 0.0f) {
            frightened_timer_ -= dt;
            if (frightened_timer_ <= 0.0f) {
                frightened_timer_ = 0.0f;
                for (int i = 0; i < kNumGhosts; ++i) {
                    ghosts_[i].state = GHOST_CHASE;
                }
            }
        }

        // 5. 幽灵移动与碰撞交互
        for (int i = 0; i < kNumGhosts; ++i) {
            MoveGhost(ghosts_[i], dt);

            // 碰撞判定
            float dist = fabsf(pac_x_ - ghosts_[i].x) + fabsf(pac_y_ - ghosts_[i].y);
            if (dist < 0.75f) {
                if (ghosts_[i].state == GHOST_FRIGHTENED) {
                    // 吃掉幽灵!
                    score_ += 200;
                    if (score_ > high_score_) high_score_ = score_;
                    ghosts_[i].x = 7.5f;
                    ghosts_[i].y = 7.0f;
                    ghosts_[i].state = GHOST_CHASE;
                } else {
                    // 吃豆人丧生!
                    if (lives_ > 0) lives_--;
                    if (lives_ == 0) {
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        return;
                    } else {
                        ResetPositions();
                        return;
                    }
                }
            }
        }
    }
}

void Game010Pacman::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 绘制迷宫墙壁 (经典霓虹深蓝)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (kWallMap[y][x] == 1) {
                fb_rgb24[idx + 0] = 25;
                fb_rgb24[idx + 1] = 42;
                fb_rgb24[idx + 2] = 86; // 经典雅达利/南梦宫迷宫深蓝
            } else {
                // 绘制普通豆与能量大力丸
                if (grid_[y][x] == 1) {
                    // 普通小豆: 暖黄微弱
                    fb_rgb24[idx + 0] = 243;
                    fb_rgb24[idx + 1] = 156;
                    fb_rgb24[idx + 2] = 18;
                } else if (grid_[y][x] == 2) {
                    // 大力丸能量豆: 耀眼大白/微黄闪烁
                    fb_rgb24[idx + 0] = 255;
                    fb_rgb24[idx + 1] = 255;
                    fb_rgb24[idx + 2] = 220;
                }
            }
        }
    }

    // 2. 绘制幽灵
    for (int i = 0; i < kNumGhosts; ++i) {
        int gx = (int)roundf(ghosts_[i].x);
        int gy = (int)roundf(ghosts_[i].y);
        if (gx >= 0 && gx < 16 && gy >= 0 && gy < 16) {
            int idx = (gy * 16 + gx) * 3;
            if (ghosts_[i].state == GHOST_FRIGHTENED) {
                // 惊恐态: 幽灵海蓝 (快结束时白蓝交替)
                if (frightened_timer_ < 1.5f && ((int)(frightened_timer_ * 6.0f) % 2 == 0)) {
                    fb_rgb24[idx + 0] = 236; fb_rgb24[idx + 1] = 240; fb_rgb24[idx + 2] = 241;
                } else {
                    fb_rgb24[idx + 0] = 41;  fb_rgb24[idx + 1] = 128; fb_rgb24[idx + 2] = 185;
                }
            } else {
                fb_rgb24[idx + 0] = ghosts_[i].r;
                fb_rgb24[idx + 1] = ghosts_[i].g;
                fb_rgb24[idx + 2] = ghosts_[i].b;
            }
        }
    }

    // 3. 绘制吃豆人 (经典高亮柠檬黄)
    int px = (int)roundf(pac_x_);
    int py = (int)roundf(pac_y_);
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb_rgb24[idx + 0] = 255;
        fb_rgb24[idx + 1] = 242;
        fb_rgb24[idx + 2] = 0;
    }

    // 4. 生命指示 (y=0 顶角黄点)
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + (i * 2 + 1)) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 242; fb_rgb24[idx + 2] = 0;
    }

    // 5. 胜负特效
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

CartridgeStatus Game010Pacman::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (remaining_dots_ == 0) ? 100 : (uint8_t)(100 - remaining_dots_);
    return st;
}

} // namespace arcade
