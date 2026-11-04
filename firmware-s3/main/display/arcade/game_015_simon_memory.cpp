// game_015_simon_memory.cpp —— 目标 #015 闪灯记忆 (Simon Says) 核心实现
#include "game_015_simon_memory.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static inline void SetPixel15(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game015SimonMemory::Game015SimonMemory()
    : state_(STATE_TITLE),
      phase_(SIMON_SHOW_ON),
      sequence_{},
      seq_len_(1),
      show_idx_(0),
      input_idx_(0),
      lit_pad_(-1),
      phase_timer_(0.45f),
      input_flash_timer_(0.0f),
      score_(0),
      high_score_(0),
      rng_seed_(0x15197801u),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
}

uint32_t Game015SimonMemory::NextRand() {
    rng_seed_ = rng_seed_ * 1103515245u + 12345u;
    return (rng_seed_ >> 16) & 0x7FFFu;
}

void Game015SimonMemory::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game015SimonMemory::Init() {
    Reset();
}

void Game015SimonMemory::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    phase_ = SIMON_SHOW_ON;
    memset(sequence_, 0, sizeof(sequence_));
    rng_seed_ = 0x15197801u;
    sequence_[0] = (uint8_t)(NextRand() % 4);
    seq_len_ = 1;
    show_idx_ = 0;
    input_idx_ = 0;
    lit_pad_ = 0;
    phase_timer_ = 0.45f;
    input_flash_timer_ = 0.0f;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
}

void Game015SimonMemory::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        phase_ = SIMON_SHOW_ON;
        memset(sequence_, 0, sizeof(sequence_));
        rng_seed_ = 0x15197801u;
        sequence_[0] = (uint8_t)(NextRand() % 4);
        seq_len_ = 1;
        show_idx_ = 0;
        input_idx_ = 0;
        lit_pad_ = (int)sequence_[0];
        phase_timer_ = 0.45f;
        input_flash_timer_ = 0.0f;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
    }
}

