// game_015_tron.cpp —— 创战纪光轮摩托 1982 核心实现
#include "game_015_tron.h"
#include <string.h>

namespace arcade {

Game015Tron::Game015Tron()
    : state_(STATE_TITLE),
      p1_wins_(0),
      p2_wins_(0),
      step_timer_(0.0f),
      step_interval_(0.12f),
      state_timer_(0.0f),
      score_(0),
      high_score_(0) {
}

void Game015Tron::ResetRound() {
    memset(grid_, TRON_NONE, sizeof(grid_));

    // 外围竞技场实体电栅边界 (x=0,15, y=0,15)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                grid_[y][x] = TRON_WALL;
            }
        }
    }

    // P1 初始位置与方向
    p1_.x = 3;
    p1_.y = 8;
    p1_.dir_x = 1;
    p1_.dir_y = 0;
    p1_.alive = true;
    p1_.r = 0; p1_.g = 255; p1_.b = 255; // 赛博青蓝
    grid_[p1_.y][p1_.x] = TRON_P1;

    // P2 (AI) 初始位置与方向
    p2_.x = 12;
    p2_.y = 8;
    p2_.dir_x = -1;
    p2_.dir_y = 0;
    p2_.alive = true;
    p2_.r = 230; p2_.g = 126; p2_.b = 34; // 经典光轮橙
    grid_[p2_.y][p2_.x] = TRON_P2_AI;

    step_timer_ = 0.0f;
}

void Game015Tron::Init() {
    Reset();
}

void Game015Tron::Reset() {
    state_ = STATE_PLAYING;
    p1_wins_ = 0;
    p2_wins_ = 0;
    score_ = 0;
    state_timer_ = 0.0f;
    step_interval_ = 0.12f;
    ResetRound();
}

void Game015Tron::StepAI() {
    // 评估前方是否受阻
    int fwd_x = p2_.x + p2_.dir_x;
    int fwd_y = p2_.y + p2_.dir_y;

    bool forward_blocked = (grid_[fwd_y][fwd_x] != TRON_NONE);

    // 候选转向方向 (向左转或向右转 90 度，绝不掉头)
    int cand_dx[2] = {-p2_.dir_y, p2_.dir_y};
    int cand_dy[2] = {p2_.dir_x, -p2_.dir_x};

    if (forward_blocked) {
        int best_dir = -1;
        int max_space = -1;

        for (int i = 0; i < 2; ++i) {
            int test_x = p2_.x + cand_dx[i];
            int test_y = p2_.y + cand_dy[i];

            if (grid_[test_y][test_x] == TRON_NONE) {
                // 深度探针：统计该方向能走多少格
                int space = 0;
                int px = test_x;
                int py = test_y;
                while (grid_[py][px] == TRON_NONE && space < 8) {
                    space++;
                    px += cand_dx[i];
                    py += cand_dy[i];
                }
                if (space > max_space) {
                    max_space = space;
                    best_dir = i;
                }
            }
        }

        if (best_dir != -1) {
            p2_.dir_x = cand_dx[best_dir];
            p2_.dir_y = cand_dy[best_dir];
        }
    } else {
        // 前方畅通时，微小概率自主变向包抄玩家
        int cand_dir = (p1_.y > p2_.y) ? 1 : (p1_.y < p2_.y) ? 0 : 0;
        int test_x = p2_.x + cand_dx[cand_dir];
        int test_y = p2_.y + cand_dy[cand_dir];
        if (grid_[test_y][test_x] == TRON_NONE && (p2_.x % 4 == 0)) {
            p2_.dir_x = cand_dx[cand_dir];
            p2_.dir_y = cand_dy[cand_dir];
        }
    }
}

