// game_008_breakout.cpp —— 经典打砖块 1976 核心实现
#include "game_008_breakout.h"
#include <string.h>
#include <math.h>

namespace arcade {

Game008Breakout::Game008Breakout()
    : state_(STATE_TITLE),
      paddle_x_(6.0f),
      paddle_w_(4.0f),
      ball_x_(8.0f),
      ball_y_(13.0f),
      ball_vx_(6.0f),
      ball_vy_(-8.0f),
      ball_stuck_(true),
      remaining_bricks_(0),
      lives_(3),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

void Game008Breakout::ResetBallAndPaddle() {
    paddle_x_ = 6.0f;
    paddle_w_ = 4.0f;
    ball_stuck_ = true;
    ball_x_ = paddle_x_ + paddle_w_ * 0.5f;
    ball_y_ = 13.0f;
    ball_vx_ = 6.5f;
    ball_vy_ = -8.5f;
}

void Game008Breakout::Init() {
    Reset();
}

void Game008Breakout::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    remaining_bricks_ = kRows * kCols;

    // 初始化 4 排 8 列砖块 (Row 0: 红, Row 1: 橙, Row 2: 绿, Row 3: 黄)
    for (int r = 0; r < kRows; ++r) {
        uint8_t cr, cg, cb, hp;
        if (r == 0)      { cr = 231; cg = 76;  cb = 60;  hp = 2; } // 红色耐久 2
        else if (r == 1) { cr = 230; cg = 126; cb = 34;  hp = 1; } // 橙色耐久 1
        else if (r == 2) { cr = 46;  cg = 204; cb = 113; hp = 1; } // 绿色耐久 1
        else             { cr = 241; cg = 196; cb = 15;  hp = 1; } // 黄色耐久 1

        for (int c = 0; c < kCols; ++c) {
            bricks_[r][c].hp = hp;
            bricks_[r][c].r = cr;
            bricks_[r][c].g = cg;
            bricks_[r][c].b = cb;
        }
    }

    ResetBallAndPaddle();
}

void Game008Breakout::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        // 演示状态：挡板自动跟随小球
        paddle_x_ = ball_x_ - paddle_w_ * 0.5f;
        if (paddle_x_ < 0.0f) paddle_x_ = 0.0f;
        if (paddle_x_ > 16.0f - paddle_w_) paddle_x_ = 16.0f - paddle_w_;

        ball_x_ += ball_vx_ * dt;
        ball_y_ += ball_vy_ * dt;
        if (ball_x_ <= 0.0f || ball_x_ >= 15.0f) ball_vx_ = -ball_vx_;
        if (ball_y_ <= 0.0f || ball_y_ >= 13.0f) ball_vy_ = -ball_vy_;

        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT))) {
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

        // 挡板移动
        const float paddle_speed = 12.0f;
        if (keys_down & KEY_LEFT) {
            paddle_x_ -= paddle_speed * dt;
        } else if (keys_down & KEY_RIGHT) {
            paddle_x_ += paddle_speed * dt;
        }
        if (paddle_x_ < 0.0f) paddle_x_ = 0.0f;
        if (paddle_x_ > 16.0f - paddle_w_) paddle_x_ = 16.0f - paddle_w_;

        // 发球判定 (吸附在挡板上时，按动作键开球)
        if (ball_stuck_) {
            ball_x_ = paddle_x_ + paddle_w_ * 0.5f;
            ball_y_ = 13.0f;
            if (keys_pressed & (KEY_A | KEY_B | KEY_UP | KEY_START)) {
                ball_stuck_ = false;
                ball_vx_ = ((keys_down & KEY_LEFT) ? -6.0f : (keys_down & KEY_RIGHT) ? 6.0f : 5.0f);
                ball_vy_ = -8.5f;
            }
            return;
        }

        // 小球物理移动
        ball_x_ += ball_vx_ * dt;
        ball_y_ += ball_vy_ * dt;

        // 左右墙壁反弹
        if (ball_x_ <= 0.0f) {
            ball_x_ = 0.0f;
            ball_vx_ = fabsf(ball_vx_);
        } else if (ball_x_ >= 15.0f) {
            ball_x_ = 15.0f;
            ball_vx_ = -fabsf(ball_vx_);
        }

        // 天花板反弹
        if (ball_y_ <= 0.0f) {
            ball_y_ = 0.0f;
            ball_vy_ = fabsf(ball_vy_);
        }

        // 挡板碰撞检测 (y = 14)
        if (ball_vy_ > 0.0f && ball_y_ >= 13.3f && ball_y_ <= 14.5f) {
            if (ball_x_ >= paddle_x_ - 0.5f && ball_x_ <= paddle_x_ + paddle_w_ + 0.5f) {
                ball_y_ = 13.2f;
                // 反弹向上
                float speed = sqrtf(ball_vx_ * ball_vx_ + ball_vy_ * ball_vy_);
                if (speed < 15.0f) speed += 0.2f; // 逐渐微提速

                // 冲击切角偏折
                float hit_offset = (ball_x_ - (paddle_x_ + paddle_w_ * 0.5f)) / (paddle_w_ * 0.5f);
                ball_vx_ = hit_offset * 7.5f;
                ball_vy_ = -sqrtf(fmaxf(16.0f, speed * speed - ball_vx_ * ball_vx_));
            }
        }

        // 砖块碰撞检测 (网格行 y 从 2 到 5, 列 c 从 0 到 7，每块宽 2)
        int ball_row = (int)roundf(ball_y_) - 2;
        int ball_col = (int)roundf(ball_x_) / 2;

        if (ball_row >= 0 && ball_row < kRows && ball_col >= 0 && ball_col < kCols) {
            if (bricks_[ball_row][ball_col].hp > 0) {
                bricks_[ball_row][ball_col].hp--;
                if (bricks_[ball_row][ball_col].hp == 0) {
                    remaining_bricks_--;
                    // 分数累加 (越靠上排分越高)
                    uint32_t pts = (kRows - ball_row) * 15;
                    score_ += pts;
                    if (score_ > high_score_) high_score_ = score_;
                }

                // 物理反弹
                ball_vy_ = -ball_vy_;

                // 全部击碎清屏通关判定
                if (remaining_bricks_ <= 0) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }

        // 跌落底部丢命
        if (ball_y_ > 15.5f) {
            if (lives_ > 0) lives_--;
            if (lives_ == 0) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
            } else {
                ResetBallAndPaddle();
            }
        }
    }
}

