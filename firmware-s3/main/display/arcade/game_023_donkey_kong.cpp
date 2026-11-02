// game_023_donkey_kong.cpp —— 经典大金刚 1981 核心实现
#include "game_023_donkey_kong.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

namespace arcade {

Game023DonkeyKong::Game023DonkeyKong()
    : state_(STATE_TITLE),
      player_x_(1.0f),
      player_y_(13.0f),
      player_vy_(0.0f),
      jump_base_y_(13.0f),
      is_climbing_(false),
      is_jumping_(false),
      lives_(3),
      hammer_timer_(0.0f),
      barrel_spawn_timer_(0.0f),
      hammer_x_(2),
      hammer_y_(9),
      hammer_available_(true),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

bool Game023DonkeyKong::IsOnLadder(int x, int y) const {
    if (x == 12 && y >= 10 && y <= 14) return true;
    if (x == 3 && y >= 6 && y <= 10) return true;
    if (x == 7 && y >= 2 && y <= 6) return true;
    return false;
}

void Game023DonkeyKong::InitLevel() {
    player_x_ = 1.0f;
    player_y_ = 13.0f;
    player_vy_ = 0.0f;
    is_climbing_ = false;
    is_jumping_ = false;
    hammer_timer_ = 0.0f;
    barrel_spawn_timer_ = 0.0f;
    hammer_x_ = 2;
    hammer_y_ = 9;
    hammer_available_ = true;

    for (int i = 0; i < MAX_BARRELS; ++i) {
        barrels_[i].active = false;
    }
}

void Game023DonkeyKong::Init() {
    Reset();
}

void Game023DonkeyKong::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    InitLevel();
}

void Game023DonkeyKong::SpawnBarrel() {
    for (int i = 0; i < MAX_BARRELS; ++i) {
        if (!barrels_[i].active) {
            barrels_[i].active = true;
            barrels_[i].x = 6.0f;
            barrels_[i].y = 2.0f;
            barrels_[i].vx = 3.5f; // 向右滚动
            barrels_[i].layer = 3;
            barrels_[i].falling_ladder = false;
            break;
        }
    }
}

void Game023DonkeyKong::UpdateBarrels(float dt) {
    barrel_spawn_timer_ += dt;
    if (barrel_spawn_timer_ >= 3.2f) {
        barrel_spawn_timer_ = 0.0f;
        SpawnBarrel();
    }

    for (int i = 0; i < MAX_BARRELS; ++i) {
        if (!barrels_[i].active) continue;

        if (barrels_[i].falling_ladder) {
            // 顺着梯子竖直跌落
            barrels_[i].y += 5.0f * dt;
            int target_y = (barrels_[i].layer == 2) ? 6 : (barrels_[i].layer == 1) ? 10 : 14;
            if (barrels_[i].y >= (float)target_y) {
                barrels_[i].y = (float)target_y;
                barrels_[i].falling_ladder = false;
                // 到达新层，反转速度
                barrels_[i].vx = (barrels_[i].layer % 2 == 1) ? 3.5f : -3.5f;
            }
        } else {
            // 沿钢梁横向滚动
            barrels_[i].x += barrels_[i].vx * dt;

            // 顶层 3 (y=2): 向右滚到 x=11 跌落到层 2 (y=6)
            if (barrels_[i].layer == 3) {
                if (barrels_[i].x >= 11.0f) {
                    barrels_[i].layer = 2;
                    barrels_[i].x = 11.0f;
                    barrels_[i].y = 5.0f;
                    barrels_[i].vx = -3.5f; // 向左滚动
                }
            } else if (barrels_[i].layer == 2) {
                // 经过梯子 2 (x=3) 时有 40% 概率滚下梯子
                if (fabsf(barrels_[i].x - 3.0f) < 0.25f && (rand() % 10 < 4)) {
                    barrels_[i].layer = 1;
                    barrels_[i].falling_ladder = true;
                    barrels_[i].x = 3.0f;
                } else if (barrels_[i].x <= 2.0f) {
                    // 滚出左边缘跌落到层 1 (y=10)
                    barrels_[i].layer = 1;
                    barrels_[i].x = 2.0f;
                    barrels_[i].y = 9.0f;
                    barrels_[i].vx = 3.5f; // 向右滚动
                }
            } else if (barrels_[i].layer == 1) {
                // 经过梯子 1 (x=12) 时有 40% 概率滚下梯子
                if (fabsf(barrels_[i].x - 12.0f) < 0.25f && (rand() % 10 < 4)) {
                    barrels_[i].layer = 0;
                    barrels_[i].falling_ladder = true;
                    barrels_[i].x = 12.0f;
                } else if (barrels_[i].x >= 13.0f) {
                    // 滚出右边缘跌落到底层 0 (y=14)
                    barrels_[i].layer = 0;
                    barrels_[i].x = 13.0f;
                    barrels_[i].y = 13.0f;
                    barrels_[i].vx = -3.5f; // 向左滚动
                }
            } else if (barrels_[i].layer == 0) {
                if (barrels_[i].x < -0.5f) {
                    barrels_[i].active = false; // 滚出画面
                }
            }
        }

        // 碰撞与跳跃跨越检测
        float dist = fabsf(player_x_ - barrels_[i].x) + fabsf(player_y_ - barrels_[i].y);
        if (dist <= 0.85f) {
            if (hammer_timer_ > 0.0f) {
                // 铁锤暴击砸碎木桶
                barrels_[i].active = false;
                score_ += 300;
                if (score_ > high_score_) high_score_ = score_;
            } else {
                // 玩家被木桶碾碎
                lives_--;
                if (lives_ <= 0) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                } else {
                    InitLevel();
                    return;
                }
            }
        } else if (is_jumping_ && player_y_ < barrels_[i].y && fabsf(player_x_ - barrels_[i].x) < 0.8f) {
            // 跳跃跨越滚木桶奖励
            score_ += 100;
            if (score_ > high_score_) high_score_ = score_;
        }
    }
}

