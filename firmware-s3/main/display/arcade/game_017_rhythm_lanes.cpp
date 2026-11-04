// game_017_rhythm_lanes.cpp —— 目标 #017 四轨节奏 (Rhythm Lanes) 核心实现
#include "game_017_rhythm_lanes.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const float kJudgeY = 13.0f;
static const float kPerfectWindow = 0.75f;

static inline void SetPixel17(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game017RhythmLanes::Game017RhythmLanes()
    : state_(STATE_TITLE),
      notes_{},
      beat_timer_(0.0f),
      beats_spawned_(0),
      notes_cleared_(0),
      combo_(0),
      misses_(0),
      last_lane_(0),
      lane_flash_{0.0f, 0.0f, 0.0f, 0.0f},
      lane_grade_{0, 0, 0, 0},
      miss_flash_timer_(0.0f),
      score_(0),
      high_score_(0),
      rng_seed_(0x17201401u),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
}

uint32_t Game017RhythmLanes::NextRand() {
    rng_seed_ = rng_seed_ * 1103515245u + 12345u;
    return (rng_seed_ >> 16) & 0x7FFFu;
}

void Game017RhythmLanes::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game017RhythmLanes::SpawnBeatNote() {
    if (beats_spawned_ >= kTotalBeats) return;
    int slot = -1;
    for (int i = 0; i < kMaxNotes; ++i) {
        if (!notes_[i].active) {
            slot = i;
            break;
        }
    }
    if (slot < 0) return;

    uint8_t lane = (uint8_t)(NextRand() % 4);
    if (lane == last_lane_ && (NextRand() % 3) != 0) {
        lane = (uint8_t)((lane + 1 + (NextRand() % 3)) % 4);
    }
    last_lane_ = lane;
    if(state_==STATE_PLAYING)SoundEvent(Sound::Beat,lane);

    notes_[slot].lane = lane;
    notes_[slot].y = 0.0f;
    notes_[slot].active = true;
    beats_spawned_++;
}

bool Game017RhythmLanes::AnyActiveNotes() const {
    for (int i = 0; i < kMaxNotes; ++i) {
        if (notes_[i].active) return true;
    }
    return false;
}

void Game017RhythmLanes::HandleLanePress(uint8_t lane) {
    int best_idx = -1;
    float best_dist = 999.0f;
    for (int i = 0; i < kMaxNotes; ++i) {
        if (!notes_[i].active || notes_[i].lane != lane) continue;
        float dist = fabsf(notes_[i].y - kJudgeY);
        if (dist <= JudgeWindow() && dist < best_dist) {
            best_dist = dist;
            best_idx = i;
        }
    }

    if (best_idx >= 0) {
        notes_[best_idx].active = false;
        notes_cleared_++;
        SoundEvent(Sound::Hit,lane);
        int capped_combo = (combo_ > 10) ? 10 : combo_;
        if (best_dist <= kPerfectWindow) {
            AddScore(20u + (uint32_t)(capped_combo * 2));
            lane_grade_[lane] = 2;
            lane_flash_[lane] = 0.22f;
        } else {
            AddScore(10u + (uint32_t)capped_combo);
            lane_grade_[lane] = 1;
            lane_flash_[lane] = 0.18f;
        }
        combo_++;
    } else {
        // 空拍乱按惩罚
        combo_ = 0;
        misses_++;
        miss_flash_timer_ = 0.20f;
        if (misses_ >= MaxMisses()) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
        }
    }
}

void Game017RhythmLanes::Init() {
    Reset();
}

void Game017RhythmLanes::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    for (int i = 0; i < kMaxNotes; ++i) {
        notes_[i].lane = 0;
        notes_[i].y = 0.0f;
        notes_[i].active = false;
    }
    beat_timer_ = 0.0f;
    beats_spawned_ = 0;
    notes_cleared_ = 0;
    combo_ = 0;
    misses_ = 0;
    last_lane_ = 0;
    for (int t = 0; t < 4; ++t) {
        lane_flash_[t] = 0.0f;
        lane_grade_[t] = 0;
    }
    miss_flash_timer_ = 0.0f;
    score_ = 0;
    rng_seed_ = 0x17201401u;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    SpawnBeatNote();
}

void Game017RhythmLanes::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        for (int i = 0; i < kMaxNotes; ++i) {
            notes_[i].lane = 0;
            notes_[i].y = 0.0f;
            notes_[i].active = false;
        }
        beat_timer_ = 0.0f;
        beats_spawned_ = 0;
        notes_cleared_ = 0;
        combo_ = 0;
        misses_ = 0;
        last_lane_ = 0;
        for (int t = 0; t < 4; ++t) {
            lane_flash_[t] = 0.0f;
            lane_grade_[t] = 0;
        }
        miss_flash_timer_ = 0.0f;
        score_ = 0;
        rng_seed_ = 0x17201401u;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        SpawnBeatNote();
    }
}

