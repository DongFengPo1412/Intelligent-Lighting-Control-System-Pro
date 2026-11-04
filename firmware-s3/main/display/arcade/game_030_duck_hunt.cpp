// game_030_duck_hunt.cpp —— 目标 #030 打鸭子 (Duck Hunt) 核心实现
#include "game_030_duck_hunt.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <math.h>
#include <string.h>

namespace arcade {

static inline void SetPx030(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game030DuckHunt::Game030DuckHunt()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      round_(1),
      duck_index_(0),
      round_hits_(0),
      round_misses_(0),
      shells_(3),
      duck_results_{},
      duck_state_(DUCK_FLYING),
      duck_x_(7.5f),
      duck_y_(12.5f),
      duck_vx_(4.0f),
      duck_vy_(-3.5f),
      escape_timer_(4.5f),
      phase_timer_(0.0f),
      weave_timer_(0.85f),
      reticle_x_(7.5f),
      reticle_y_(6.5f),
      muzzle_flash_(0.0f),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      seed_(0x030D0C84u) {
    SetupNewGame(STATE_TITLE);
}

uint32_t Game030DuckHunt::NextRand() {
    seed_ = seed_ * 1103515245u + 12345u;
    return (seed_ >> 16) & 0x7FFFu;
}

void Game030DuckHunt::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game030DuckHunt::SpawnDuck() {
    shells_ = 3;
    duck_state_ = DUCK_FLYING;
    escape_timer_ = 4.5f;
    phase_timer_ = 0.0f;
    weave_timer_ = 0.85f;

    uint32_t r1 = NextRand();
    uint32_t r2 = NextRand();
    duck_x_ = 3.0f + (float)(r1 % 10);
    duck_y_ = 12.2f;

    float base_spd = 4.2f + (float)(round_ - 1) * 1.15f;
    float dir_sign = ((r2 & 1u) == 0u) ? 1.0f : -1.0f;
    if (duck_x_ > 9.0f) dir_sign = -1.0f;
    else if (duck_x_ < 6.0f) dir_sign = 1.0f;

    duck_vx_ = dir_sign * base_spd * 0.82f;
    duck_vy_ = -base_spd * 0.68f;
}

void Game030DuckHunt::StartRound() {
    duck_index_ = 0;
    round_hits_ = 0;
    round_misses_ = 0;
    for (int i = 0; i < kDucksPerRound; ++i) duck_results_[i] = 0;
    SpawnDuck();
}

void Game030DuckHunt::SetupNewGame(CartridgeState new_state) {
    state_ = new_state;
    score_ = 0;
    round_ = 1;
    reticle_x_ = 7.5f;
    reticle_y_ = 6.5f;
    muzzle_flash_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    seed_ = 0x030D0C84u;
    StartRound();
}

void Game030DuckHunt::Init() {
    Reset();
}

void Game030DuckHunt::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    SetupNewGame(STATE_TITLE);
}

void Game030DuckHunt::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupNewGame(STATE_PLAYING);
    }
}

void Game030DuckHunt::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game030DuckHunt::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game030DuckHunt::FinishCurrentDuck(bool was_hit) {
    if (duck_index_ < kDucksPerRound) {
        duck_results_[duck_index_] = was_hit ? 1 : 2;
    }
    if (was_hit) {
        round_hits_++;
    } else {
        round_misses_++;
    }
    duck_index_++;

    if (duck_index_ >= kDucksPerRound) {
        if (round_hits_ >= kRoundQuota) {
            AddScore(round_hits_ == kDucksPerRound ? 500u : 200u);
            if (round_ >= kTotalRounds) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
            } else {
                round_++;
                StartRound();
            }
        } else {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
        }
    } else {
        SpawnDuck();
    }
}

bool Game030DuckHunt::PullTrigger() {
    if (shells_ == 0 || duck_state_ != DUCK_FLYING) return false;

    shells_--;
    muzzle_flash_ = 0.08f;

    if (fabsf(reticle_x_ - duck_x_) <= 1.4f && fabsf(reticle_y_ - duck_y_) <= 1.4f) {
        duck_state_ = DUCK_STUNNED;
        phase_timer_ = 0.32f;
        AddScore(100u);
        return true;
    }

    if (shells_ == 0) {
        // 3发弹药耗尽未命中 -> 鸭子立刻向上逃离
        duck_state_ = DUCK_ESCAPING;
        duck_vx_ *= 0.3f;
        duck_vy_ = -10.5f;
    }
    return false;
}

