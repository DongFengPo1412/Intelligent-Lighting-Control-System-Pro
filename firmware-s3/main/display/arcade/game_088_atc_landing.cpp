// game_088_atc_landing.cpp —— 目标 #088 机场降落引导 核心实现
#include "game_088_atc_landing.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const int kAtcDirVec[4][2] = {
    {1, 0},   // ATC_DIR_RIGHT (EAST)
    {0, 1},   // ATC_DIR_DOWN  (SOUTH)
    {-1, 0},  // ATC_DIR_LEFT  (WEST)
    {0, -1},  // ATC_DIR_UP    (NORTH)
};

static inline void SetPx88(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game088AtcLanding::Game088AtcLanding()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      selected_plane_(0),
      landed_count_(0),
      spawn_timer_(1.5f),
      landing_flash_timer_(0.0f),
      rng_seed_(0x2009088Bu) {
    SetupMatch(STATE_TITLE);
}

void Game088AtcLanding::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game088AtcLanding::EnsureValidSelection() {
    if (selected_plane_ >= 0 && selected_plane_ < kMaxPlanes && planes_[selected_plane_].active) {
        return;
    }
    for (int i = 0; i < kMaxPlanes; ++i) {
        if (planes_[i].active) {
            selected_plane_ = i;
            return;
        }
    }
    selected_plane_ = 0;
}

void Game088AtcLanding::SpawnPlane() {
    int slot = -1;
    for (int i = 0; i < kMaxPlanes; ++i) {
        if (!planes_[i].active) {
            slot = i;
            break;
        }
    }
    if (slot < 0) return;

    static const float kEntryPoints[8][3] = {
        {1.0f, 3.0f, (float)ATC_DIR_RIGHT},
        {14.0f, 3.0f, (float)ATC_DIR_LEFT},
        {1.0f, 13.0f, (float)ATC_DIR_RIGHT},
        {14.0f, 13.0f, (float)ATC_DIR_LEFT},
        {3.0f, 1.5f, (float)ATC_DIR_DOWN},
        {12.0f, 1.5f, (float)ATC_DIR_DOWN},
        {3.0f, 14.5f, (float)ATC_DIR_UP},
        {12.0f, 14.5f, (float)ATC_DIR_UP},
    };

    rng_seed_ = rng_seed_ * 1103515245u + 12345u;
    int start_k = (int)((rng_seed_ >> 16) % 8);

    for (int attempt = 0; attempt < 8; ++attempt) {
        int k = (start_k + attempt) % 8;
        float sx = kEntryPoints[k][0];
        float sy = kEntryPoints[k][1];
        bool safe = true;
        for (int i = 0; i < kMaxPlanes; ++i) {
            if (!planes_[i].active) continue;
            float dx = planes_[i].x - sx;
            float dy = planes_[i].y - sy;
            if (dx * dx + dy * dy < 4.2f * 4.2f) {
                safe = false;
                break;
            }
        }
        if (safe) {
            planes_[slot].active = true;
            planes_[slot].x = sx;
            planes_[slot].y = sy;
            planes_[slot].dir = (uint8_t)kEntryPoints[k][2];
            planes_[slot].speed = 1.9f;
            planes_[slot].fuel = 30.0f;
            planes_[slot].color_id = (uint8_t)slot;
            EnsureValidSelection();
            return;
        }
    }
}

void Game088AtcLanding::SetupMatch(CartridgeState new_state) {
    state_ = new_state;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    selected_plane_ = 0;
    landed_count_ = 0;
    spawn_timer_ = 2.4f;
    landing_flash_timer_ = 0.0f;
    rng_seed_ = 0x2009088Bu;

    for (int i = 0; i < kMaxPlanes; ++i) {
        planes_[i] = {false, 0.0f, 0.0f, ATC_DIR_RIGHT, 1.9f, 30.0f, (uint8_t)i};
    }

    SpawnPlane();
}

void Game088AtcLanding::Init() {
    Reset();
}

void Game088AtcLanding::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    SetupMatch(STATE_TITLE);
}

void Game088AtcLanding::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupMatch(STATE_PLAYING);
    }
}

