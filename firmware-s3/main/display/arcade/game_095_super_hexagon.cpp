// game_095_super_hexagon.cpp —— 目标 #095 旋转避壁 (Super Hexagon) 核心实现
#include "game_095_super_hexagon.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const float kPi095 = 3.14159265f;
static const float kTwoPi095 = 6.28318531f;
static const float kSectorSpan095 = 1.04719755f; // 2*pi / 6
static const float kPlayerRadius095 = 2.2f;

static inline void SetPx095(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

int Game095SuperHexagon::AngleToSector(float angle) {
    float a = fmodf(angle, kTwoPi095);
    if (a < 0.0f) a += kTwoPi095;
    int sec = (int)(a / kSectorSpan095);
    if (sec < 0) sec = 0;
    if (sec > 5) sec = 5;
    return sec;
}

Game095SuperHexagon::Game095SuperHexagon()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      rng_seed_(0x2012BEEFu),
      player_angle_(0.52f),
      survival_timer_(0.0f),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      walls_passed_(0),
      last_gap_(0) {
    SetupArena();
}

uint32_t Game095SuperHexagon::NextRand() {
    rng_seed_ = rng_seed_ * 1103515245u + 12345u;
    return (rng_seed_ >> 16) & 0x7FFFu;
}

void Game095SuperHexagon::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

uint8_t Game095SuperHexagon::MakeWallMask() {
    uint8_t gap0 = (uint8_t)((last_gap_ + 1u + (NextRand() % 5u)) % 6u);
    last_gap_ = gap0;
    uint8_t mask = (uint8_t)(0x3Fu & ~(1u << gap0));
    if ((NextRand() & 1u) == 0u) {
        uint8_t gap1 = (uint8_t)((gap0 + 3u) % 6u);
        mask = (uint8_t)(mask & ~(1u << gap1));
    }
    return mask;
}

void Game095SuperHexagon::SetupArena() {
    score_ = 0;
    rng_seed_ = 0x2012BEEFu;
    player_angle_ = 0.52f;
    survival_timer_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    walls_passed_ = 0;
    last_gap_ = 0;

    for (int i = 0; i < kNumWalls; ++i) {
        walls_[i].radius = 9.0f + (float)i * 5.5f;
        walls_[i].solid_mask = MakeWallMask();
        walls_[i].passed = false;
    }
}

void Game095SuperHexagon::Init() {
    Reset();
}

void Game095SuperHexagon::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    SetupArena();
}

void Game095SuperHexagon::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupArena();
        state_ = STATE_PLAYING;
    }
}

void Game095SuperHexagon::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game095SuperHexagon::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game095SuperHexagon::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt < 0.0f) dt = 0.0f;
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        player_angle_ = fmodf(player_angle_ + 1.8f * dt, kTwoPi095);
        if (keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_A | KEY_B | KEY_UP | KEY_DOWN)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_A | KEY_B))) {
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

        survival_timer_ += dt;

        uint16_t ctrl = keys_down | keys_pressed;
        const float rot_speed = 7.4f;
        if (ctrl & (KEY_LEFT | KEY_A)) {
            player_angle_ -= rot_speed * dt;
        }
        if (ctrl & (KEY_RIGHT | KEY_B)) {
            player_angle_ += rot_speed * dt;
        }
        player_angle_ = fmodf(player_angle_, kTwoPi095);
        if (player_angle_ < 0.0f) player_angle_ += kTwoPi095;

        int player_sec = AngleToSector(player_angle_);
        float shrink_speed = (difficulty_==0?3.f:difficulty_==2?4.3f:3.8f) + (float)walls_passed_ * 0.04f;
        float maximum=difficulty_==0?4.f:difficulty_==2?5.5f:5.f;
        if (shrink_speed > maximum) shrink_speed = maximum;

        for (int i = 0; i < kNumWalls; ++i) {
            walls_[i].radius -= shrink_speed * dt;

            if (walls_[i].radius <= 2.50f && walls_[i].radius >= 1.90f) {
                if ((walls_[i].solid_mask & (1u << player_sec)) != 0u) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                }
            }

            if (!walls_[i].passed && walls_[i].radius < 1.90f) {
                walls_[i].passed = true;
                walls_passed_++;
                AddScore(25);
                if (walls_passed_ >= 30 || survival_timer_ >= 45.0f) {
                    AddScore(100);
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    return;
                }
            }

            if (walls_[i].radius < 1.3f) {
                float max_r = 9.0f;
                for (int j = 0; j < kNumWalls; ++j) {
                    if (j != i && walls_[j].radius > max_r) {
                        max_r = walls_[j].radius;
                    }
                }
                walls_[i].radius = max_r + 5.5f;
                walls_[i].solid_mask = MakeWallMask();
                walls_[i].passed = false;
            }
        }
    }
}