void Game030DuckHunt::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt < 0.0f) dt = 0.0f;
    if (dt > 0.05f) dt = 0.05f;

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
        return;
    }

    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        duck_x_ += duck_vx_ * dt * 0.6f;
        duck_y_ += duck_vy_ * dt * 0.6f;
        if (duck_x_ < 1.5f || duck_x_ > 13.5f) duck_vx_ = -duck_vx_;
        if (duck_y_ < 2.0f || duck_y_ > 10.5f) duck_vy_ = -duck_vy_;
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B))) {
            Start();
        }
        return;
    }

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        if (muzzle_flash_ > 0.0f) muzzle_flash_ -= dt;

        // 准星四向移动
        const float aim_speed = 13.5f;
        if (keys_down & KEY_LEFT)  reticle_x_ -= aim_speed * dt;
        if (keys_down & KEY_RIGHT) reticle_x_ += aim_speed * dt;
        if (keys_down & KEY_UP)    reticle_y_ -= aim_speed * dt;
        if (keys_down & KEY_DOWN)  reticle_y_ += aim_speed * dt;

        if (reticle_x_ < 0.0f) reticle_x_ = 0.0f;
        if (reticle_x_ > 15.0f) reticle_x_ = 15.0f;
        if (reticle_y_ < 0.0f) reticle_y_ = 0.0f;
        if (reticle_y_ > 12.0f) reticle_y_ = 12.0f;

        if (keys_pressed & (KEY_A | KEY_B)) {
            PullTrigger();
        }

        // 野鸭状态机更新
        if (duck_state_ == DUCK_FLYING) {
            escape_timer_ -= dt;
            if (escape_timer_ <= 0.0f) {
                duck_state_ = DUCK_ESCAPING;
                duck_vx_ *= 0.3f;
                duck_vy_ = -10.5f;
                return;
            }

            weave_timer_ -= dt;
            if (weave_timer_ <= 0.0f) {
                weave_timer_ = 0.75f;
                uint32_t r = NextRand();
                if ((r & 3u) == 0u) duck_vx_ = -duck_vx_;
                if ((r & 4u) != 0u) duck_vy_ = -duck_vy_;
            }

            duck_x_ += duck_vx_ * dt;
            duck_y_ += duck_vy_ * dt;

            if (duck_x_ <= 1.0f) {
                duck_x_ = 1.0f;
                duck_vx_ = fabsf(duck_vx_);
            } else if (duck_x_ >= 14.0f) {
                duck_x_ = 14.0f;
                duck_vx_ = -fabsf(duck_vx_);
            }

            if (duck_y_ <= 1.2f) {
                duck_y_ = 1.2f;
                duck_vy_ = fabsf(duck_vy_);
            } else if (duck_y_ >= 11.2f) {
                duck_y_ = 11.2f;
                duck_vy_ = -fabsf(duck_vy_);
            }
        } else if (duck_state_ == DUCK_STUNNED) {
            phase_timer_ -= dt;
            if (phase_timer_ <= 0.0f) {
                duck_state_ = DUCK_FALLING;
            }
        } else if (duck_state_ == DUCK_FALLING) {
            duck_y_ += 11.5f * dt;
            if (duck_y_ >= 13.2f) {
                FinishCurrentDuck(true);
            }
        } else if (duck_state_ == DUCK_ESCAPING) {
            duck_x_ += duck_vx_ * dt;
            duck_y_ += duck_vy_ * dt;
            if (duck_y_ < -0.6f) {
                FinishCurrentDuck(false);
            }
        }
    }
}

