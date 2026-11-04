// game_094_grapple_swing.cpp —— 目标 #094 钩爪摆荡 (Grapple Swing) 核心实现
#include "game_094_grapple_swing.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const float kFinishX094 = 90.0f;

static inline void SetPx094(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game094GrappleSwing::Game094GrappleSwing()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      lives_(3),
      px_(3.5f),
      py_(9.0f),
      vx_(0.0f),
      vy_(0.0f),
      on_ground_(true),
      latched_(false),
      latched_by_hold_(false),
      latched_anchor_(-1),
      rope_len_(6.0f),
      theta_(0.0f),
      omega_(0.0f),
      grapple_buffer_(0.0f),
      checkpoint_x_(3.5f),
      checkpoint_y_(9.0f),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    SetupCourse();
}

void Game094GrappleSwing::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game094GrappleSwing::RespawnPlayer() {
    px_ = checkpoint_x_;
    py_ = checkpoint_y_;
    vx_ = 0.0f;
    vy_ = 0.0f;
    on_ground_ = true;
    latched_ = false;
    latched_by_hold_ = false;
    latched_anchor_ = -1;
    rope_len_ = 6.0f;
    theta_ = 0.0f;
    omega_ = 0.0f;
    grapple_buffer_ = 0.0f;
}

void Game094GrappleSwing::SetupCourse() {
    score_ = 0;
    lives_ = 3;
    checkpoint_x_ = 3.5f;
    checkpoint_y_ = 9.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;

    static const float kAnchorCoords[kNumAnchors][2] = {
        {9.5f, 2.0f},  {21.0f, 2.0f}, {33.0f, 2.5f}, {45.0f, 2.0f},
        {57.0f, 2.0f}, {69.0f, 2.5f}, {80.0f, 2.0f}, {88.5f, 2.5f}
    };
    for (int i = 0; i < kNumAnchors; ++i) {
        anchors_[i] = {kAnchorCoords[i][0], kAnchorCoords[i][1], false};
    }

    static const float kGemCoords[kNumGems][2] = {
        {15.0f, 7.5f}, {27.0f, 7.5f}, {39.0f, 8.0f},
        {51.0f, 7.5f}, {63.0f, 7.5f}, {75.0f, 8.0f}, {85.0f, 7.5f}
    };
    for (int i = 0; i < kNumGems; ++i) {
        gems_[i] = {kGemCoords[i][0], kGemCoords[i][1], false};
    }

    ledges_[0] = {0.0f, 6.5f, 10.0f};
    ledges_[1] = {41.5f, 44.5f, 11.0f};
    ledges_[2] = {89.0f, 99.0f, 10.5f};

    RespawnPlayer();
}

void Game094GrappleSwing::Init() {
    Reset();
}

void Game094GrappleSwing::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    SetupCourse();
}

void Game094GrappleSwing::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupCourse();
        state_ = STATE_PLAYING;
    }
}

void Game094GrappleSwing::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game094GrappleSwing::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game094GrappleSwing::TryAttachAnchor(bool held) {
    int best = -1;
    float best_metric = 999.0f;

    for (int i = 0; i < kNumAnchors; ++i) {
        float ax = anchors_[i].x;
        float ay = anchors_[i].y;
        if (ay >= py_ - 0.8f) continue;
        if (ax < px_ - 3.5f) continue;
        float dist = hypotf(px_ - ax, py_ - ay);
        if (dist < 2.2f || dist > 12.5f) continue;

        float metric = dist - ((ax >= px_) ? 1.5f : 0.0f);
        if (metric < best_metric) {
            best_metric = metric;
            best = i;
        }
    }

    if (best < 0) return false;

    float ax = anchors_[best].x;
    float ay = anchors_[best].y;
    float dx = px_ - ax;
    float dy = py_ - ay;
    float dist = hypotf(dx, dy);
    if (dist < 2.5f) dist = 2.5f;
    if (dist > 10.5f) dist = 10.5f;

    latched_ = true;
    latched_by_hold_ = held;
    latched_anchor_ = (int8_t)best;
    rope_len_ = dist;
    theta_ = atan2f(dx, dy);
    on_ground_ = false;
    grapple_buffer_ = 0.0f;

    float v_tan = vx_ * cosf(theta_) - vy_ * sinf(theta_);
    omega_ = v_tan / rope_len_;
    if (ax > px_ && omega_ < 1.15f) {
        omega_ = 1.15f;
    }
    if (omega_ < -5.5f) omega_ = -5.5f;
    if (omega_ > 5.5f) omega_ = 5.5f;

    px_ = ax + rope_len_ * sinf(theta_);
    py_ = ay + rope_len_ * cosf(theta_);
    vx_ = rope_len_ * cosf(theta_) * omega_;
    vy_ = -rope_len_ * sinf(theta_) * omega_;

    if (!anchors_[best].visited) {
        anchors_[best].visited = true;
        AddScore(25);
    }
    return true;
}

