// game_022_pinball.cpp —— 目标 #022 迷你弹珠台 (Mini Pinball) 核心实现
#include "game_022_pinball.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const float kPinballGravity = 16.5f;
static const float kMaxBallSpeed = 16.5f;

static inline void SetPixel22(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game022Pinball::Game022Pinball()
    : state_(STATE_TITLE),
      ball_x_(11.5f),
      ball_y_(2.5f),
      ball_vx_(-4.2f),
      ball_vy_(1.5f),
      left_flipper_up_(false),
      right_flipper_up_(false),
      left_swing_timer_(0.0f),
      right_swing_timer_(0.0f),
      sling_flash_l_(0.0f),
      sling_flash_r_(0.0f),
      bumpers_{},
      balls_left_(3),
      score_(0),
      high_score_(0),
      rng_seed_(0x22197901u),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
}

uint32_t Game022Pinball::NextRand() {
    rng_seed_ = rng_seed_ * 1103515245u + 12345u;
    return (rng_seed_ >> 16) & 0x7FFFu;
}

void Game022Pinball::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game022Pinball::InitBumpers() {
    bumpers_[0] = {4.5f, 4.5f, 25u, 0.0f};
    bumpers_[1] = {10.5f, 4.5f, 25u, 0.0f};
    bumpers_[2] = {7.5f, 7.2f, 50u, 0.0f};
}

void Game022Pinball::SpawnBall() {
    float jitter = ((float)(NextRand() % 21) - 10.0f) * 0.08f;
    ball_x_ = 11.5f;
    ball_y_ = 2.2f;
    ball_vx_ = -4.5f + jitter;
    ball_vy_ = 1.2f;
}

void Game022Pinball::Init() {
    Reset();
}

void Game022Pinball::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    left_flipper_up_ = false;
    right_flipper_up_ = false;
    left_swing_timer_ = 0.0f;
    right_swing_timer_ = 0.0f;
    sling_flash_l_ = 0.0f;
    sling_flash_r_ = 0.0f;
    balls_left_ = 3;
    score_ = 0;
    rng_seed_ = 0x22197901u;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    InitBumpers();
    SpawnBall();
}

void Game022Pinball::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        left_flipper_up_ = false;
        right_flipper_up_ = false;
        left_swing_timer_ = 0.0f;
        right_swing_timer_ = 0.0f;
        sling_flash_l_ = 0.0f;
        sling_flash_r_ = 0.0f;
        balls_left_ = 3;
        score_ = 0;
        rng_seed_ = 0x22197901u;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        InitBumpers();
        SpawnBall();
    }
}

