// game_016_whack_a_mole.cpp —— 目标 #016 打地鼠 (Whack-A-Mole) 核心实现
#include "game_016_whack_a_mole.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const int kHoleX[3] = {3, 8, 13};
static const int kHoleY[3] = {4, 9, 14};
static const float kRoundDuration = 45.0f;

static inline void SetPixel16(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game016WhackAMole::Game016WhackAMole()
    : state_(STATE_TITLE),
      holes_{},
      cursor_row_(1),
      cursor_col_(1),
      hammer_timer_(0.0f),
      lives_(3),
      time_remaining_(kRoundDuration),
      spawn_cooldown_(0.45f),
      spawn_count_(0),
      score_(0),
      high_score_(0),
      rng_seed_(0x16197601u),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
}

uint32_t Game016WhackAMole::NextRand() {
    rng_seed_ = rng_seed_ * 1103515245u + 12345u;
    return (rng_seed_ >> 16) & 0x7FFFu;
}

void Game016WhackAMole::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game016WhackAMole::InitHoles() {
    for (int i = 0; i < kTotalHoles; ++i) {
        holes_[i].popped = false;
        holes_[i].whacked = false;
        holes_[i].kind = WHACK_MOLE_NORMAL;
        holes_[i].pop_timer = 0.0f;
    }
}

void Game016WhackAMole::SpawnMole(bool force_normal) {
    int pick = (int)(NextRand() % kTotalHoles);
    for (int t = 0; t < kTotalHoles; ++t) {
        int idx = (pick + t) % kTotalHoles;
        if (!holes_[idx].popped) {
            holes_[idx].popped = true;
            holes_[idx].whacked = false;
            holes_[idx].pop_timer = 1.15f + (float)(NextRand() % 5) * 0.10f;
            if (force_normal || spawn_count_ == 0 || (NextRand() % 100) < 74) {
                holes_[idx].kind = WHACK_MOLE_NORMAL;
            } else {
                holes_[idx].kind = WHACK_MOLE_BOMB;
            }
            spawn_count_++;
            break;
        }
    }
}

void Game016WhackAMole::StrikeHammer() {
    hammer_timer_ = 0.16f;
    int idx = cursor_row_ * 3 + cursor_col_;
    if (holes_[idx].popped && !holes_[idx].whacked) {
        holes_[idx].whacked = true;
        holes_[idx].pop_timer = 0.14f;
        if (holes_[idx].kind == WHACK_MOLE_NORMAL) {
            AddScore(10);
        } else {
            if (lives_ > 1) {
                lives_--;
            } else {
                lives_ = 0;
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
            }
        }
    }
}

void Game016WhackAMole::Init() {
    Reset();
}

void Game016WhackAMole::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    cursor_row_ = 1;
    cursor_col_ = 1;
    hammer_timer_ = 0.0f;
    lives_ = 3;
    time_remaining_ = kRoundDuration;
    spawn_cooldown_ = 0.35f;
    spawn_count_ = 0;
    score_ = 0;
    rng_seed_ = 0x16197601u;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    InitHoles();
    SpawnMole(true);
}

void Game016WhackAMole::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        cursor_row_ = 1;
        cursor_col_ = 1;
        hammer_timer_ = 0.0f;
        lives_ = 3;
        time_remaining_ = kRoundDuration;
        spawn_cooldown_ = 0.55f;
        spawn_count_ = 0;
        score_ = 0;
        rng_seed_ = 0x16197601u;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        InitHoles();
        SpawnMole(true);
    }
}

