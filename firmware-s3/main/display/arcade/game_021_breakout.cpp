// game_021_breakout.cpp —— 目标 #021 经典打砖块 核心实现
#include "game_021_breakout.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

Game021Breakout::Game021Breakout()
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
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
}

void Game021Breakout::ResetBallAndPaddle() {
    paddle_x_ = 6.0f;
    paddle_w_ = 4.0f;
    ball_stuck_ = true;
    ball_x_ = paddle_x_ + paddle_w_ * 0.5f;
    ball_y_ = 13.0f;
    ball_vx_ = 6.5f;
    ball_vy_ = -8.5f;
}

void Game021Breakout::Init() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    Reset();
}

void Game021Breakout::Reset() {
    state_ = STATE_TITLE;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    remaining_bricks_ = kRows * kCols;

    for (int r = 0; r < kRows; ++r) {
        uint8_t cr, cg, cb, hp;
        if (r == 0)      { cr = 231; cg = 76;  cb = 60;  hp = 2; }
        else if (r == 1) { cr = 230; cg = 126; cb = 34;  hp = 1; }
        else if (r == 2) { cr = 46;  cg = 204; cb = 113; hp = 1; }
        else             { cr = 241; cg = 196; cb = 15;  hp = 1; }

        for (int c = 0; c < kCols; ++c) {
            bricks_[r][c].hp = hp;
            bricks_[r][c].r = cr;
            bricks_[r][c].g = cg;
            bricks_[r][c].b = cb;
        }
    }

    ResetBallAndPaddle();
}

void Game021Breakout::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        lives_ = 3;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        remaining_bricks_ = kRows * kCols;

        for (int r = 0; r < kRows; ++r) {
            uint8_t cr, cg, cb, hp;
            if (r == 0)      { cr = 231; cg = 76;  cb = 60;  hp = 2; }
            else if (r == 1) { cr = 230; cg = 126; cb = 34;  hp = 1; }
            else if (r == 2) { cr = 46;  cg = 204; cb = 113; hp = 1; }
            else             { cr = 241; cg = 196; cb = 15;  hp = 1; }

            for (int c = 0; c < kCols; ++c) {
                bricks_[r][c].hp = hp;
                bricks_[r][c].r = cr;
                bricks_[r][c].g = cg;
                bricks_[r][c].b = cb;
            }
        }
        ResetBallAndPaddle();
    }
}

void Game021Breakout::Pause() {
    if (state_ == STATE_PLAYING) state_ = STATE_PAUSED;
}

void Game021Breakout::Resume() {
    if (state_ == STATE_PAUSED) state_ = STATE_PLAYING;
}