void Game017RhythmLanes::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game017RhythmLanes::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game017RhythmLanes::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt < 0.0f) dt = 0.0f;
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
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

        for (int t = 0; t < 4; ++t) {
            if (lane_flash_[t] > 0.0f) {
                lane_flash_[t] -= dt;
                if (lane_flash_[t] <= 0.0f) {
                    lane_flash_[t] = 0.0f;
                    lane_grade_[t] = 0;
                }
            }
        }
        if (miss_flash_timer_ > 0.0f) {
            miss_flash_timer_ -= dt;
            if (miss_flash_timer_ < 0.0f) miss_flash_timer_ = 0.0f;
        }

        if (keys_pressed & KEY_LEFT) {
            HandleLanePress(0);
            if (state_ != STATE_PLAYING) return;
        }
        if (keys_pressed & KEY_DOWN) {
            HandleLanePress(1);
            if (state_ != STATE_PLAYING) return;
        }
        if (keys_pressed & KEY_UP) {
            HandleLanePress(2);
            if (state_ != STATE_PLAYING) return;
        }
        if (keys_pressed & KEY_RIGHT) {
            HandleLanePress(3);
            if (state_ != STATE_PLAYING) return;
        }

        for (int i = 0; i < kMaxNotes; ++i) {
            if (!notes_[i].active) continue;
            notes_[i].y += FallSpeed() * dt;
            if (notes_[i].y > 15.2f) {
                notes_[i].active = false;
                combo_ = 0;
                misses_++;
                miss_flash_timer_ = 0.20f;
                if (misses_ >= MaxMisses()) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }

        beat_timer_ += dt;
        while (beat_timer_ >= BeatInterval()) {
            beat_timer_ -= BeatInterval();
            if(beats_spawned_ < kTotalBeats)SpawnBeatNote();
            else SoundEvent(Sound::Beat,last_lane_); // Keep the tail's final notes on the beat.
        }
        if(beats_spawned_ >= kTotalBeats && !AnyActiveNotes()) {
            state_ = STATE_VICTORY;state_timer_ = 0.0f;return;
        }
    }
}

void Game017RhythmLanes::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    static const uint8_t kNoteColor[4][3] = {
        {255, 70, 115},  // Lane 0: 霓虹粉红
        {0, 225, 255},   // Lane 1: 电光青
        {50, 240, 120},  // Lane 2: 翠绿
        {255, 205, 35},  // Lane 3: 琥珀金
    };

    // 4 轨道背景 (每轨 3 像素宽 + 1 像素分割线)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 3 || x == 7 || x == 11 || x == 15) {
                SetPixel17(fb_rgb24, x, y, 36, 42, 65);
            } else {
                SetPixel17(fb_rgb24, x, y, 10, 12, 24);
            }
        }
    }

    // 判定线 y=13..14
    for (int x = 0; x < 16; ++x) {
        if (x == 3 || x == 7 || x == 11 || x == 15) continue;
        if (miss_flash_timer_ > 0.0f) {
            SetPixel17(fb_rgb24, x, 13, 240, 45, 45);
            SetPixel17(fb_rgb24, x, 14, 120, 20, 20);
        } else {
            SetPixel17(fb_rgb24, x, 13, 220, 220, 245);
            SetPixel17(fb_rgb24, x, 14, 70, 75, 110);
        }
    }

    // 绘制下落音符 (2 像素高色块)
    for (int i = 0; i < kMaxNotes; ++i) {
        if (!notes_[i].active) continue;
        int lane = notes_[i].lane;
        int x0 = lane * 4;
        int ny = (int)roundf(notes_[i].y);
        uint8_t cr = kNoteColor[lane][0];
        uint8_t cg = kNoteColor[lane][1];
        uint8_t cb = kNoteColor[lane][2];
        for (int dx = 0; dx < 3; ++dx) {
            SetPixel17(fb_rgb24, x0 + dx, ny, cr, cg, cb);
            SetPixel17(fb_rgb24, x0 + dx, ny - 1, (uint8_t)(cr / 2), (uint8_t)(cg / 2), (uint8_t)(cb / 2));
        }
    }

    // 命中闪光特效
    for (int t = 0; t < 4; ++t) {
        if (lane_flash_[t] > 0.0f) {
            int x0 = t * 4;
            uint8_t fr = (lane_grade_[t] == 2) ? 255 : 90;
            uint8_t fg = 255;
            uint8_t fb_c = (lane_grade_[t] == 2) ? 140 : 180;
            for (int y = 12; y <= 14; ++y) {
                for (int dx = 0; dx < 3; ++dx) {
                    SetPixel17(fb_rgb24, x0 + dx, y, fr, fg, fb_c);
                }
            }
        }
    }

    // Fit every difficulty's remaining chances within the 16-pixel row.
    int hp = MaxMisses() - misses_;
    for (int i = 0; i < hp && i < MaxMisses(); ++i) {
        SetPixel17(fb_rgb24, i * 15 / (MaxMisses() - 1), 0, 80, 230, 140);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPixel17(fb_rgb24, 6, y, 250, 250, 250);
            SetPixel17(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game017RhythmLanes::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    int hp = MaxMisses() - misses_;
    st.lives = (hp > 0 && state_ != STATE_GAMEOVER) ? (uint8_t)hp : 0;
    st.state = (uint8_t)state_;
    int prog = (beats_spawned_ * 100) / kTotalBeats;
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

static_assert(sizeof(Game017RhythmLanes) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
