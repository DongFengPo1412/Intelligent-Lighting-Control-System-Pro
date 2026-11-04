// game_018_red_green_light.cpp —— 目标 #018 红灯绿灯 (Red Light Green) 核心实现
#include "game_018_red_green_light.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const float kYellowDuration = 0.55f;
static const float kRedGraceTime = 0.08f;
static const float kFinishLineY = 3.0f;
static const float kStartLineY = 15.0f;
static const float kRoundTimeLimit = 18.0f;

static inline void SetPixel18(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game018RedGreenLight::Game018RedGreenLight()
    : state_(STATE_TITLE),
      signal_(SIGNAL_GREEN),
      signal_timer_(1.5f),
      red_elapsed_(0.0f),
      player_x_(7.5f),
      player_y_(kStartLineY),
      round_(1),
      round_timer_(kRoundTimeLimit),
      laser_eliminated_(false),
      score_(0),
      high_score_(0),
      rng_seed_(0x18202101u),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
}

uint32_t Game018RedGreenLight::NextRand() {
    rng_seed_ = rng_seed_ * 1103515245u + 12345u;
    return (rng_seed_ >> 16) & 0x7FFFu;
}

void Game018RedGreenLight::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

float Game018RedGreenLight::NextGreenDuration() {
    float base = 1.55f - (float)(round_ - 1) * 0.22f;
    if (base < 0.85f) base = 0.85f;
    return base + (float)(NextRand() % 5) * 0.10f;
}

float Game018RedGreenLight::NextRedDuration() {
    return 1.05f + (float)(NextRand() % 5) * 0.12f;
}

void Game018RedGreenLight::StartRound(int round_num) {
    round_ = round_num;
    player_x_ = 7.5f;
    player_y_ = kStartLineY;
    round_timer_ = kRoundTimeLimit;
    signal_ = SIGNAL_GREEN;
    signal_timer_ = NextGreenDuration();
    red_elapsed_ = 0.0f;
    laser_eliminated_ = false;
}

void Game018RedGreenLight::Init() {
    Reset();
}

void Game018RedGreenLight::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    rng_seed_ = 0x18202101u;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    StartRound(1);
}

void Game018RedGreenLight::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        rng_seed_ = 0x18202101u;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        StartRound(1);
    }
}

void Game018RedGreenLight::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game018RedGreenLight::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game018RedGreenLight::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt < 0.0f) dt = 0.0f;
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        int cyc = ((int)(anim_timer_ * 1.5f)) % 3;
        signal_ = (TrafficSignalPhase)cyc;
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP))) {
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

        round_timer_ -= dt;
        if (round_timer_ <= 0.0f) {
            round_timer_ = 0.0f;
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            return;
        }

        // 更新交通信号灯状态机: GREEN -> YELLOW(0.55s) -> RED -> GREEN
        signal_timer_ -= dt;
        if (signal_ == SIGNAL_RED) {
            red_elapsed_ += dt;
        }
        if (signal_timer_ <= 0.0f) {
            if (signal_ == SIGNAL_GREEN) {
                signal_ = SIGNAL_YELLOW;
                signal_timer_ = kYellowDuration;
            } else if (signal_ == SIGNAL_YELLOW) {
                signal_ = SIGNAL_RED;
                signal_timer_ = NextRedDuration();
                red_elapsed_ = 0.0f;
            } else {
                signal_ = SIGNAL_GREEN;
                signal_timer_ = NextGreenDuration();
                red_elapsed_ = 0.0f;
            }
        }

        const uint16_t move_mask = KEY_A | KEY_UP;
        bool moving = (keys_down & move_mask) != 0;

        if (signal_ == SIGNAL_RED && red_elapsed_ > kRedGraceTime && moving) {
            laser_eliminated_ = true;
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            return;
        }

        if (moving) {
            float run_speed = 4.6f + (float)(round_ - 1) * 0.7f;
            player_y_ -= run_speed * dt;
            if (player_y_ <= kFinishLineY) {
                player_y_ = kFinishLineY;
                uint32_t time_bonus = (uint32_t)(round_timer_ * 5.0f);
                AddScore(100u + time_bonus);
                if (round_ >= kTotalRounds) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    return;
                }
                StartRound(round_ + 1);
            }
        }
    }
}