void Game021Breakout::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        paddle_x_ = ball_x_ - paddle_w_ * 0.5f;
        if (paddle_x_ < 0.0f) paddle_x_ = 0.0f;
        if (paddle_x_ > 16.0f - paddle_w_) paddle_x_ = 16.0f - paddle_w_;

        ball_x_ += ball_vx_ * dt;
        ball_y_ += ball_vy_ * dt;
        if (ball_x_ <= 0.0f || ball_x_ >= 15.0f) ball_vx_ = -ball_vx_;
        if (ball_y_ <= 0.0f || ball_y_ >= 13.0f) ball_vy_ = -ball_vy_;

        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT))) {
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

        const float paddle_speed = 12.0f;
        if (keys_down & KEY_LEFT) {
            paddle_x_ -= paddle_speed * dt;
        } else if (keys_down & KEY_RIGHT) {
            paddle_x_ += paddle_speed * dt;
        }
        if (paddle_x_ < 0.0f) paddle_x_ = 0.0f;
        if (paddle_x_ > 16.0f - paddle_w_) paddle_x_ = 16.0f - paddle_w_;

        if (ball_stuck_) {
            ball_x_ = paddle_x_ + paddle_w_ * 0.5f;
            ball_y_ = 13.0f;
            if (keys_pressed & (KEY_A | KEY_B | KEY_UP | KEY_START)) {
                ball_stuck_ = false;
            }
            return;
        }

        ball_x_ += ball_vx_ * dt;
        ball_y_ += ball_vy_ * dt;

        if (ball_x_ <= 0.0f) {
            ball_x_ = 0.0f;
            ball_vx_ = fabsf(ball_vx_);
        } else if (ball_x_ >= 15.0f) {
            ball_x_ = 15.0f;
            ball_vx_ = -fabsf(ball_vx_);
        }

        if (ball_y_ <= 0.0f) {
            ball_y_ = 0.0f;
            ball_vy_ = fabsf(ball_vy_);
        }

        if (ball_vy_ > 0.0f && ball_y_ >= 13.2f && ball_y_ <= 14.8f) {
            if (ball_x_ >= paddle_x_ - 0.5f && ball_x_ <= paddle_x_ + paddle_w_ + 0.5f) {
                ball_y_ = 13.1f;
                ball_vy_ = -fabsf(ball_vy_);

                float hit_offset = (ball_x_ - (paddle_x_ + paddle_w_ * 0.5f)) / (paddle_w_ * 0.5f);
                ball_vx_ = hit_offset * 9.0f;
            }
        }

        int brick_y_start = 2;
        int check_r = (int)roundf(ball_y_) - brick_y_start;
        int check_c = (int)roundf(ball_x_) / 2;

        if (check_r >= 0 && check_r < kRows && check_c >= 0 && check_c < kCols) {
            if (bricks_[check_r][check_c].hp > 0) {
                bricks_[check_r][check_c].hp--;
                ball_vy_ = -ball_vy_;

                if (bricks_[check_r][check_c].hp == 0) {
                    remaining_bricks_--;
                    score_ += 10;
                    if (score_ > high_score_) {
                        high_score_ = score_;
                        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                    }

                    if (remaining_bricks_ <= 0) {
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        return;
                    }
                } else {
                    bricks_[check_r][check_c].r = 255;
                    bricks_[check_r][check_c].g = 255;
                    bricks_[check_r][check_c].b = 255;
                }
            }
        }

        if (ball_y_ > 15.5f) {
            if (lives_ > 1) {
                lives_--;
                ResetBallAndPaddle();
            } else {
                lives_ = 0;
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                if (score_ > high_score_) {
                    high_score_ = score_;
                    ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                }
            }
        }
    }
}

void Game021Breakout::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, 16 * 16 * 3);

    for (int r = 0; r < kRows; ++r) {
        int y = 2 + r;
        for (int c = 0; c < kCols; ++c) {
            if (bricks_[r][c].hp > 0) {
                int x1 = c * 2;
                int x2 = x1 + 1;
                uint8_t cr = bricks_[r][c].r;
                uint8_t cg = bricks_[r][c].g;
                uint8_t cb = bricks_[r][c].b;

                int idx1 = (y * 16 + x1) * 3;
                int idx2 = (y * 16 + x2) * 3;
                fb_rgb24[idx1 + 0] = cr; fb_rgb24[idx1 + 1] = cg; fb_rgb24[idx1 + 2] = cb;
                fb_rgb24[idx2 + 0] = cr; fb_rgb24[idx2 + 1] = cg; fb_rgb24[idx2 + 2] = cb;
            }
        }
    }

    int px = (int)roundf(paddle_x_);
    int pw = (int)paddle_w_;
    for (int x = px; x < px + pw && x < 16; ++x) {
        if (x >= 0) {
            int idx = (14 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 52;
            fb_rgb24[idx + 1] = 152;
            fb_rgb24[idx + 2] = 219;
        }
    }

    int bx = (int)roundf(ball_x_);
    int by = (int)roundf(ball_y_);
    if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
        int idx = (by * 16 + bx) * 3;
        fb_rgb24[idx + 0] = 255;
        fb_rgb24[idx + 1] = 255;
        fb_rgb24[idx + 2] = 255;
    }

    for (int i = 0; i < lives_ && i < 3; ++i) {
        int idx = (0 * 16 + i * 2) * 3;
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

CartridgeStatus Game021Breakout::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(((kRows * kCols - remaining_bricks_) * 100) / (kRows * kCols));
    return st;
}

} // namespace arcade