void Game015SimonMemory::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game015SimonMemory::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game015SimonMemory::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt < 0.0f) dt = 0.0f;
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        lit_pad_ = ((int)(anim_timer_ * 3.0f)) % 4;
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_DOWN | KEY_UP | KEY_RIGHT)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_DOWN | KEY_UP | KEY_RIGHT))) {
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

        float show_dur = 0.45f - (float)(seq_len_ - 1) * 0.015f;
        if (show_dur < 0.20f) show_dur = 0.20f;

        if (phase_ == SIMON_SHOW_ON) {
            lit_pad_ = (int)sequence_[show_idx_];
            phase_timer_ -= dt;
            if (phase_timer_ <= 0.0f) {
                lit_pad_ = -1;
                phase_ = SIMON_SHOW_GAP;
                phase_timer_ = 0.14f;
            }
            return;
        }

        if (phase_ == SIMON_SHOW_GAP) {
            lit_pad_ = -1;
            phase_timer_ -= dt;
            if (phase_timer_ <= 0.0f) {
                show_idx_++;
                if (show_idx_ < seq_len_) {
                    phase_ = SIMON_SHOW_ON;
                    phase_timer_ = show_dur;
                    lit_pad_ = (int)sequence_[show_idx_];
                } else {
                    phase_ = SIMON_INPUT;
                    input_idx_ = 0;
                    lit_pad_ = -1;
                    input_flash_timer_ = 0.0f;
                }
            }
            return;
        }

        if (phase_ == SIMON_ROUND_PAUSE) {
            if (input_flash_timer_ > 0.0f) {
                input_flash_timer_ -= dt;
                if (input_flash_timer_ <= 0.0f) lit_pad_ = -1;
            }
            phase_timer_ -= dt;
            if (phase_timer_ <= 0.0f) {
                show_idx_ = 0;
                phase_ = SIMON_SHOW_ON;
                phase_timer_ = show_dur;
                lit_pad_ = (int)sequence_[0];
            }
            return;
        }

        if (phase_ == SIMON_INPUT) {
            if (input_flash_timer_ > 0.0f) {
                input_flash_timer_ -= dt;
                if (input_flash_timer_ <= 0.0f) {
                    input_flash_timer_ = 0.0f;
                    lit_pad_ = -1;
                }
            }

            static const uint16_t kPadKeys[4] = {KEY_LEFT, KEY_DOWN, KEY_UP, KEY_RIGHT};
            const uint16_t kTrackMask = KEY_LEFT | KEY_DOWN | KEY_UP | KEY_RIGHT;
            uint16_t pressed_tracks = keys_pressed & kTrackMask;
            if (pressed_tracks != 0) {
                uint8_t expected = sequence_[input_idx_];
                if (pressed_tracks == kPadKeys[expected]) {
                    lit_pad_ = (int)expected;
                    input_flash_timer_ = 0.18f;
                    input_idx_++;
                    if (input_idx_ >= seq_len_) {
                        AddScore(10u * (uint32_t)seq_len_);
                        if (seq_len_ >= kMaxSequence) {
                            state_ = STATE_VICTORY;
                            state_timer_ = 0.0f;
                            return;
                        }
                        sequence_[seq_len_] = (uint8_t)(NextRand() % 4);
                        seq_len_++;
                        phase_ = SIMON_ROUND_PAUSE;
                        phase_timer_ = 0.35f;
                    }
                } else {
                    lit_pad_ = -1;
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }
    }
}

void Game015SimonMemory::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, 768);

    // 4 象限色块: 0=左上红(LEFT), 1=左下绿(DOWN), 2=右上蓝(UP), 3=右下黄(RIGHT)
    static const int kPadRect[4][4] = {
        {1, 1, 6, 6},
        {1, 9, 6, 14},
        {9, 1, 14, 6},
        {9, 9, 14, 14},
    };
    static const uint8_t kDimColors[4][3] = {
        {75, 16, 20},
        {14, 72, 28},
        {16, 38, 90},
        {85, 72, 12},
    };
    static const uint8_t kBrightColors[4][3] = {
        {255, 55, 65},
        {45, 250, 95},
        {55, 155, 255},
        {255, 235, 45},
    };

    for (int p = 0; p < 4; ++p) {
        bool is_lit = (lit_pad_ == p) && (state_ != STATE_GAMEOVER);
        uint8_t cr = is_lit ? kBrightColors[p][0] : kDimColors[p][0];
        uint8_t cg = is_lit ? kBrightColors[p][1] : kDimColors[p][1];
        uint8_t cb = is_lit ? kBrightColors[p][2] : kDimColors[p][2];
        if (state_ == STATE_GAMEOVER) {
            cr = 180; cg = 20; cb = 20;
        }

        for (int y = kPadRect[p][1]; y <= kPadRect[p][3]; ++y) {
            for (int x = kPadRect[p][0]; x <= kPadRect[p][2]; ++x) {
                SetPixel15(fb_rgb24, x, y, cr, cg, cb);
            }
        }
        if (is_lit) {
            int cx = (kPadRect[p][0] + kPadRect[p][2]) / 2;
            int cy = (kPadRect[p][1] + kPadRect[p][3]) / 2;
            SetPixel15(fb_rgb24, cx, cy, 255, 255, 255);
            SetPixel15(fb_rgb24, cx + 1, cy, 255, 255, 255);
            SetPixel15(fb_rgb24, cx, cy + 1, 255, 255, 255);
            SetPixel15(fb_rgb24, cx + 1, cy + 1, 255, 255, 255);
        }
    }

    // 中心状态核心: 演示期青色, 玩家输入期亮绿
    uint8_t hr = 120, hg = 120, hb = 140;
    if (state_ == STATE_PLAYING) {
        if (phase_ == SIMON_INPUT) {
            hr = 40; hg = 230; hb = 120;
        } else {
            hr = 0; hg = 200; hb = 255;
        }
    } else if (state_ == STATE_GAMEOVER) {
        hr = 255; hg = 30; hb = 30;
    }
    SetPixel15(fb_rgb24, 7, 7, hr, hg, hb);
    SetPixel15(fb_rgb24, 8, 7, hr, hg, hb);
    SetPixel15(fb_rgb24, 7, 8, hr, hg, hb);
    SetPixel15(fb_rgb24, 8, 8, hr, hg, hb);

    // 顶部进度条 (长度 1..15)
    for (int i = 0; i < seq_len_ && i < 15; ++i) {
        SetPixel15(fb_rgb24, i, 0, 220, 190, 40);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPixel15(fb_rgb24, 6, y, 250, 250, 250);
            SetPixel15(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game015SimonMemory::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    int completed = (state_ == STATE_VICTORY) ? kMaxSequence : (seq_len_ - 1);
    st.progress = (uint8_t)((completed * 100) / kMaxSequence);
    return st;
}

static_assert(sizeof(Game015SimonMemory) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
