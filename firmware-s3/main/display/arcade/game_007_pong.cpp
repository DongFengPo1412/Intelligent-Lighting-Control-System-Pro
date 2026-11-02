// game_007_pong.cpp —— 双人乒乓 1972 核心实现
#include "game_007_pong.h"
#include <string.h>
#include <math.h>

namespace arcade {

Game007Pong::Game007Pong()
    : state_(STATE_TITLE),
      p1_y_(6.0f),
      p2_y_(6.0f),
      paddle_h_(4.0f),
      ball_x_(7.5f),
      ball_y_(7.5f),
      ball_vx_(7.0f),
      ball_vy_(3.0f),
      p1_score_(0),
      p2_score_(0),
      p2_is_ai_(true),
      serve_delay_(0.0f),
      state_timer_(0.0f) {
}

void Game007Pong::ResetBall(bool serve_to_right) {
    ball_x_ = 7.5f;
    ball_y_ = 7.5f;
    float base_speed = 7.5f;
    ball_vx_ = serve_to_right ? base_speed : -base_speed;
    ball_vy_ = ((ball_y_ > 7.5f) ? -2.5f : 2.5f);
    serve_delay_ = 0.6f; // 发球短暂倒计时
}

void Game007Pong::Init() {
    Reset();
}

void Game007Pong::Reset() {
    state_ = STATE_PLAYING;
    p1_y_ = 6.0f;
    p2_y_ = 6.0f;
    paddle_h_ = 4.0f;
    p1_score_ = 0;
    p2_score_ = 0;
    p2_is_ai_ = true;
    state_timer_ = 0.0f;
    ResetBall(true);
}

void Game007Pong::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        // 标题画面演示：双 AI 自动对打
        float paddle_speed = 6.0f * dt;
        if (ball_y_ < p1_y_ + 1.5f && p1_y_ > 0.0f) p1_y_ -= paddle_speed;
        else if (ball_y_ > p1_y_ + 2.5f && p1_y_ < 16.0f - paddle_h_) p1_y_ += paddle_speed;

        if (ball_y_ < p2_y_ + 1.5f && p2_y_ > 0.0f) p2_y_ -= paddle_speed;
        else if (ball_y_ > p2_y_ + 2.5f && p2_y_ < 16.0f - paddle_h_) p2_y_ += paddle_speed;

        ball_x_ += ball_vx_ * dt;
        ball_y_ += ball_vy_ * dt;
        if (ball_y_ <= 0.0f || ball_y_ >= 15.0f) ball_vy_ = -ball_vy_;
        if (ball_x_ <= 2.0f || ball_x_ >= 13.0f) ball_vx_ = -ball_vx_;

        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN))) {
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

        // 挡板速度
        const float paddle_speed = 9.5f;

        // 1. P1 (左侧挡板) 控制：UP / DOWN
        if (keys_down & KEY_UP) {
            p1_y_ -= paddle_speed * dt;
        } else if (keys_down & KEY_DOWN) {
            p1_y_ += paddle_speed * dt;
        }
        if (p1_y_ < 0.0f) p1_y_ = 0.0f;
        if (p1_y_ > 16.0f - paddle_h_) p1_y_ = 16.0f - paddle_h_;

        // 2. P2 (右侧挡板) 控制：如果有 A/B 键输入，则由双人玩家控制；否则由智能 AI 补位
        if (keys_down & KEY_A) {
            p2_is_ai_ = false;
            p2_y_ -= paddle_speed * dt;
        } else if (keys_down & KEY_B) {
            p2_is_ai_ = false;
            p2_y_ += paddle_speed * dt;
        } else if (p2_is_ai_) {
            // AI 智能平滑追踪小球 Y 坐标
            float ai_target_y = ball_y_ - (paddle_h_ * 0.5f);
            float ai_speed = 7.0f * dt; // 微带反应延迟
            if (p2_y_ < ai_target_y - 0.5f) p2_y_ += ai_speed;
            else if (p2_y_ > ai_target_y + 0.5f) p2_y_ -= ai_speed;
        }
        if (p2_y_ < 0.0f) p2_y_ = 0.0f;
        if (p2_y_ > 16.0f - paddle_h_) p2_y_ = 16.0f - paddle_h_;

        // 发球短暂停顿
        if (serve_delay_ > 0.0f) {
            serve_delay_ -= dt;
            return;
        }

        // 3. 小球运动演算
        ball_x_ += ball_vx_ * dt;
        ball_y_ += ball_vy_ * dt;

        // 上下墙壁刚体反弹
        if (ball_y_ <= 0.0f) {
            ball_y_ = 0.0f;
            ball_vy_ = fabsf(ball_vy_);
        } else if (ball_y_ >= 15.0f) {
            ball_y_ = 15.0f;
            ball_vy_ = -fabsf(ball_vy_);
        }

        // 4. 左侧 P1 挡板碰撞检测 (x = 1)
        if (ball_vx_ < 0.0f && ball_x_ <= 1.8f && ball_x_ >= 0.5f) {
            if (ball_y_ >= p1_y_ - 0.5f && ball_y_ <= p1_y_ + paddle_h_ + 0.5f) {
                ball_x_ = 1.9f;
                // 每次对拉球速线性微增 5%
                float speed = fabsf(ball_vx_) * 1.05f;
                if (speed > 16.0f) speed = 16.0f;
                ball_vx_ = speed;

                // 冲击切角反弹公式：撞在挡板边缘产生大斜率，撞在中央产生平直反弹
                float hit_offset = (ball_y_ - (p1_y_ + paddle_h_ * 0.5f)) / (paddle_h_ * 0.5f);
                ball_vy_ = hit_offset * 7.5f;
            }
        }

        // 5. 右侧 P2 挡板碰撞检测 (x = 14)
        if (ball_vx_ > 0.0f && ball_x_ >= 13.2f && ball_x_ <= 14.8f) {
            if (ball_y_ >= p2_y_ - 0.5f && ball_y_ <= p2_y_ + paddle_h_ + 0.5f) {
                ball_x_ = 13.1f;
                float speed = fabsf(ball_vx_) * 1.05f;
                if (speed > 16.0f) speed = 16.0f;
                ball_vx_ = -speed;

                float hit_offset = (ball_y_ - (p2_y_ + paddle_h_ * 0.5f)) / (paddle_h_ * 0.5f);
                ball_vy_ = hit_offset * 7.5f;
            }
        }

        // 6. 得分与出界判定
        if (ball_x_ < 0.0f) {
            // 右方 P2 得分
            p2_score_++;
            if (p2_score_ >= kWinningScore) {
                state_ = STATE_GAMEOVER; // P1 败北
                state_timer_ = 0.0f;
            } else {
                ResetBall(false); // 发给得分方
            }
        } else if (ball_x_ > 15.0f) {
            // 左方 P1 得分
            p1_score_++;
            if (p1_score_ >= kWinningScore) {
                state_ = STATE_VICTORY;  // P1 获胜
                state_timer_ = 0.0f;
            } else {
                ResetBall(true);
            }
        }
    }
}