void Game016WhackAMole::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game016WhackAMole::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game016WhackAMole::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt < 0.0f) dt = 0.0f;
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT))) {
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

        if (keys_pressed & KEY_UP) {
            if (cursor_row_ > 0) cursor_row_--;
        }
        if (keys_pressed & KEY_DOWN) {
            if (cursor_row_ < 2) cursor_row_++;
        }
        if (keys_pressed & KEY_LEFT) {
            if (cursor_col_ > 0) cursor_col_--;
        }
        if (keys_pressed & KEY_RIGHT) {
            if (cursor_col_ < 2) cursor_col_++;
        }

        if (hammer_timer_ > 0.0f) {
            hammer_timer_ -= dt;
            if (hammer_timer_ < 0.0f) hammer_timer_ = 0.0f;
        }
        if (keys_pressed & (KEY_A | KEY_B)) {
            StrikeHammer();
            if (state_ != STATE_PLAYING) return;
        }

        for (int i = 0; i < kTotalHoles; ++i) {
            if (!holes_[i].popped) continue;
            holes_[i].pop_timer -= dt;
            if (holes_[i].pop_timer <= 0.0f) {
                bool missed_normal = (!holes_[i].whacked && holes_[i].kind == WHACK_MOLE_NORMAL);
                holes_[i].popped = false;
                holes_[i].whacked = false;
                if (missed_normal) {
                    // 漏打地鼠扣除剩余时间
                    time_remaining_ -= 2.5f;
                }
            }
        }

        spawn_cooldown_ -= dt;
        if (spawn_cooldown_ <= 0.0f) {
            spawn_cooldown_ = 0.60f + (float)(NextRand() % 4) * 0.08f;
            SpawnMole(false);
        }

        time_remaining_ -= dt;
        if (time_remaining_ <= 0.0f) {
            time_remaining_ = 0.0f;
            if (score_ >= kTargetScore) {
                state_ = STATE_VICTORY;
            } else {
                state_ = STATE_GAMEOVER;
            }
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game016WhackAMole::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 草坪背景
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPixel16(fb_rgb24, x, y, 22, 56, 26);
        }
    }

    // 3x3 地洞与地鼠
    for (int r = 0; r < 3; ++r) {
        for (int c = 0; c < 3; ++c) {
            int cx = kHoleX[c];
            int cy = kHoleY[r];
            int idx = r * 3 + c;

            for (int dy = -1; dy <= 0; ++dy) {
                for (int dx = -1; dx <= 0; ++dx) {
                    SetPixel16(fb_rgb24, cx + dx, cy + dy, 40, 26, 16);
                }
            }

            if (holes_[idx].popped) {
                if (holes_[idx].whacked) {
                    SetPixel16(fb_rgb24, cx - 1, cy - 1, 255, 255, 255);
                    SetPixel16(fb_rgb24, cx, cy - 1, 255, 240, 120);
                } else if (holes_[idx].kind == WHACK_MOLE_NORMAL) {
                    SetPixel16(fb_rgb24, cx - 1, cy - 1, 205, 115, 38);
                    SetPixel16(fb_rgb24, cx, cy - 1, 240, 165, 90);
                    SetPixel16(fb_rgb24, cx - 1, cy, 165, 85, 28);
                } else {
                    SetPixel16(fb_rgb24, cx - 1, cy - 1, 225, 35, 125);
                    SetPixel16(fb_rgb24, cx, cy - 1, 255, 90, 60);
                    SetPixel16(fb_rgb24, cx - 1, cy, 145, 25, 110);
                }
            }
        }
    }

    // 绘制锤子准星边框角标
    int cur_cx = kHoleX[cursor_col_];
    int cur_cy = kHoleY[cursor_row_];
    bool swinging = (hammer_timer_ > 0.0f);
    uint8_t hr = swinging ? 255 : 0;
    uint8_t hg = 255;
    uint8_t hb = swinging ? 60 : 255;
    SetPixel16(fb_rgb24, cur_cx, cur_cy, hr, hg, hb);
    SetPixel16(fb_rgb24, cur_cx - 2, cur_cy - 1, hr, hg, hb);
    SetPixel16(fb_rgb24, cur_cx + 1, cur_cy - 1, hr, hg, hb);

    // 顶部 HUD: 左侧红心生命, 右侧黄色倒计时条
    for (int i = 0; i < (int)lives_ && i < 3; ++i) {
        SetPixel16(fb_rgb24, i * 2, 0, 235, 65, 55);
    }
    int timer_px = (int)((time_remaining_ / kRoundDuration) * 9.0f + 0.5f);
    for (int i = 0; i < timer_px && i < 9; ++i) {
        SetPixel16(fb_rgb24, 15 - i, 0, 245, 200, 20);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPixel16(fb_rgb24, 6, y, 250, 250, 250);
            SetPixel16(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game016WhackAMole::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    uint32_t prog = (score_ * 100u) / kTargetScore;
    if (prog > 100u) prog = 100u;
    st.progress = (uint8_t)prog;
    return st;
}

static_assert(sizeof(Game016WhackAMole) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