void Game023DonkeyKong::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) state_ = STATE_PLAYING;
        return;
    }

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        // 1. 铁锤计时器
        if (hammer_timer_ > 0.0f) {
            hammer_timer_ -= dt;
            if (hammer_timer_ < 0.0f) hammer_timer_ = 0.0f;
        }

        // 2. 拾取铁锤检测
        if (hammer_available_ && (int)roundf(player_x_) == hammer_x_ && (int)roundf(player_y_) == hammer_y_) {
            hammer_available_ = false;
            hammer_timer_ = 5.0f;
            score_ += 200;
            if (score_ > high_score_) high_score_ = score_;
        }

        // 3. 玩家攀爬与移动物理
        int px = (int)roundf(player_x_);
        int py = (int)roundf(player_y_);

        if (is_climbing_) {
            float climb_speed = 4.0f;
            if (keys_down & KEY_UP) player_y_ -= climb_speed * dt;
            if (keys_down & KEY_DOWN) player_y_ += climb_speed * dt;

            // 检查是否爬出梯子
            int check_y = (int)roundf(player_y_);
            if (!IsOnLadder(px, check_y)) {
                is_climbing_ = false;
            }
        } else {
            // 平台横向移动
            float move_speed = 5.5f;
            if (keys_down & KEY_LEFT) player_x_ -= move_speed * dt;
            if (keys_down & KEY_RIGHT) player_x_ += move_speed * dt;

            if (player_x_ < 0.0f) player_x_ = 0.0f;
            if (player_x_ > 15.0f) player_x_ = 15.0f;

            // 触发梯子攀爬
            if ((keys_down & (KEY_UP | KEY_DOWN)) && IsOnLadder(px, py)) {
                is_climbing_ = true;
                player_x_ = (float)px;
                player_vy_ = 0.0f;
                is_jumping_ = false;
                return;
            }

            // 跳跃物理
            if (!is_jumping_ && (keys_pressed & (KEY_A | KEY_B))) {
                is_jumping_ = true;
                jump_base_y_ = player_y_;
                player_vy_ = -6.8f;
            }

            if (is_jumping_) {
                player_vy_ += 14.0f * dt; // 重力
                player_y_ += player_vy_ * dt;

                if (player_y_ >= jump_base_y_) {
                    player_y_ = jump_base_y_;
                    player_vy_ = 0.0f;
                    is_jumping_ = false;
                }
            } else {
                // 吸附到所在横梁
                if (player_y_ <= 3.0f && player_x_ >= 4.0f && player_x_ <= 11.0f) player_y_ = 1.0f;
                else if (player_y_ <= 7.0f && player_x_ >= 2.0f) player_y_ = 5.0f;
                else if (player_y_ <= 11.0f && player_x_ <= 13.0f) player_y_ = 9.0f;
                else player_y_ = 13.0f;
            }
        }

        // 4. 更新木桶物理与碰撞
        UpdateBarrels(dt);

        // 5. 拯救宝琳通关判定
        if (player_y_ <= 2.5f && player_x_ >= 9.0f) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            score_ += 1000;
            if (score_ > high_score_) high_score_ = score_;
        }
    }
}