void Game007Pong::Render(uint8_t* fb_rgb24) {
    // 1. 经典街机黑夜纯黑底色
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 2. 中央虚线球网 (在 x=7, x=8 处画虚线)
    for (int y = 0; y < 16; y += 2) {
        int idx = (y * 16 + 7) * 3;
        fb_rgb24[idx + 0] = fb_rgb24[idx + 1] = fb_rgb24[idx + 2] = 40;
    }

    // 3. 绘制左侧 P1 挡板 (x=1，青白发光)
    int p1_top = (int)roundf(p1_y_);
    int p1_bot = (int)roundf(p1_y_ + paddle_h_);
    for (int y = p1_top; y < p1_bot; ++y) {
        if (y >= 0 && y < 16) {
            int idx = (y * 16 + 1) * 3;
            fb_rgb24[idx + 0] = 0; fb_rgb24[idx + 1] = 210; fb_rgb24[idx + 2] = 255;
        }
    }

    // 4. 绘制右侧 P2 挡板 (x=14，琥珀金发光)
    int p2_top = (int)roundf(p2_y_);
    int p2_bot = (int)roundf(p2_y_ + paddle_h_);
    for (int y = p2_top; y < p2_bot; ++y) {
        if (y >= 0 && y < 16) {
            int idx = (y * 16 + 14) * 3;
            fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 168; fb_rgb24[idx + 2] = 0;
        }
    }

    // 5. 绘制反弹小球 (高亮白)
    int bx = (int)roundf(ball_x_);
    int by = (int)roundf(ball_y_);
    if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
        int idx = (by * 16 + bx) * 3;
        fb_rgb24[idx + 0] = fb_rgb24[idx + 1] = fb_rgb24[idx + 2] = 255;
    }

    // 6. 顶部比分光点显示 (左侧用点数显示 P1 分，右侧显示 P2 分)
    for (int i = 0; i < p1_score_; ++i) {
        int idx = (0 * 16 + (3 + i)) * 3;
        fb_rgb24[idx + 0] = 0; fb_rgb24[idx + 1] = 210; fb_rgb24[idx + 2] = 255;
    }
    for (int i = 0; i < p2_score_; ++i) {
        int idx = (0 * 16 + (12 - i)) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 168; fb_rgb24[idx + 2] = 0;
    }

    // 7. 结算特效
    if (state_ == STATE_VICTORY) {
        // 左半屏绿光庆祝
        for (int y = 0; y < 16; ++y) {
            int idx = (y * 16 + 0) * 3;
            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
        }
    } else if (state_ == STATE_GAMEOVER) {
        // 右半屏红光宣告
        for (int y = 0; y < 16; ++y) {
            int idx = (y * 16 + 15) * 3;
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
        }
    }
}

CartridgeStatus Game007Pong::GetStatus() const {
    CartridgeStatus st;
    st.score = ((uint32_t)p1_score_ << 16) | (uint32_t)p2_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((p1_score_ + p2_score_) * 10);
    return st;
}

} // namespace arcade
