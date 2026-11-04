// game_014_orbit_hop.cpp —— 目标 #014 轨道跃迁 (Orbit Hop) 核心实现
#include "game_014_orbit_hop.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const float kCenterX = 7.5f;
static const float kCenterY = 7.5f;
static const float kOrbitRadii[3] = {2.8f, 4.8f, 6.8f};
static const float kTwoPi = 6.2831853f;

static inline void SetPixel14(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game014OrbitHop::Game014OrbitHop()
    : state_(STATE_TITLE),
      orbit_idx_(1),
      hop_dir_(1),
      player_angle_(0.0f),
      hop_flash_timer_(0.0f),
      stars_{},
      mines_{},
      stars_remaining_(0),
      waves_cleared_(0),
      score_(0),
      high_score_(0),
      rng_seed_(0x14201601u),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
}

uint32_t Game014OrbitHop::NextRand() {
    rng_seed_ = rng_seed_ * 1103515245u + 12345u;
    return (rng_seed_ >> 16) & 0x7FFFu;
}

void Game014OrbitHop::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game014OrbitHop::SpawnWave() {
    stars_remaining_ = kMaxStars;
    for (int i = 0; i < kMaxStars; ++i) {
        int orb = i % kNumOrbits;
        float base_a = (float)(i / kNumOrbits) * 3.1415926f + (float)(NextRand() % 100) * 0.025f + 0.8f;
        while (base_a >= kTwoPi) base_a -= kTwoPi;
        stars_[i].orbit = orb;
        stars_[i].angle = base_a;
        stars_[i].active = true;
    }

    int active_mines = (waves_cleared_ >= 2) ? 4 : 3;
    for (int i = 0; i < kMaxMines; ++i) {
        if (i < active_mines) {
            mines_[i].orbit = i % kNumOrbits;
            // 生成在远离玩家当前角度的安全半圆区域 (相差约 pi 弧度)
            float offset = 2.4f + (float)(NextRand() % 150) * 0.01f;
            float ma = player_angle_ + offset;
            while (ma >= kTwoPi) ma -= kTwoPi;
            mines_[i].angle = ma;
            mines_[i].speed = 1.15f + (float)(i % 3) * 0.18f + (float)waves_cleared_ * 0.08f;
            mines_[i].active = true;
        } else {
            mines_[i].orbit = 0;
            mines_[i].angle = 0.0f;
            mines_[i].speed = 0.0f;
            mines_[i].active = false;
        }
    }
}

void Game014OrbitHop::Init() {
    Reset();
}

void Game014OrbitHop::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    orbit_idx_ = 1;
    hop_dir_ = 1;
    player_angle_ = 0.0f;
    hop_flash_timer_ = 0.0f;
    stars_remaining_ = 0;
    waves_cleared_ = 0;
    score_ = 0;
    rng_seed_ = 0x14201601u;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    SpawnWave();
}

void Game014OrbitHop::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        orbit_idx_ = 1;
        hop_dir_ = 1;
        player_angle_ = 0.0f;
        hop_flash_timer_ = 0.0f;
        waves_cleared_ = 0;
        score_ = 0;
        rng_seed_ = 0x14201601u;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        SpawnWave();
    }
}

