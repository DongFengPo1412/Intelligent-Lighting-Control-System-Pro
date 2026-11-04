// game_020_pong.cpp —— 目标 #020 双人乒乓 核心实现
#include "game_020_pong.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

Game020Pong::Game020Pong()
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
      state_timer_(0.0f),
      anim_timer_(0.0f),
      high_score_(0) {
}

float Game020Pong::AiRandError() {
    ai_seed_ = ai_seed_ * 1103515245u + 12345u;
    float r = (float)((ai_seed_ >> 16) & 0x7FFF) / 32767.0f;  // 0..1
    return (r * 2.0f - 1.0f) * kAiMaxError;
}

void Game020Pong::ResetBall(bool serve_to_right) {
    ball_x_ = 7.5f;
    ball_y_ = 7.5f;
    float base_speed = 7.5f;
    ball_vx_ = serve_to_right ? base_speed : -base_speed;
    ball_vy_ = ((ball_y_ > 7.5f) ? -2.5f : 2.5f);
    serve_delay_ = 0.6f;
    ai_error_ = AiRandError();
}

void Game020Pong::Init() {
    Reset();
}

void Game020Pong::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    p1_y_ = 6.0f;
    p2_y_ = 6.0f;
    paddle_h_ = 4.0f;
    p1_score_ = 0;
    p2_score_ = 0;
    p2_is_ai_ = true;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    ResetBall(true);
}

void Game020Pong::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        p1_y_ = 6.0f;
        p2_y_ = 6.0f;
        paddle_h_ = 4.0f;
        p1_score_ = 0;
        p2_score_ = 0;
        p2_is_ai_ = true;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        ResetBall(true);
    }
}

void Game020Pong::Pause() {
    if (state_ == STATE_PLAYING) state_ = STATE_PAUSED;
}

void Game020Pong::Resume() {
    if (state_ == STATE_PAUSED) state_ = STATE_PLAYING;
}

void Game020Pong::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
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
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN))) {
            Start();
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

        const float paddle_speed = 9.5f;

        if (keys_down & KEY_UP) {
            p1_y_ -= paddle_speed * dt;
        } else if (keys_down & KEY_DOWN) {
            p1_y_ += paddle_speed * dt;
        }
        if (p1_y_ < 0.0f) p1_y_ = 0.0f;
        if (p1_y_ > 16.0f - paddle_h_) p1_y_ = 16.0f - paddle_h_;

        if (keys_down & KEY_A) {
            p2_is_ai_ = false;
            p2_y_ -= paddle_speed * dt;
        } else if (keys_down & KEY_B) {
            p2_is_ai_ = false;
            p2_y_ += paddle_speed * dt;
        } else if (p2_is_ai_) {
            // 只有球朝 AI 飞来时才追球, 否则缓慢回中; 追球目标带有随机误差
            float ai_target_y;
            float ai_speed;
            if (ball_vx_ > 0.0f) {
                ai_target_y = ball_y_ - (paddle_h_ * 0.5f) + ai_error_;
                ai_speed = kAiSpeed * dt;
            } else {
                ai_target_y = 8.0f - (paddle_h_ * 0.5f);
                ai_speed = kAiSpeed * 0.5f * dt;
            }
            if (p2_y_ < ai_target_y - 0.3f) p2_y_ += ai_speed;
            else if (p2_y_ > ai_target_y + 0.3f) p2_y_ -= ai_speed;
        }
        if (p2_y_ < 0.0f) p2_y_ = 0.0f;
        if (p2_y_ > 16.0f - paddle_h_) p2_y_ = 16.0f - paddle_h_;

        if (serve_delay_ > 0.0f) {
            serve_delay_ -= dt;
            return;
        }

        ball_x_ += ball_vx_ * dt;
        ball_y_ += ball_vy_ * dt;

        if (ball_y_ <= 0.0f) {
            ball_y_ = 0.0f;
            ball_vy_ = fabsf(ball_vy_);
        } else if (ball_y_ >= 15.0f) {
            ball_y_ = 15.0f;
            ball_vy_ = -fabsf(ball_vy_);
        }

        if (ball_vx_ < 0.0f && ball_x_ <= 1.8f && ball_x_ >= 0.5f) {
            if (ball_y_ >= p1_y_ - 0.5f && ball_y_ <= p1_y_ + paddle_h_ + 0.5f) {
                ball_x_ = 1.9f;
                float speed = fabsf(ball_vx_) * 1.05f;
                if (speed > 16.0f) speed = 16.0f;
                ball_vx_ = speed;

                float hit_offset = (ball_y_ - (p1_y_ + paddle_h_ * 0.5f)) / (paddle_h_ * 0.5f);
                ball_vy_ = hit_offset * 7.5f;
                ai_error_ = AiRandError();
            }
        }

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

        if (ball_x_ < 0.0f) {
            p2_score_++;
            if (p2_score_ >= kWinningScore) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                uint32_t final_score = p1_score_ * 10;
                if (final_score > high_score_) {
                    high_score_ = final_score;
                    ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                }
            } else {
                ResetBall(false);
            }
        } else if (ball_x_ > 15.0f) {
            p1_score_++;
            uint32_t current_score = p1_score_ * 10;
            if (current_score > high_score_) {
                high_score_ = current_score;
                ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
            }
            if (p1_score_ >= kWinningScore) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
            } else {
                ResetBall(true);
            }
        }
    }
}