void Game015Tron::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        // 玩家 90 度转向输入 (禁止 180 度原地自杀调头)
        if ((keys_pressed & KEY_UP) && p1_.dir_y != 1) {
            p1_.dir_x = 0; p1_.dir_y = -1;
        } else if ((keys_pressed & KEY_DOWN) && p1_.dir_y != -1) {
            p1_.dir_x = 0; p1_.dir_y = 1;
        } else if ((keys_pressed & KEY_LEFT) && p1_.dir_x != 1) {
            p1_.dir_x = -1; p1_.dir_y = 0;
        } else if ((keys_pressed & KEY_RIGHT) && p1_.dir_x != -1) {
            p1_.dir_x = 1; p1_.dir_y = 0;
        }

        step_timer_ += dt;
        if (step_timer_ >= step_interval_) {
            step_timer_ = 0.0f;

            // AI 寻路决策
            StepAI();

            int p1_nx = p1_.x + p1_.dir_x;
            int p1_ny = p1_.y + p1_.dir_y;

            int p2_nx = p2_.x + p2_.dir_x;
            int p2_ny = p2_.y + p2_.dir_y;

            bool p1_crashed = (grid_[p1_ny][p1_nx] != TRON_NONE);
            bool p2_crashed = (grid_[p2_ny][p2_nx] != TRON_NONE);

            // 正面相对撞车
            if (p1_nx == p2_nx && p1_ny == p2_ny) {
                p1_crashed = true;
                p2_crashed = true;
            }

            if (p1_crashed || p2_crashed) {
                if (p1_crashed && p2_crashed) {
                    // 平局重来
                    ResetRound();
                } else if (p1_crashed) {
                    p2_wins_++;
                    if (p2_wins_ >= kTargetWins) {
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                    } else {
                        ResetRound();
                    }
                } else {
                    p1_wins_++;
                    score_ += 100;
                    if (score_ > high_score_) high_score_ = score_;

                    if (p1_wins_ >= kTargetWins) {
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                    } else {
                        ResetRound();
                    }
                }
                return;
            }

            // 移动并留下永久固体光痕
            p1_.x = p1_nx;
            p1_.y = p1_ny;
            grid_[p1_.y][p1_.x] = TRON_P1;

            p2_.x = p2_nx;
            p2_.y = p2_ny;
            grid_[p2_.y][p2_.x] = TRON_P2_AI;
        }
    }
}

void Game015Tron::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 绘制竞技场电栅与双方永久光痕
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            uint8_t cell = grid_[y][x];

            if (cell == TRON_WALL) {
                // 竞技场紫色电栅
                fb_rgb24[idx + 0] = 142; fb_rgb24[idx + 1] = 68;  fb_rgb24[idx + 2] = 173;
            } else if (cell == TRON_P1) {
                // P1 青蓝光痕墙
                fb_rgb24[idx + 0] = 0;   fb_rgb24[idx + 1] = 200; fb_rgb24[idx + 2] = 255;
            } else if (cell == TRON_P2_AI) {
                // P2 橙红光痕墙
                fb_rgb24[idx + 0] = 230; fb_rgb24[idx + 1] = 126; fb_rgb24[idx + 2] = 34;
            }
        }
    }

    // 2. 绘制双方摩托车车头 (耀眼高光)
    int idx_p1 = (p1_.y * 16 + p1_.x) * 3;
    fb_rgb24[idx_p1 + 0] = 255; fb_rgb24[idx_p1 + 1] = 255; fb_rgb24[idx_p1 + 2] = 255;

    int idx_p2 = (p2_.y * 16 + p2_.x) * 3;
    fb_rgb24[idx_p2 + 0] = 255; fb_rgb24[idx_p2 + 1] = 242; fb_rgb24[idx_p2 + 2] = 0;

    // 3. 顶部 HUD: 双方胜场指示 (左侧P1青点，右侧AI橙点)
    for (int i = 0; i < p1_wins_; ++i) {
        int idx = (0 * 16 + (i + 1)) * 3;
        fb_rgb24[idx + 0] = 0; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }
    for (int i = 0; i < p2_wins_; ++i) {
        int idx = (0 * 16 + (14 - i)) * 3;
        fb_rgb24[idx + 0] = 230; fb_rgb24[idx + 1] = 126; fb_rgb24[idx + 2] = 34;
    }

    // 4. 特效渲染
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

CartridgeStatus Game015Tron::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = (p1_wins_ >= p2_wins_) ? 1 : 0;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((p1_wins_ * 100) / kTargetWins);
    return st;
}

} // namespace arcade