void Game022Pinball::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game022Pinball::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game022Pinball::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt < 0.0f) dt = 0.0f;
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        ball_x_ = 7.5f + cosf(anim_timer_ * 2.8f) * 3.5f;
        ball_y_ = 6.0f + sinf(anim_timer_ * 3.6f) * 2.5f;
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
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

        // 左右独立挡板输入映射
        left_flipper_up_ = (keys_down & (KEY_A | KEY_LEFT)) != 0;
        right_flipper_up_ = (keys_down & (KEY_B | KEY_RIGHT)) != 0;

        if (keys_pressed & (KEY_A | KEY_LEFT)) {
            left_swing_timer_ = 0.22f;
        } else if (left_swing_timer_ > 0.0f) {
            left_swing_timer_ -= dt;
            if (left_swing_timer_ < 0.0f) left_swing_timer_ = 0.0f;
        }

        if (keys_pressed & (KEY_B | KEY_RIGHT)) {
            right_swing_timer_ = 0.22f;
        } else if (right_swing_timer_ > 0.0f) {
            right_swing_timer_ -= dt;
            if (right_swing_timer_ < 0.0f) right_swing_timer_ = 0.0f;
        }

        if (sling_flash_l_ > 0.0f) sling_flash_l_ = fmaxf(0.0f, sling_flash_l_ - dt);
        if (sling_flash_r_ > 0.0f) sling_flash_r_ = fmaxf(0.0f, sling_flash_r_ - dt);
        for (int i = 0; i < kNumBumpers; ++i) {
            if (bumpers_[i].flash_timer > 0.0f) {
                bumpers_[i].flash_timer = fmaxf(0.0f, bumpers_[i].flash_timer - dt);
            }
        }

        // 重力与弹珠积分
        ball_vy_ += kPinballGravity * dt;
        ball_x_ += ball_vx_ * dt;
        ball_y_ += ball_vy_ * dt;

        // 外框金属边界反弹
        if (ball_x_ < 1.2f) {
            ball_x_ = 1.2f;
            ball_vx_ = fabsf(ball_vx_) * 0.85f;
            if (ball_vx_ < 1.5f) ball_vx_ = 1.5f;
        } else if (ball_x_ > 13.8f) {
            ball_x_ = 13.8f;
            ball_vx_ = -fabsf(ball_vx_) * 0.85f;
            if (ball_vx_ > -1.5f) ball_vx_ = -1.5f;
        }
        if (ball_y_ < 1.2f) {
            ball_y_ = 1.2f;
            ball_vy_ = fabsf(ball_vy_) * 0.85f;
        }

        // 侧翼弹弓 (Slingshots) 与导轨: y in [10.5..12.8]
        if (ball_y_ >= 10.5f && ball_y_ <= 12.8f) {
            if (ball_x_ <= 2.6f) {
                ball_x_ = 2.8f;
                ball_vx_ = 6.8f;
                ball_vy_ = -8.5f;
                sling_flash_l_ = 0.20f;
                AddScore(15);
            } else if (ball_x_ >= 12.4f) {
                ball_x_ = 12.2f;
                ball_vx_ = -6.8f;
                ball_vy_ = -8.5f;
                sling_flash_r_ = 0.20f;
                AddScore(15);
            }
        }

        // 发光蘑菇头弹射器碰撞 (+25 / +50)
        for (int i = 0; i < kNumBumpers; ++i) {
            float dx = ball_x_ - bumpers_[i].x;
            float dy = ball_y_ - bumpers_[i].y;
            float dist_sq = dx * dx + dy * dy;
            if (dist_sq < 1.45f * 1.45f) {
                float dist = sqrtf(dist_sq);
                float nx = (dist > 0.01f) ? (dx / dist) : 0.0f;
                float ny = (dist > 0.01f) ? (dy / dist) : -1.0f;
                ball_x_ = bumpers_[i].x + nx * 1.50f;
                ball_y_ = bumpers_[i].y + ny * 1.50f;
                ball_vx_ = nx * 10.5f;
                ball_vy_ = ny * 10.5f;
                bumpers_[i].flash_timer = 0.22f;
                AddScore(bumpers_[i].points);
            }
        }

        // 左挡板碰撞区: x in [2.6 .. 6.8], y in [12.8 .. 14.6]
        if (ball_y_ >= 12.8f && ball_y_ <= 14.6f && ball_x_ >= 2.6f && ball_x_ <= 6.8f && ball_vy_ > -1.0f) {
            if (left_flipper_up_ || left_swing_timer_ > 0.0f) {
                ball_y_ = 12.6f;
                ball_vy_ = (left_swing_timer_ > 0.0f) ? -14.2f : -11.5f;
                ball_vx_ = 2.0f + (ball_x_ - 3.0f) * 2.2f;
                AddScore(10);
            } else if (ball_vy_ > 0.0f) {
                ball_y_ = 12.8f;
                ball_vy_ = -fabsf(ball_vy_) * 0.35f;
                ball_vx_ += 1.8f;
            }
        }

        // 右挡板碰撞区: x in [8.2 .. 12.4], y in [12.8 .. 14.6]
        if (ball_y_ >= 12.8f && ball_y_ <= 14.6f && ball_x_ >= 8.2f && ball_x_ <= 12.4f && ball_vy_ > -1.0f) {
            if (right_flipper_up_ || right_swing_timer_ > 0.0f) {
                ball_y_ = 12.6f;
                ball_vy_ = (right_swing_timer_ > 0.0f) ? -14.2f : -11.5f;
                ball_vx_ = -2.0f - (12.0f - ball_x_) * 2.2f;
                AddScore(10);
            } else if (ball_vy_ > 0.0f) {
                ball_y_ = 12.8f;
                ball_vy_ = -fabsf(ball_vy_) * 0.35f;
                ball_vx_ -= 1.8f;
            }
        }

        // 限速保护
        float spd = sqrtf(ball_vx_ * ball_vx_ + ball_vy_ * ball_vy_);
        if (spd > kMaxBallSpeed) {
            float sc = kMaxBallSpeed / spd;
            ball_vx_ *= sc;
            ball_vy_ *= sc;
        }

        // 底部漏球口检测 (y >= 16.0)
        if (ball_y_ >= 16.0f) {
            if (balls_left_ > 1) {
                balls_left_--;
                SpawnBall();
            } else {
                balls_left_ = 0;
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game022Pinball::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 霓虹深蓝桌面与银色边框
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15 || y == 0) {
                SetPixel22(fb_rgb24, x, y, 150, 160, 190);
            } else {
                SetPixel22(fb_rgb24, x, y, 10, 14, 36);
            }
        }
    }
    // 底部中央漏球深渊 (x=7..8, y=15)
    SetPixel22(fb_rgb24, 7, 15, 0, 0, 0);
    SetPixel22(fb_rgb24, 8, 15, 0, 0, 0);

    // 绘制侧翼弹弓 (Slingshots)
    uint8_t sl_r = (sling_flash_l_ > 0.0f) ? 255 : 180;
    uint8_t sl_g = (sling_flash_l_ > 0.0f) ? 255 : 60;
    uint8_t sl_b = (sling_flash_l_ > 0.0f) ? 120 : 210;
    SetPixel22(fb_rgb24, 1, 11, sl_r, sl_g, sl_b);
    SetPixel22(fb_rgb24, 2, 12, sl_r, sl_g, sl_b);

    uint8_t sr_r = (sling_flash_r_ > 0.0f) ? 255 : 180;
    uint8_t sr_g = (sling_flash_r_ > 0.0f) ? 255 : 60;
    uint8_t sr_b = (sling_flash_r_ > 0.0f) ? 120 : 210;
    SetPixel22(fb_rgb24, 14, 11, sr_r, sr_g, sr_b);
    SetPixel22(fb_rgb24, 13, 12, sr_r, sr_g, sr_b);

    // 绘制 3 颗弹射蘑菇头
    for (int i = 0; i < kNumBumpers; ++i) {
        int bx = (int)roundf(bumpers_[i].x);
        int by = (int)roundf(bumpers_[i].y);
        bool lit = (bumpers_[i].flash_timer > 0.0f);
        if (lit) {
            SetPixel22(fb_rgb24, bx, by, 255, 255, 255);
            SetPixel22(fb_rgb24, bx - 1, by, 255, 230, 40);
            SetPixel22(fb_rgb24, bx + 1, by, 255, 230, 40);
            SetPixel22(fb_rgb24, bx, by - 1, 255, 230, 40);
            SetPixel22(fb_rgb24, bx, by + 1, 255, 230, 40);
        } else if (bumpers_[i].points >= 50) {
            SetPixel22(fb_rgb24, bx, by, 255, 190, 20);
            SetPixel22(fb_rgb24, bx - 1, by, 210, 90, 20);
            SetPixel22(fb_rgb24, bx + 1, by, 210, 90, 20);
            SetPixel22(fb_rgb24, bx, by - 1, 210, 90, 20);
            SetPixel22(fb_rgb24, bx, by + 1, 210, 90, 20);
        } else {
            SetPixel22(fb_rgb24, bx, by, 245, 50, 75);
            SetPixel22(fb_rgb24, bx - 1, by, 160, 25, 45);
            SetPixel22(fb_rgb24, bx + 1, by, 160, 25, 45);
            SetPixel22(fb_rgb24, bx, by - 1, 160, 25, 45);
            SetPixel22(fb_rgb24, bx, by + 1, 160, 25, 45);
        }
    }

    // 绘制左挡板 (x=3..6) 与右挡板 (x=9..12)
    SetPixel22(fb_rgb24, 3, 13, 0, 220, 255);
    SetPixel22(fb_rgb24, 4, left_flipper_up_ ? 13 : 13, 0, 220, 255);
    SetPixel22(fb_rgb24, 5, left_flipper_up_ ? 12 : 14, 80, 245, 255);
    SetPixel22(fb_rgb24, 6, left_flipper_up_ ? 12 : 14, 200, 255, 255);

    SetPixel22(fb_rgb24, 12, 13, 255, 140, 25);
    SetPixel22(fb_rgb24, 11, right_flipper_up_ ? 13 : 13, 255, 140, 25);
    SetPixel22(fb_rgb24, 10, right_flipper_up_ ? 12 : 14, 255, 195, 50);
    SetPixel22(fb_rgb24, 9, right_flipper_up_ ? 12 : 14, 255, 245, 160);

    // 绘制银色钢珠
    if (state_ != STATE_GAMEOVER) {
        int px = (int)roundf(ball_x_);
        int py = (int)roundf(ball_y_);
        SetPixel22(fb_rgb24, px, py, 255, 255, 255);
    }

    // 顶部剩余球数指示
    for (int b = 0; b < (int)balls_left_ && b < 3; ++b) {
        SetPixel22(fb_rgb24, 1 + b * 2, 0, 255, 215, 30);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPixel22(fb_rgb24, 6, y, 250, 250, 250);
            SetPixel22(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game022Pinball::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = balls_left_;
    st.state = (uint8_t)state_;
    uint32_t prog = score_ / 10u;
    if (prog > 100u) prog = 100u;
    st.progress = (uint8_t)prog;
    return st;
}

static_assert(sizeof(Game022Pinball) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