void Game094GrappleSwing::DetachGrapple() {
    if (!latched_) return;
    vx_ = rope_len_ * cosf(theta_) * omega_;
    vy_ = -rope_len_ * sinf(theta_) * omega_ - 1.2f;
    latched_ = false;
    latched_by_hold_ = false;
    latched_anchor_ = -1;
}

void Game094GrappleSwing::LoseLife() {
    if (lives_ > 1) {
        lives_--;
        RespawnPlayer();
    } else {
        lives_ = 0;
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
    }
}

void Game094GrappleSwing::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B))) {
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

        if (latched_) {
            bool release_hold = latched_by_hold_ && ((keys_down & KEY_A) == 0);
            if ((keys_pressed & (KEY_A | KEY_B)) || release_hold) {
                DetachGrapple();
            }
        } else {
            if (keys_pressed & KEY_A) {
                if (!TryAttachAnchor((keys_down & KEY_A) != 0)) {
                    grapple_buffer_ = 0.18f;
                }
            } else if (grapple_buffer_ > 0.0f) {
                grapple_buffer_ -= dt;
                if (keys_down & KEY_A) {
                    TryAttachAnchor(true);
                } else {
                    grapple_buffer_ = 0.0f;
                }
            }
        }

        if (latched_ && latched_anchor_ >= 0) {
            uint16_t ctrl = keys_down | keys_pressed;
            if (ctrl & KEY_UP) {
                rope_len_ -= 4.5f * dt;
                if (rope_len_ < 2.5f) rope_len_ = 2.5f;
            }
            if (ctrl & KEY_DOWN) {
                rope_len_ += 4.5f * dt;
                if (rope_len_ > 10.5f) rope_len_ = 10.5f;
            }

            float ang_acc = -(24.0f / rope_len_) * sinf(theta_);
            if (ctrl & KEY_RIGHT) ang_acc += 4.2f;
            if (ctrl & KEY_LEFT) ang_acc -= 4.2f;

            omega_ += ang_acc * dt;
            omega_ *= (1.0f - 0.12f * dt);
            if (omega_ < -5.5f) omega_ = -5.5f;
            if (omega_ > 5.5f) omega_ = 5.5f;

            theta_ += omega_ * dt;
            if (theta_ < -1.42f) {
                theta_ = -1.42f;
                if (omega_ < 0.0f) omega_ = -omega_ * 0.4f;
            } else if (theta_ > 1.42f) {
                theta_ = 1.42f;
                if (omega_ > 0.0f) omega_ = -omega_ * 0.4f;
            }

            float ax = anchors_[latched_anchor_].x;
            float ay = anchors_[latched_anchor_].y;
            px_ = ax + rope_len_ * sinf(theta_);
            py_ = ay + rope_len_ * cosf(theta_);
            vx_ = rope_len_ * cosf(theta_) * omega_;
            vy_ = -rope_len_ * sinf(theta_) * omega_;
        } else if (on_ground_) {
            uint16_t ctrl = keys_down | keys_pressed;
            if (ctrl & KEY_LEFT) px_ -= 6.0f * dt;
            if (ctrl & KEY_RIGHT) px_ += 6.0f * dt;
            if (px_ < 0.5f) px_ = 0.5f;

            if (keys_pressed & (KEY_B | KEY_UP)) {
                vy_ = -9.5f;
                if (ctrl & KEY_RIGHT) vx_ = 4.5f;
                on_ground_ = false;
            } else {
                bool supported = false;
                for (int i = 0; i < kNumLedges; ++i) {
                    if (px_ >= ledges_[i].x1 - 0.3f && px_ <= ledges_[i].x2 + 0.3f &&
                        fabsf((py_ + 1.0f) - ledges_[i].y) < 0.6f) {
                        supported = true;
                        break;
                    }
                }
                if (!supported) on_ground_ = false;
            }
        } else {
            uint16_t ctrl = keys_down | keys_pressed;
            if (ctrl & KEY_LEFT) vx_ -= 5.0f * dt;
            if (ctrl & KEY_RIGHT) vx_ += 5.0f * dt;

            vy_ += 20.0f * dt;
            if (vy_ > 16.0f) vy_ = 16.0f;

            float prev_foot = py_ + 1.0f;
            px_ += vx_ * dt;
            py_ += vy_ * dt;

            if (px_ < 0.5f) {
                px_ = 0.5f;
                if (vx_ < 0.0f) vx_ = 0.0f;
            }
            if (py_ < 1.0f) {
                py_ = 1.0f;
                if (vy_ < 0.0f) vy_ = 0.0f;
            }

            if (vy_ >= 0.0f) {
                float cur_foot = py_ + 1.0f;
                for (int i = 0; i < kNumLedges; ++i) {
                    if (px_ >= ledges_[i].x1 - 0.3f && px_ <= ledges_[i].x2 + 0.3f &&
                        prev_foot <= ledges_[i].y + 0.4f && cur_foot >= ledges_[i].y) {
                        py_ = ledges_[i].y - 1.0f;
                        vy_ = 0.0f;
                        vx_ *= 0.4f;
                        on_ground_ = true;
                        if (i == 1) {
                            checkpoint_x_ = 43.0f;
                            checkpoint_y_ = 10.0f;
                        }
                        break;
                    }
                }
            }
        }

        // Gem collection
        for (int i = 0; i < kNumGems; ++i) {
            if (!gems_[i].collected && hypotf(px_ - gems_[i].x, py_ - gems_[i].y) <= 1.6f) {
                gems_[i].collected = true;
                AddScore(50);
            }
        }

        // Mid-course checkpoint update
        if (px_ >= 42.5f && py_ < 13.0f && checkpoint_x_ < 40.0f) {
            checkpoint_x_ = 43.0f;
            checkpoint_y_ = 10.0f;
        }

        // Finish platform victory check (x >= 90)
        if (px_ >= kFinishX094 && py_ <= 13.5f) {
            AddScore(300);
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            return;
        }

        // Abyss lava check (y >= 15)
        if (py_ >= 15.0f) {
            LoseLife();
            return;
        }
    }
}