void Game008Breakout::Render(uint8_t* fb_rgb24) {
    // 1. 复古纯黑街机底色
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 2. 绘制 4 排彩色砖块 (从 y=2 到 y=5)
    for (int r = 0; r < kRows; ++r) {
        int y = r + 2;
        for (int c = 0; c < kCols; ++c) {
            if (bricks_[r][c].hp > 0) {
                int x0 = c * 2;
                int x1 = c * 2 + 1;
                uint8_t cr = bricks_[r][c].r;
                uint8_t cg = bricks_[r][c].g;
                uint8_t cb = bricks_[r][c].b;

                // 若耐久剩 1 (红砖受损态)，颜色微暗区分
                if (bricks_[r][c].hp == 1 && r == 0) {
                    cr = 192; cg = 57; cb = 43;
                }

                int idx0 = (y * 16 + x0) * 3;
                int idx1 = (y * 16 + x1) * 3;
                fb_rgb24[idx0 + 0] = cr; fb_rgb24[idx0 + 1] = cg; fb_rgb24[idx0 + 2] = cb;
                fb_rgb24[idx1 + 0] = cr; fb_rgb24[idx1 + 1] = cg; fb_rgb24[idx1 + 2] = cb;
            }
        }
    }

    // 3. 绘制底部发光挡板 (y = 14, 青蓝光泽)
    int px_start = (int)roundf(paddle_x_);
    int px_end = (int)roundf(paddle_x_ + paddle_w_);
    for (int x = px_start; x < px_end; ++x) {
        if (x >= 0 && x < 16) {
            int idx = (14 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 52;
            fb_rgb24[idx + 1] = 152;
            fb_rgb24[idx + 2] = 219;
        }
    }

    // 4. 绘制小球 (耀眼白)
    int bx = (int)roundf(ball_x_);
    int by = (int)roundf(ball_y_);
    if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
        int idx = (by * 16 + bx) * 3;
        fb_rgb24[idx + 0] = fb_rgb24[idx + 1] = fb_rgb24[idx + 2] = 255;
    }

    // 5. 顶部生命显示 (左上角显示剩余球数 ❤️)
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + (i * 2)) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }

    // 6. 通关/死亡特效
    if (state_ == STATE_VICTORY) {
        // 全屏彩虹高光庆祝
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
        }
    } else if (state_ == STATE_GAMEOVER) {
        // 底部红线
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
        }
    }
}

CartridgeStatus Game008Breakout::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(((kRows * kCols - remaining_bricks_) * 100) / (kRows * kCols));
    return st;
}

} // namespace arcade