void Game088AtcLanding::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game088AtcLanding::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game088AtcLanding::SetSelectedHeading(uint8_t new_dir) {
    EnsureValidSelection();
    if (selected_plane_ >= 0 && selected_plane_ < kMaxPlanes && planes_[selected_plane_].active) {
        planes_[selected_plane_].dir = new_dir;
        if (new_dir == ATC_DIR_RIGHT && fabsf(planes_[selected_plane_].y - 8.0f) <= 0.6f) {
            planes_[selected_plane_].y = 8.0f;
        }
    }
}

void Game088AtcLanding::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    (void)keys_down;
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

    if (keys_pressed & KEY_START) {
        state_ = STATE_PAUSED;
        return;
    }

    if (landing_flash_timer_ > 0.0f) {
        landing_flash_timer_ -= dt;
    }

    EnsureValidSelection();

    // KEY_B cycles active selected aircraft
    if (keys_pressed & KEY_B) {
        for (int step = 1; step <= kMaxPlanes; ++step) {
            int cand = (selected_plane_ + step) % kMaxPlanes;
            if (planes_[cand].active) {
                selected_plane_ = cand;
                break;
            }
        }
    }

    // D-pad or KEY_A assigns new heading vector to selected aircraft
    if (keys_pressed & KEY_RIGHT) SetSelectedHeading(ATC_DIR_RIGHT);
    else if (keys_pressed & KEY_DOWN) SetSelectedHeading(ATC_DIR_DOWN);
    else if (keys_pressed & KEY_LEFT) SetSelectedHeading(ATC_DIR_LEFT);
    else if (keys_pressed & KEY_UP) SetSelectedHeading(ATC_DIR_UP);
    else if (keys_pressed & KEY_A) {
        EnsureValidSelection();
        if (planes_[selected_plane_].active) {
            SetSelectedHeading((uint8_t)((planes_[selected_plane_].dir + 1) % 4));
        }
    }

    // Spawn planes up to 4 active (and ensure at least 1 plane when airspace empty)
    int active_cnt = 0;
    for (int i = 0; i < kMaxPlanes; ++i) {
        if (planes_[i].active) active_cnt++;
    }
    spawn_timer_ -= dt;
    if ((active_cnt == 0 && landed_count_ < kTargetLandings) || (spawn_timer_ <= 0.0f && active_cnt < kMaxPlanes)) {
        SpawnPlane();
        spawn_timer_ = 3.6f;
    }

    // Update aircraft positions, fuel, and Eastward final approach onto threshold (5, 8)
    for (int i = 0; i < kMaxPlanes; ++i) {
        if (!planes_[i].active) continue;
        AtcPlane& p = planes_[i];

        p.fuel -= dt;
        if (p.fuel <= 0.0f) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            return;
        }

        p.x += (float)kAtcDirVec[p.dir][0] * p.speed * dt;
        p.y += (float)kAtcDirVec[p.dir][1] * p.speed * dt;

        // Airspace border bounce
        if (p.x < 0.6f && p.dir == ATC_DIR_LEFT) { p.x = 0.6f; p.dir = ATC_DIR_RIGHT; }
        else if (p.x > 14.6f && p.dir == ATC_DIR_RIGHT) { p.x = 14.6f; p.dir = ATC_DIR_LEFT; }
        if (p.y < 1.4f && p.dir == ATC_DIR_UP) { p.y = 1.4f; p.dir = ATC_DIR_DOWN; }
        else if (p.y > 14.6f && p.dir == ATC_DIR_DOWN) { p.y = 14.6f; p.dir = ATC_DIR_UP; }

        // Check Eastward final approach onto runway threshold (5, 8)
        if (p.dir == ATC_DIR_RIGHT && fabsf(p.x - 5.0f) <= 0.65f && fabsf(p.y - 8.0f) <= 0.65f) {
            p.active = false;
            landed_count_++;
            landing_flash_timer_ = 0.35f;
            AddScore(100);
            EnsureValidSelection();
            if (landed_count_ >= kTargetLandings) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                return;
            }
        }
    }

    // Mid-air collision check (dist < 1.3 px)
    for (int i = 0; i < kMaxPlanes; ++i) {
        if (!planes_[i].active) continue;
        for (int j = i + 1; j < kMaxPlanes; ++j) {
            if (!planes_[j].active) continue;
            float dx = planes_[i].x - planes_[j].x;
            float dy = planes_[i].y - planes_[j].y;
            if (dx * dx + dy * dy < 1.3f * 1.3f) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game088AtcLanding::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Radar dark green-teal airspace backdrop
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (y == 0) {
                SetPx88(fb_rgb24, x, y, 8, 12, 18);
            } else if (x == 8 || y == 8) {
                SetPx88(fb_rgb24, x, y, 12, 34, 28);
            } else {
                SetPx88(fb_rgb24, x, y, 8, 22, 20);
            }
        }
    }

    // Approach guide beacons at x=3,4 on y=8
    bool beacon_on = (((int)(anim_timer_ * 5.0f)) % 2) == 0;
    SetPx88(fb_rgb24, 3, 8, 15, beacon_on ? 140 : 65, 50);
    SetPx88(fb_rgb24, 4, 8, 20, beacon_on ? 190 : 85, 65);

    // Central horizontal Runway strip (x=5..11, y=8)
    for (int x = 5; x <= 11; ++x) {
        if (landing_flash_timer_ > 0.0f) {
            SetPx88(fb_rgb24, x, 8, 60, 255, 130);
        } else if (x == 5) {
            // Threshold (5, 8)
            SetPx88(fb_rgb24, x, 8, 40, 245, 95);
        } else if ((x & 1) == 1) {
            SetPx88(fb_rgb24, x, 8, 180, 190, 200);
        } else {
            SetPx88(fb_rgb24, x, 8, 70, 75, 85);
        }
    }

    // Aircraft + 1px heading nose + selection highlight + low-fuel blink
    static const uint8_t kPlaneColors[4][3] = {
        {0, 225, 255},
        {255, 195, 35},
        {215, 105, 255},
        {80, 250, 140},
    };
    bool fast_blink = (((int)(anim_timer_ * 10.0f)) % 2) == 0;

    for (int i = 0; i < kMaxPlanes; ++i) {
        if (!planes_[i].active) continue;
        const AtcPlane& p = planes_[i];
        int px = (int)roundf(p.x);
        int py = (int)roundf(p.y);
        int nx = px + kAtcDirVec[p.dir][0];
        int ny = py + kAtcDirVec[p.dir][1];

        // Nose heading vector pixel
        if (i == selected_plane_) {
            SetPx88(fb_rgb24, nx, ny, 255, 255, 255);
        } else {
            SetPx88(fb_rgb24, nx, ny, 90, 140, 150);
        }

        // Fuselage dot
        if (p.fuel < 7.0f && fast_blink) {
            SetPx88(fb_rgb24, px, py, 255, 35, 35);
        } else if (i == selected_plane_ && !fast_blink) {
            SetPx88(fb_rgb24, px, py, 255, 255, 255);
        } else {
            const uint8_t* col = kPlaneColors[p.color_id & 3];
            SetPx88(fb_rgb24, px, py, col[0], col[1], col[2]);
        }
    }

    // Row 0 HUD: Landed progress (0..9) + Selected Plane Fuel bar (12..15)
    for (int k = 0; k < kTargetLandings; ++k) {
        if (k < (int)landed_count_) {
            SetPx88(fb_rgb24, k, 0, 45, 240, 105);
        } else {
            SetPx88(fb_rgb24, k, 0, 20, 45, 30);
        }
    }
    if (selected_plane_ >= 0 && selected_plane_ < kMaxPlanes && planes_[selected_plane_].active) {
        int fpips = (int)ceilf((planes_[selected_plane_].fuel / 30.0f) * 4.0f);
        if (fpips < 0) fpips = 0;
        if (fpips > 4) fpips = 4;
        for (int f = 0; f < 4; ++f) {
            if (f < fpips) {
                if (fpips <= 1) SetPx88(fb_rgb24, 12 + f, 0, 255, 50, 50);
                else SetPx88(fb_rgb24, 12 + f, 0, 255, 205, 40);
            }
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx88(fb_rgb24, 6, y, 250, 250, 250);
            SetPx88(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game088AtcLanding::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((landed_count_ * 100) / kTargetLandings);
    if (st.progress > 100) st.progress = 100;
    return st;
}

static_assert(sizeof(Game088AtcLanding) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
