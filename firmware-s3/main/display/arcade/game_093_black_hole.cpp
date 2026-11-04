// game_093_black_hole.cpp —— 目标 #093 黑洞吞噬 (Hole.io) 核心实现
#include "game_093_black_hole.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const float kWorldSize093 = 24.0f;
static const float kRoundDuration093 = 45.0f;

static inline void SetPx093(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game093BlackHole::Game093BlackHole()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      hole_x_(12.0f),
      hole_y_(12.0f),
      hole_radius_(1.0f),
      time_left_(kRoundDuration093),
      swallow_pulse_(0.0f),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      remaining_props_(kTotalProps) {
    SetupCity();
}

void Game093BlackHole::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game093BlackHole::SetupCity() {
    score_ = 0;
    hole_x_ = 12.0f;
    hole_y_ = 12.0f;
    hole_radius_ = 1.0f;
    time_left_ = kRoundDuration093;
    swallow_pulse_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    remaining_props_ = kTotalProps;

    static const float kTier1Pos[10][2] = {
        {9.0f, 11.0f}, {14.0f, 11.0f}, {11.0f, 8.0f}, {11.0f, 15.0f},
        {6.0f, 6.0f},  {17.0f, 6.0f},  {6.0f, 17.0f}, {17.0f, 17.0f},
        {7.0f, 13.0f}, {16.0f, 9.0f}
    };
    for (int i = 0; i < 10; ++i) {
        props_[i] = {true, 1, 1, kTier1Pos[i][0], kTier1Pos[i][1], 1.0f};
    }

    static const float kTier2Pos[6][2] = {
        {2.0f, 9.0f}, {20.0f, 9.0f}, {2.0f, 15.0f},
        {20.0f, 15.0f}, {9.0f, 2.0f}, {14.0f, 20.0f}
    };
    for (int i = 0; i < 6; ++i) {
        props_[10 + i] = {true, 2, 2, kTier2Pos[i][0], kTier2Pos[i][1], 1.8f};
    }

    static const float kTier3Pos[4][2] = {
        {1.0f, 1.0f}, {20.0f, 1.0f}, {1.0f, 20.0f}, {20.0f, 20.0f}
    };
    for (int i = 0; i < 4; ++i) {
        props_[16 + i] = {true, 3, 3, kTier3Pos[i][0], kTier3Pos[i][1], 2.6f};
    }
}

void Game093BlackHole::Init() {
    Reset();
}

void Game093BlackHole::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    SetupCity();
}

void Game093BlackHole::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupCity();
        state_ = STATE_PLAYING;
    }
}

void Game093BlackHole::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game093BlackHole::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game093BlackHole::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        if (swallow_pulse_ > 0.0f) {
            swallow_pulse_ -= dt;
            if (swallow_pulse_ < 0.0f) swallow_pulse_ = 0.0f;
        }

        time_left_ -= dt;
        if (time_left_ <= 0.0f) {
            time_left_ = 0.0f;
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            return;
        }

        uint16_t move_mask = keys_down | keys_pressed;
        float vx = 0.0f;
        float vy = 0.0f;
        if (move_mask & KEY_LEFT) vx -= 1.0f;
        if (move_mask & KEY_RIGHT) vx += 1.0f;
        if (move_mask & KEY_UP) vy -= 1.0f;
        if (move_mask & KEY_DOWN) vy += 1.0f;

        if (vx != 0.0f || vy != 0.0f) {
            float inv = 1.0f / sqrtf(vx * vx + vy * vy);
            const float move_speed = 9.0f;
            hole_x_ += vx * inv * move_speed * dt;
            hole_y_ += vy * inv * move_speed * dt;
        }

        if (hole_x_ < 1.2f) hole_x_ = 1.2f;
        if (hole_x_ > kWorldSize093 - 1.2f) hole_x_ = kWorldSize093 - 1.2f;
        if (hole_y_ < 1.2f) hole_y_ = 1.2f;
        if (hole_y_ > kWorldSize093 - 1.2f) hole_y_ = kWorldSize093 - 1.2f;

        for (int i = 0; i < kTotalProps; ++i) {
            if (!props_[i].alive) continue;
            float half = (float)props_[i].size * 0.5f;
            float ox = props_[i].x + half;
            float oy = props_[i].y + half;
            float dx = hole_x_ - ox;
            float dy = hole_y_ - oy;
            float dist = hypotf(dx, dy);

            if (hole_radius_ + 0.001f >= props_[i].req_radius) {
                // Can swallow! Apply horizon pull & swallow inside capture radius
                float pull_range = hole_radius_ + half + 0.8f;
                if (dist < pull_range && dist > 0.05f) {
                    float pull = 5.5f * dt;
                    props_[i].x += (dx / dist) * pull;
                    props_[i].y += (dy / dist) * pull;
                    ox = props_[i].x + half;
                    oy = props_[i].y + half;
                    dist = hypotf(hole_x_ - ox, hole_y_ - oy);
                }

                float capture_r = hole_radius_ * 0.85f + 0.45f;
                if (dist <= capture_r) {
                    props_[i].alive = false;
                    if (remaining_props_ > 0) remaining_props_--;
                    swallow_pulse_ = 0.22f;

                    if (props_[i].tier == 1) {
                        hole_radius_ += 0.10f;
                        AddScore(15);
                    } else if (props_[i].tier == 2) {
                        hole_radius_ += 0.15f;
                        AddScore(40);
                    } else {
                        hole_radius_ += 0.20f;
                        AddScore(100);
                    }
                    if (hole_radius_ > 3.5f) hole_radius_ = 3.5f;

                    if (remaining_props_ == 0) {
                        AddScore((uint32_t)(time_left_ * 5.0f));
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            } else {
                // Too large to swallow: solid building/vehicle nudges black hole away!
                float min_sep = half + 0.68f;
                if (dist < min_sep) {
                    if (dist < 0.001f) {
                        hole_x_ = ox + min_sep;
                    } else {
                        hole_x_ = ox + (dx / dist) * min_sep;
                        hole_y_ = oy + (dy / dist) * min_sep;
                    }
                    if (hole_x_ < 1.2f) hole_x_ = 1.2f;
                    if (hole_x_ > kWorldSize093 - 1.2f) hole_x_ = kWorldSize093 - 1.2f;
                    if (hole_y_ < 1.2f) hole_y_ = 1.2f;
                    if (hole_y_ > kWorldSize093 - 1.2f) hole_y_ = kWorldSize093 - 1.2f;
                }
            }
        }
    }
}