void Game020Pong::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, p1_score_ * 10, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, 16 * 16 * 3);

    for (int y = 0; y < 16; y += 2) {
        int idx = (y * 16 + 7) * 3;
        fb_rgb24[idx + 0] = fb_rgb24[idx + 1] = fb_rgb24[idx + 2] = 40;
    }

    int p1_top = (int)roundf(p1_y_);
    int p1_bot = p1_top + (int)paddle_h_;
    for (int y = p1_top; y < p1_bot && y < 16; ++y) {
        if (y >= 0) {
            int idx = (y * 16 + 1) * 3;
            fb_rgb24[idx + 0] = 52;
            fb_rgb24[idx + 1] = 152;
            fb_rgb24[idx + 2] = 219;
        }
    }

    int p2_top = (int)roundf(p2_y_);
    int p2_bot = p2_top + (int)paddle_h_;
    for (int y = p2_top; y < p2_bot && y < 16; ++y) {
        if (y >= 0) {
            int idx = (y * 16 + 14) * 3;
            fb_rgb24[idx + 0] = 231;
            fb_rgb24[idx + 1] = 76;
            fb_rgb24[idx + 2] = 60;
        }
    }

    int bx = (int)roundf(ball_x_);
    int by = (int)roundf(ball_y_);
    if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
        int idx = (by * 16 + bx) * 3;
        fb_rgb24[idx + 0] = 241;
        fb_rgb24[idx + 1] = 196;
        fb_rgb24[idx + 2] = 15;
    }

    for (int i = 0; i < p1_score_ && i < 5; ++i) {
        int idx = (0 * 16 + (3 + i)) * 3;
        fb_rgb24[idx + 0] = 52; fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219;
    }
    for (int i = 0; i < p2_score_ && i < 5; ++i) {
        int idx = (0 * 16 + (12 - i)) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 6; y <= 9; ++y) {
            int idx1 = (y * 16 + 6) * 3;
            int idx2 = (y * 16 + 9) * 3;
            fb_rgb24[idx1 + 0] = fb_rgb24[idx1 + 1] = fb_rgb24[idx1 + 2] = 250;
            fb_rgb24[idx2 + 0] = fb_rgb24[idx2 + 1] = fb_rgb24[idx2 + 2] = 250;
        }
    }
}

CartridgeStatus Game020Pong::GetStatus() const {
    CartridgeStatus st;
    st.score = p1_score_ * 10;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(p1_score_ * 20);
    return st;
}

} // namespace arcade