void Game095SuperHexagon::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    float pulse = 0.5f + 0.5f * sinf(anim_timer_ * 6.0f);
    int hue_phase = ((int)(anim_timer_ * 0.7f)) % 3;

    // 6-sector alternating geometric backdrop + shrinking hexagonal walls
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            float dx = ((float)x + 0.5f) - 7.5f;
            float dy = ((float)y + 0.5f) - 7.5f;
            float ang = atan2f(dy, dx);
            if (ang < 0.0f) ang += kTwoPi095;
            int sec = AngleToSector(ang);

            float bisector = ((float)sec + 0.5f) * kSectorSpan095;
            float r_hex = (dx * cosf(bisector) + dy * sinf(bisector)) / 0.8660254f;

            bool even_sec = ((sec & 1) == 0);
            uint8_t br = 0, bg = 0, bb = 0;
            if (hue_phase == 0) {
                br = even_sec ? (uint8_t)(42 + 16 * pulse) : 22;
                bg = 8;
                bb = even_sec ? 32 : 18;
            } else if (hue_phase == 1) {
                br = 12;
                bg = even_sec ? 28 : 14;
                bb = even_sec ? (uint8_t)(52 + 16 * pulse) : 30;
            } else {
                br = even_sec ? 38 : 20;
                bg = even_sec ? (uint8_t)(24 + 12 * pulse) : 12;
                bb = 8;
            }

            // Check if pixel lies on any solid hexagonal wall band
            bool on_wall = false;
            for (int i = 0; i < kNumWalls; ++i) {
                if ((walls_[i].solid_mask & (1u << sec)) != 0u) {
                    if (fabsf(r_hex - walls_[i].radius) <= 0.52f && walls_[i].radius <= 9.6f) {
                        on_wall = true;
                        break;
                    }
                }
            }

            if (on_wall) {
                if (hue_phase == 0) {
                    SetPx095(fb_rgb24, x, y, 255, 70, 95);
                } else if (hue_phase == 1) {
                    SetPx095(fb_rgb24, x, y, 60, 225, 255);
                } else {
                    SetPx095(fb_rgb24, x, y, 255, 185, 35);
                }
            } else {
                SetPx095(fb_rgb24, x, y, br, bg, bb);
            }
        }
    }

    // Pulsing 2x2 center core at (7..8, 7..8)
    uint8_t cr = (uint8_t)(180.0f + 75.0f * pulse);
    uint8_t cg = (hue_phase == 1) ? 245 : (uint8_t)(60.0f + 90.0f * pulse);
    uint8_t cb = (hue_phase == 2) ? 60 : 255;
    for (int cy = 7; cy <= 8; ++cy) {
        for (int cx = 7; cx <= 8; ++cx) {
            SetPx095(fb_rgb24, cx, cy, cr, cg, cb);
        }
    }

    // Orbiting player marker at radius ~2.2
    int px = (int)floorf(7.5f + kPlayerRadius095 * cosf(player_angle_));
    int py = (int)floorf(7.5f + kPlayerRadius095 * sinf(player_angle_));
    if (state_ == STATE_GAMEOVER) {
        SetPx095(fb_rgb24, px, py, 255, 40, 40);
    } else {
        SetPx095(fb_rgb24, px, py, 255, 255, 255);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx095(fb_rgb24, 6, y, 250, 250, 250);
            SetPx095(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game095SuperHexagon::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    uint32_t prog = ((uint32_t)walls_passed_ * 100u) / 30u;
    st.progress = (uint8_t)(prog > 100u ? 100u : prog);
    return st;
}

static_assert(sizeof(Game095SuperHexagon) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