void Game093BlackHole::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    int cam_x = (int)roundf(hole_x_ - 8.0f);
    int cam_y = (int)roundf(hole_y_ - 8.0f);
    if (cam_x < 0) cam_x = 0;
    if (cam_x > 8) cam_x = 8;
    if (cam_y < 0) cam_y = 0;
    if (cam_y > 8) cam_y = 8;

    // Scrolling urban asphalt & street grid
    for (int sy = 0; sy < 16; ++sy) {
        int wy = cam_y + sy;
        for (int sx = 0; sx < 16; ++sx) {
            int wx = cam_x + sx;
            if (wx % 6 == 0 || wy % 6 == 0) {
                if (((wx + wy) % 3) == 0) {
                    SetPx093(fb_rgb24, sx, sy, 52, 54, 64);
                } else {
                    SetPx093(fb_rgb24, sx, sy, 34, 36, 44);
                }
            } else {
                SetPx093(fb_rgb24, sx, sy, 22, 26, 32);
            }
        }
    }

    // Render city props across 3 size tiers
    for (int i = 0; i < kTotalProps; ++i) {
        if (!props_[i].alive) continue;
        int px = (int)roundf(props_[i].x) - cam_x;
        int py = (int)roundf(props_[i].y) - cam_y;
        bool edible = (hole_radius_ + 0.001f >= props_[i].req_radius);

        if (props_[i].tier == 1) {
            if ((i & 1) == 0) {
                SetPx093(fb_rgb24, px, py, 46, 215, 90);
            } else {
                SetPx093(fb_rgb24, px, py, 255, 145, 35);
            }
        } else if (props_[i].tier == 2) {
            uint8_t r = edible ? 255 : 215;
            uint8_t g = edible ? 225 : 175;
            uint8_t b = edible ? 55 : 25;
            for (int dy = 0; dy < 2; ++dy) {
                for (int dx = 0; dx < 2; ++dx) {
                    SetPx093(fb_rgb24, px + dx, py + dy,
                             (dx == 0 && dy == 0) ? 255 : r,
                             (dx == 0 && dy == 0) ? 250 : g,
                             b);
                }
            }
        } else {
            for (int dy = 0; dy < 3; ++dy) {
                for (int dx = 0; dx < 3; ++dx) {
                    if (dx == 1 && dy == 1) {
                        SetPx093(fb_rgb24, px + dx, py + dy, 255, 195, 70);
                    } else if (edible) {
                        SetPx093(fb_rgb24, px + dx, py + dy, 55, 225, 255);
                    } else {
                        SetPx093(fb_rgb24, px + dx, py + dy, 35, 135, 185);
                    }
                }
            }
        }
    }

    // Render dark void + glowing purple accretion ring
    float hsx = hole_x_ - (float)cam_x;
    float hsy = hole_y_ - (float)cam_y;
    float pulse = 0.5f + 0.5f * sinf(anim_timer_ * 7.0f);
    float outer_r = hole_radius_ + 0.48f + (swallow_pulse_ > 0.0f ? 0.25f : 0.0f);
    float core_r = hole_radius_ * 0.72f;
    if (core_r < 0.65f) core_r = 0.65f;

    for (int sy = 0; sy < 16; ++sy) {
        for (int sx = 0; sx < 16; ++sx) {
            float d = hypotf(((float)sx + 0.5f) - hsx, ((float)sy + 0.5f) - hsy);
            if (d <= core_r) {
                SetPx093(fb_rgb24, sx, sy, 5, 2, 10);
            } else if (d <= outer_r) {
                uint8_t pr = (uint8_t)(165.0f + 75.0f * pulse);
                uint8_t pg = (uint8_t)(40.0f + (swallow_pulse_ > 0.0f ? 90.0f : 35.0f * pulse));
                uint8_t pb = 255;
                SetPx093(fb_rgb24, sx, sy, pr, pg, pb);
            }
        }
    }

    // Top row timer bar (45s countdown)
    int bars = (int)ceilf((time_left_ / kRoundDuration093) * 16.0f);
    if (bars < 0) bars = 0;
    if (bars > 16) bars = 16;
    for (int x = 0; x < bars; ++x) {
        if (time_left_ > 15.0f) {
            SetPx093(fb_rgb24, x, 0, 140, 80, 255);
        } else {
            SetPx093(fb_rgb24, x, 0, 255, 65, 55);
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx093(fb_rgb24, 6, y, 250, 250, 250);
            SetPx093(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game093BlackHole::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    uint32_t eaten = (uint32_t)(kTotalProps - remaining_props_);
    st.progress = (uint8_t)((eaten * 100u) / (uint32_t)kTotalProps);
    return st;
}

static_assert(sizeof(Game093BlackHole) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