void Game094GrappleSwing::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    int cam_x = (int)roundf(px_ - 5.0f);
    if (cam_x < 0) cam_x = 0;
    if (cam_x > 84) cam_x = 84;

    // Deep canyon cavern sky + ceiling stone + bottom lava abyss
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (y == 0) {
                SetPx094(fb_rgb24, x, y, 50, 42, 62);
            } else if (y == 15) {
                bool wave = (((x + cam_x + (int)(anim_timer_ * 8.0f)) & 1) == 0);
                SetPx094(fb_rgb24, x, y, 255, wave ? 95 : 45, 15);
            } else {
                SetPx094(fb_rgb24, x, y, 14, 18 + y, 34 + y);
            }
        }
    }

    // Canyon stone ledges & glowing finish portal
    for (int i = 0; i < kNumLedges; ++i) {
        int x1 = (int)roundf(ledges_[i].x1) - cam_x;
        int x2 = (int)roundf(ledges_[i].x2) - cam_x;
        int ly = (int)roundf(ledges_[i].y);
        for (int sx = x1; sx <= x2; ++sx) {
            if (sx < 0 || sx >= 16) continue;
            if (i == 2) {
                SetPx094(fb_rgb24, sx, ly, 50, 240, 120);
                if (sx == (int)roundf(kFinishX094) - cam_x + 1) {
                    SetPx094(fb_rgb24, sx, ly - 1, 255, 225, 45);
                    SetPx094(fb_rgb24, sx, ly - 2, 255, 225, 45);
                }
            } else {
                SetPx094(fb_rgb24, sx, ly, 155, 110, 65);
            }
            for (int by = ly + 1; by < 15; ++by) {
                SetPx094(fb_rgb24, sx, by, 85, 58, 38);
            }
        }
    }

    // Floating bonus gems
    for (int i = 0; i < kNumGems; ++i) {
        if (gems_[i].collected) continue;
        int gx = (int)roundf(gems_[i].x) - cam_x;
        int gy = (int)roundf(gems_[i].y);
        SetPx094(fb_rgb24, gx, gy, 245, 75, 255);
    }

    // Overhead golden anchor nodes
    for (int i = 0; i < kNumAnchors; ++i) {
        int ax = (int)roundf(anchors_[i].x) - cam_x;
        int ay = (int)roundf(anchors_[i].y);
        SetPx094(fb_rgb24, ax, ay - 1, 110, 95, 80);
        if (latched_ && latched_anchor_ == i) {
            SetPx094(fb_rgb24, ax, ay, 140, 255, 255);
        } else {
            SetPx094(fb_rgb24, ax, ay, 255, 210, 35);
        }
    }

    // Active cyan grapple tether line
    if (latched_ && latched_anchor_ >= 0) {
        float ax = anchors_[latched_anchor_].x - (float)cam_x;
        float ay = anchors_[latched_anchor_].y;
        float sx = px_ - (float)cam_x;
        float sy = py_;
        for (int step = 1; step <= 10; ++step) {
            float t = (float)step / 10.0f;
            int rx = (int)roundf(ax + (sx - ax) * t);
            int ry = (int)roundf(ay + (sy - ay) * t);
            SetPx094(fb_rgb24, rx, ry, 70, 240, 255);
        }
    }

    // Player explorer sprite
    int psx = (int)roundf(px_) - cam_x;
    int psy = (int)roundf(py_);
    SetPx094(fb_rgb24, psx, psy, 255, 245, 220);
    SetPx094(fb_rgb24, psx, psy + 1, 55, 165, 255);

    // Lives HUD at top-left
    for (int i = 0; i < (int)lives_ && i < 3; ++i) {
        SetPx094(fb_rgb24, i * 2, 0, 80, 235, 255);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx094(fb_rgb24, 6, y, 250, 250, 250);
            SetPx094(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game094GrappleSwing::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    int prog = (int)((px_ / kFinishX094) * 100.0f);
    if (prog < 0) prog = 0;
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

static_assert(sizeof(Game094GrappleSwing) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