void Game023DonkeyKong::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 绘制 4 层红色倾斜钢梁 (Girders) [231, 76, 60]
    // 层 0 (y=14)
    for (int x = 0; x < 16; ++x) {
        int idx = (14 * 16 + x) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }
    // 层 1 (y=10, x=0..13)
    for (int x = 0; x <= 13; ++x) {
        int idx = (10 * 16 + x) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }
    // 层 2 (y=6, x=2..15)
    for (int x = 2; x <= 15; ++x) {
        int idx = (6 * 16 + x) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }
    // 层 3 (y=2, x=4..11)
    for (int x = 4; x <= 11; ++x) {
        int idx = (2 * 16 + x) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }

    // 2. 绘制青蓝梯子 (Ladders) [52, 152, 219]
    for (int y = 10; y <= 14; ++y) {
        int idx = (y * 16 + 12) * 3;
        fb_rgb24[idx + 0] = 52; fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219;
    }
    for (int y = 6; y <= 10; ++y) {
        int idx = (y * 16 + 3) * 3;
        fb_rgb24[idx + 0] = 52; fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219;
    }
    for (int y = 2; y <= 6; ++y) {
        int idx = (y * 16 + 7) * 3;
        fb_rgb24[idx + 0] = 52; fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219;
    }

    // 3. 绘制大金刚 (棕褐巨猿 [140, 70, 20]) 与被困宝琳 (粉红淑女 [255, 105, 180])
    int dk_idx = (1 * 16 + 4) * 3;
    fb_rgb24[dk_idx + 0] = 140; fb_rgb24[dk_idx + 1] = 70; fb_rgb24[dk_idx + 2] = 20;

    int pauline_idx = (1 * 16 + 10) * 3;
    fb_rgb24[pauline_idx + 0] = 255; fb_rgb24[pauline_idx + 1] = 105; fb_rgb24[pauline_idx + 2] = 180;

    // 4. 绘制铁锤道具 (耀眼金黄 [241, 196, 15])
    if (hammer_available_) {
        int h_idx = (hammer_y_ * 16 + hammer_x_) * 3;
        fb_rgb24[h_idx + 0] = 241; fb_rgb24[h_idx + 1] = 196; fb_rgb24[h_idx + 2] = 15;
    }

    // 5. 绘制滚动的木桶 (深橘红 [230, 126, 34])
    for (int i = 0; i < MAX_BARRELS; ++i) {
        if (!barrels_[i].active) continue;
        int bx = (int)roundf(barrels_[i].x);
        int by = (int)roundf(barrels_[i].y);
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            fb_rgb24[idx + 0] = 230; fb_rgb24[idx + 1] = 126; fb_rgb24[idx + 2] = 34;
        }
    }

    // 6. 绘制玩家跳跳人 (持铁锤金黄闪烁 [255, 215, 0], 平常纯白 [255, 255, 255])
    if (lives_ > 0) {
        int px = (int)roundf(player_x_);
        int py = (int)roundf(player_y_);
        if (px >= 0 && px < 16 && py >= 0 && py < 16) {
            int idx = (py * 16 + px) * 3;
            if (hammer_timer_ > 0.0f) {
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 215; fb_rgb24[idx + 2] = 0;
            } else {
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
            }
        }
    }

    // 7. 顶部生命指示
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + i) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }

    // 8. 胜负特效
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

CartridgeStatus Game023DonkeyKong::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    // 进度基于玩家所在高度 (13 到 1 为 0% ~ 100%)
    int prog = (int)(((13.0f - player_y_) / 12.0f) * 100.0f);
    if (prog < 0) prog = 0;
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

} // namespace arcade