void Game030DuckHunt::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 1. 晴空或逃逸粉橙色天空 (y=0..12)
    bool escaping_sky = (duck_state_ == DUCK_ESCAPING);
    for (int y = 0; y < 13; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (muzzle_flash_ > 0.0f) {
                SetPx030(fb_rgb24, x, y, 220, 235, 255);
            } else if (escaping_sky) {
                SetPx030(fb_rgb24, x, y, 235, 130, 120);
            } else {
                SetPx030(fb_rgb24, x, y, 64, 168, 245);
            }
        }
    }

    // 2. 草丛地平线 (y=13..15)
    for (int x = 0; x < 16; ++x) {
        bool blade = ((x * 3) % 2 == 0);
        SetPx030(fb_rgb24, x, 13, blade ? 72 : 46, blade ? 215 : 185, 65);
        SetPx030(fb_rgb24, x, 14, 38, 155, 52);
        SetPx030(fb_rgb24, x, 15, 45, 32, 20);
    }

    // 3. 绘制野鸭与振翅色彩动画
    int dx = (int)roundf(duck_x_);
    int dy = (int)roundf(duck_y_);
    if (dy <= 13) {
        if (duck_state_ == DUCK_STUNNED) {
            // 中弹定格惊愕态
            SetPx030(fb_rgb24, dx, dy, 255, 255, 255);
            SetPx030(fb_rgb24, dx - 1, dy, 231, 76, 60);
            SetPx030(fb_rgb24, dx + 1, dy, 241, 196, 15);
        } else if (duck_state_ == DUCK_FALLING) {
            // 旋转下坠态
            bool spin = (((int)(anim_timer_ * 16.0f) & 1) == 0);
            SetPx030(fb_rgb24, dx, dy, 165, 95, 45);
            SetPx030(fb_rgb24, dx, dy - 1, spin ? 39 : 241, spin ? 190 : 196, spin ? 96 : 15);
        } else {
            // 飞行振翅态: 绿头野鸭 + 上下拍翅颜色切换
            int head_dir = (duck_vx_ >= 0.0f) ? 1 : -1;
            bool wing_up = (((int)(anim_timer_ * 10.0f) & 1) == 0);
            SetPx030(fb_rgb24, dx, dy, 165, 95, 45);                        // 栗色鸭身
            SetPx030(fb_rgb24, dx + head_dir, dy, 25, 195, 90);             // 翠绿鸭头
            if (wing_up) {
                SetPx030(fb_rgb24, dx, dy - 1, 245, 245, 250);              // 扬起白羽
            } else {
                SetPx030(fb_rgb24, dx - head_dir, dy + 1, 225, 180, 70);    // 下压金褐翅
            }
        }
    }

    // 4. 绘制准星
    int rx = (int)roundf(reticle_x_);
    int ry = (int)roundf(reticle_y_);
    uint8_t cr = (muzzle_flash_ > 0.0f) ? 255 : 255;
    uint8_t cg = (muzzle_flash_ > 0.0f) ? 255 : 50;
    uint8_t cb = (muzzle_flash_ > 0.0f) ? 255 : 50;
    SetPx030(fb_rgb24, rx - 1, ry, cr, cg, cb);
    SetPx030(fb_rgb24, rx + 1, ry, cr, cg, cb);
    SetPx030(fb_rgb24, rx, ry - 1, cr, cg, cb);
    SetPx030(fb_rgb24, rx, ry + 1, cr, cg, cb);

    // 5. 底部 HUD (y=15): 左侧3发霰弹, 中间6只鸭战果, 右侧轮次
    for (int s = 0; s < (int)shells_ && s < 3; ++s) {
        SetPx030(fb_rgb24, s, 15, 255, 195, 20);
    }
    for (int i = 0; i < kDucksPerRound; ++i) {
        if (duck_results_[i] == 1) {
            SetPx030(fb_rgb24, 5 + i, 15, 46, 230, 90);
        } else if (duck_results_[i] == 2) {
            SetPx030(fb_rgb24, 5 + i, 15, 235, 60, 50);
        } else {
            SetPx030(fb_rgb24, 5 + i, 15, 180, 180, 190);
        }
    }
    for (int r = 0; r < (int)round_ && r < 3; ++r) {
        SetPx030(fb_rgb24, 15 - r, 15, 0, 225, 255);
    }

    if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) SetPx030(fb_rgb24, x, 0, 231, 76, 60);
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx030(fb_rgb24, 6, y, 250, 250, 250);
            SetPx030(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game030DuckHunt::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    int margin = (kDucksPerRound - kRoundQuota + 1) - (int)round_misses_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : (uint8_t)(margin > 0 ? margin : 1);
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((state_ == STATE_VICTORY) ? 100 : (((round_ - 1) * kDucksPerRound + duck_index_) * 100 / (kTotalRounds * kDucksPerRound)));
    return st;
}

static_assert(sizeof(Game030DuckHunt) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