void Game014OrbitHop::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game014OrbitHop::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game014OrbitHop::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt < 0.0f) dt = 0.0f;
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        player_angle_ += 1.6f * dt;
        if (player_angle_ >= kTwoPi) player_angle_ -= kTwoPi;
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

        const uint16_t tap_mask = KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT | KEY_SELECT;
        if (keys_pressed & tap_mask) {
            if (orbit_idx_ == 0) {
                orbit_idx_ = 1;
                hop_dir_ = 1;
            } else if (orbit_idx_ == 2) {
                orbit_idx_ = 1;
                hop_dir_ = -1;
            } else {
                orbit_idx_ += hop_dir_;
                if (orbit_idx_ >= 2) hop_dir_ = -1;
                if (orbit_idx_ <= 0) hop_dir_ = 1;
            }
            hop_flash_timer_ = 0.16f;
        }

        if (hop_flash_timer_ > 0.0f) {
            hop_flash_timer_ -= dt;
            if (hop_flash_timer_ < 0.0f) hop_flash_timer_ = 0.0f;
        }

        float player_omega = 1.95f + (float)waves_cleared_ * 0.12f;
        player_angle_ += player_omega * dt;
        while (player_angle_ >= kTwoPi) player_angle_ -= kTwoPi;

        for (int i = 0; i < kMaxMines; ++i) {
            if (!mines_[i].active) continue;
            mines_[i].angle -= mines_[i].speed * dt;
            while (mines_[i].angle < 0.0f) mines_[i].angle += kTwoPi;
        }

        float r = kOrbitRadii[orbit_idx_];
        float px = kCenterX + cosf(player_angle_) * r;
        float py = kCenterY + sinf(player_angle_) * r;

        // 逆向红雷碰撞判定
        for (int i = 0; i < kMaxMines; ++i) {
            if (!mines_[i].active || mines_[i].orbit != orbit_idx_) continue;
            float mr = kOrbitRadii[mines_[i].orbit];
            float mx = kCenterX + cosf(mines_[i].angle) * mr;
            float my = kCenterY + sinf(mines_[i].angle) * mr;
            float dx = px - mx;
            float dy = py - my;
            if (dx * dx + dy * dy < 0.90f) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            }
        }

        // 轨道金星收集判定
        for (int i = 0; i < kMaxStars; ++i) {
            if (!stars_[i].active || stars_[i].orbit != orbit_idx_) continue;
            float sr = kOrbitRadii[stars_[i].orbit];
            float sx = kCenterX + cosf(stars_[i].angle) * sr;
            float sy = kCenterY + sinf(stars_[i].angle) * sr;
            float dx = px - sx;
            float dy = py - sy;
            if (dx * dx + dy * dy < 1.35f) {
                stars_[i].active = false;
                stars_remaining_--;
                AddScore(20);
                if (stars_remaining_ <= 0) {
                    AddScore(50);
                    waves_cleared_++;
                    if (waves_cleared_ >= kTargetWaves) {
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        return;
                    }
                    SpawnWave();
                    break;
                }
            }
        }
    }
}

void Game014OrbitHop::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 深空背景
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPixel14(fb_rgb24, x, y, 6, 8, 20);
        }
    }

    // 绘制三层同心环轨道 (r = 2.8, 4.8, 6.8)
    for (int orb = 0; orb < kNumOrbits; ++orb) {
        float rad = kOrbitRadii[orb];
        bool is_cur = (orb == orbit_idx_);
        uint8_t rr = is_cur ? 35 : 18;
        uint8_t rg = is_cur ? 65 : 32;
        uint8_t rb = is_cur ? 115 : 62;
        for (int step = 0; step < 48; ++step) {
            float a = (float)step * (kTwoPi / 48.0f);
            int ox = (int)roundf(kCenterX + cosf(a) * rad);
            int oy = (int)roundf(kCenterY + sinf(a) * rad);
            SetPixel14(fb_rgb24, ox, oy, rr, rg, rb);
        }
    }

    // 中心恒星核心
    SetPixel14(fb_rgb24, 7, 7, 255, 180, 40);
    SetPixel14(fb_rgb24, 8, 7, 255, 140, 30);
    SetPixel14(fb_rgb24, 7, 8, 255, 140, 30);
    SetPixel14(fb_rgb24, 8, 8, 255, 180, 40);

    // 绘制金星
    for (int i = 0; i < kMaxStars; ++i) {
        if (!stars_[i].active) continue;
        float sr = kOrbitRadii[stars_[i].orbit];
        int sx = (int)roundf(kCenterX + cosf(stars_[i].angle) * sr);
        int sy = (int)roundf(kCenterY + sinf(stars_[i].angle) * sr);
        SetPixel14(fb_rgb24, sx, sy, 255, 220, 30);
    }

    // 绘制逆向红雷
    for (int i = 0; i < kMaxMines; ++i) {
        if (!mines_[i].active) continue;
        float mr = kOrbitRadii[mines_[i].orbit];
        int mx = (int)roundf(kCenterX + cosf(mines_[i].angle) * mr);
        int my = (int)roundf(kCenterY + sinf(mines_[i].angle) * mr);
        SetPixel14(fb_rgb24, mx, my, 245, 40, 55);
    }

    // 绘制主角能量球
    float pr = kOrbitRadii[orbit_idx_];
    int px = (int)roundf(kCenterX + cosf(player_angle_) * pr);
    int py = (int)roundf(kCenterY + sinf(player_angle_) * pr);
    if (state_ == STATE_GAMEOVER) {
        SetPixel14(fb_rgb24, px, py, 255, 80, 30);
    } else if (hop_flash_timer_ > 0.0f) {
        SetPixel14(fb_rgb24, px, py, 255, 255, 255);
    } else {
        SetPixel14(fb_rgb24, px, py, 0, 245, 255);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPixel14(fb_rgb24, 6, y, 250, 250, 250);
            SetPixel14(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game014OrbitHop::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    int prog = (waves_cleared_ * 100) / kTargetWaves;
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

static_assert(sizeof(Game014OrbitHop) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