void Game018RedGreenLight::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 赛场沙地背景 (y=4..15)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (y <= 2) {
                SetPixel18(fb_rgb24, x, y, 16, 18, 28);
            } else if (y == 3) {
                // 终点黑白金格线
                bool alt = ((x % 2) == 0);
                SetPixel18(fb_rgb24, x, y, alt ? 255 : 40, alt ? 215 : 40, alt ? 40 : 50);
            } else {
                uint8_t shade = (uint8_t)(((x + y) % 2 == 0) ? 0 : 8);
                SetPixel18(fb_rgb24, x, y, (uint8_t)(138 + shade), (uint8_t)(106 + shade), 62);
            }
        }
    }

    // 顶部信号灯巨幕 (x=0..10, y=0..1)
    uint8_t sr = 30, sg = 230, sb = 85;
    if (signal_ == SIGNAL_YELLOW) {
        bool blink_on = (((int)(anim_timer_ * 14.0f)) % 2) == 0;
        sr = blink_on ? 255 : 110;
        sg = blink_on ? 205 : 85;
        sb = 15;
    } else if (signal_ == SIGNAL_RED) {
        sr = 245; sg = 30; sb = 35;
    }
    for (int y = 0; y <= 1; ++y) {
        for (int x = 0; x <= 10; ++x) {
            SetPixel18(fb_rgb24, x, y, sr, sg, sb);
        }
    }

    // 右上监察木偶 (x=12..14, y=0..2)
    for (int y = 0; y <= 2; ++y) {
        for (int x = 12; x <= 14; ++x) {
            if (y == 0) {
                SetPixel18(fb_rgb24, x, y, 60, 40, 25);
            } else if (y == 1) {
                if (signal_ == SIGNAL_RED && (x == 12 || x == 14)) {
                    SetPixel18(fb_rgb24, x, y, 255, 25, 25); // 红眼锁定
                } else {
                    SetPixel18(fb_rgb24, x, y, 235, 190, 145);
                }
            } else {
                SetPixel18(fb_rgb24, x, y, 240, 130, 30);
            }
        }
    }

    // 轮次指示点 (y=2, x=0..2)
    for (int r = 0; r < round_ && r < kTotalRounds; ++r) {
        SetPixel18(fb_rgb24, r * 2, 2, 0, 230, 255);
    }

    // 激光淘汰射线
    int px = (int)roundf(player_x_);
    int py = (int)roundf(player_y_);
    if (laser_eliminated_ && state_ == STATE_GAMEOVER) {
        for (int s = 0; s <= 12; ++s) {
            float t = (float)s / 12.0f;
            int lx = (int)roundf(13.0f + (player_x_ - 13.0f) * t);
            int ly = (int)roundf(1.0f + (player_y_ - 1.0f) * t);
            SetPixel18(fb_rgb24, lx, ly, 255, 40, 80);
        }
    }

    // 绘制奔跑参赛者 (青绿运动服 456)
    if (state_ == STATE_GAMEOVER && laser_eliminated_) {
        SetPixel18(fb_rgb24, px, py, 255, 80, 20);
        SetPixel18(fb_rgb24, px + 1, py, 255, 200, 40);
    } else {
        SetPixel18(fb_rgb24, px, py - 1, 245, 205, 165);
        SetPixel18(fb_rgb24, px, py, 25, 195, 145);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPixel18(fb_rgb24, 6, y, 250, 250, 250);
            SetPixel18(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game018RedGreenLight::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    float round_frac = (kStartLineY - player_y_) / (kStartLineY - kFinishLineY);
    if (round_frac < 0.0f) round_frac = 0.0f;
    if (round_frac > 1.0f) round_frac = 1.0f;
    int prog = (state_ == STATE_VICTORY)
                   ? 100
                   : (int)((((float)(round_ - 1) + round_frac) / (float)kTotalRounds) * 100.0f);
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

static_assert(sizeof(Game018RedGreenLight) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
