#include "game_180_clowns.h"
#include <cstring>
#include <cmath>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = (1 << 0);
static constexpr uint16_t BTN_DOWN  = (1 << 1);
static constexpr uint16_t BTN_LEFT  = (1 << 2);
static constexpr uint16_t BTN_RIGHT = (1 << 3);
static constexpr uint16_t BTN_A     = (1 << 4);
static constexpr uint16_t BTN_B     = (1 << 5);

Game180Clowns::Game180Clowns() {
    Reset();
}

void Game180Clowns::Init() {
    Reset();
}

void Game180Clowns::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

bool Game180Clowns::IsBalloon(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return false;
    int idx = y * 16 + x;
    return (balloon_mask_[idx / 8] & (1 << (idx % 8))) != 0;
}

void Game180Clowns::RemoveBalloon(int x, int y) {
    if (IsBalloon(x, y)) {
        int idx = y * 16 + x;
        balloon_mask_[idx / 8] &= ~(1 << (idx % 8));
        if (balloons_left_ > 0) balloons_left_--;
    }
}

void Game180Clowns::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    sx_ = 7.5f;
    seesaw_tilt_ = -1;
    seesaw_speed_ = 7.5f;

    ax_ = 4.0f;
    ay_ = 4.0f;
    avx_ = 2.5f;
    avy_ = 0.0f;
    gravity_ = 16.0f;

    std::memset(balloon_mask_, 0, sizeof(balloon_mask_));
    balloons_left_ = 0;

    for (int y = 1; y <= 3; ++y) {
        for (int x = 2; x <= 13; ++x) {
            int idx = y * 16 + x;
            balloon_mask_[idx / 8] |= (1 << (idx % 8));
            balloons_left_++;
        }
    }
}

void Game180Clowns::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_ACROBAT_SPLAT) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                ax_ = 4.0f;
                ay_ = 4.0f;
                avx_ = 2.5f;
                avy_ = 0.0f;
                seesaw_tilt_ = -1;
            } else {
                state_ = STATE_GAME_OVER;
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if (((buttons & BTN_A) && !(prev_buttons & BTN_A)) ||
            ((buttons & BTN_B) && !(prev_buttons & BTN_B))) {
            Reset();
        }
        return;
    }

    // Seesaw movement
    if (buttons & BTN_LEFT)  sx_ -= seesaw_speed_ * dt;
    if (buttons & BTN_RIGHT) sx_ += seesaw_speed_ * dt;
    sx_ = std::max(2.5f, std::min(12.5f, sx_));

    float boost = ((buttons & BTN_A) && !(prev_buttons & BTN_A)) ? 1.2f : 1.0f;

    // Acrobat physics
    avy_ += gravity_ * dt;
    ax_ += avx_ * dt;
    ay_ += avy_ * dt;

    if (ax_ <= 1.0f) { ax_ = 1.0f; avx_ = std::abs(avx_); }
    else if (ax_ >= 14.0f) { ax_ = 14.0f; avx_ = -std::abs(avx_); }

    if (ay_ <= 0.5f) { ay_ = 0.5f; avy_ = std::abs(avy_); }

    // Balloons
    int bx = static_cast<int>(std::round(ax_));
    int by = static_cast<int>(std::round(ay_));
    if (IsBalloon(bx, by)) {
        RemoveBalloon(bx, by);
        if (by == 1) score_ += 50;
        else if (by == 2) score_ += 30;
        else score_ += 10;
        avy_ = std::abs(avy_) * 0.8f;

        if (balloons_left_ == 0) {
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 2.0f;
            score_ += 2500;
            return;
        }
    }

    // Landing on Seesaw
    if (ay_ >= 13.5f && avy_ > 0.0f) {
        if (std::abs(ax_ - sx_) <= 1.5f) {
            float offset = (ax_ - sx_) / 1.5f;
            ay_ = 13.2f;
            avy_ = -(13.0f + stage_ * 0.5f) * boost;
            avx_ = offset * 6.0f;
            seesaw_tilt_ = -seesaw_tilt_;
            score_ += 20;
        } else if (ay_ >= 15.0f) {
            lives_--;
            state_ = STATE_ACROBAT_SPLAT;
            state_timer_ = 1.2f;
            return;
        }
    }
}

void Game180Clowns::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Floor
    for (int x = 0; x < 16; ++x) set_pixel(x, 15, 60, 40, 20);

    // Balloons
    for (int y = 1; y <= 3; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsBalloon(x, y)) {
                if (y == 1) set_pixel(x, y, 40, 120, 255);
                else if (y == 2) set_pixel(x, y, 40, 220, 60);
                else set_pixel(x, y, 255, 230, 40);
            }
        }
    }

    // Seesaw
    int sx = static_cast<int>(std::round(sx_));
    set_pixel(sx, 14, 255, 200, 0); // Pivot
    if (seesaw_tilt_ == -1) {
        set_pixel(sx - 1, 14, 200, 160, 20);
        set_pixel(sx + 1, 13, 200, 160, 20);
        set_pixel(sx + 1, 12, 255, 60, 60);
        set_pixel(sx + 1, 11, 255, 220, 140);
    } else {
        set_pixel(sx - 1, 13, 200, 160, 20);
        set_pixel(sx + 1, 14, 200, 160, 20);
        set_pixel(sx - 1, 12, 255, 60, 60);
        set_pixel(sx - 1, 11, 255, 220, 140);
    }

    // Airborne acrobat
    int ax = static_cast<int>(std::round(ax_));
    int ay = static_cast<int>(std::round(ay_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(ax, ay, 255, 255, 255);
        set_pixel(ax, ay - 1, 40, 180, 255);
        set_pixel(ax - 1, ay, 255, 60, 60);
        set_pixel(ax + 1, ay, 255, 60, 60);
    } else if (state_ == STATE_ACROBAT_SPLAT) {
        set_pixel(ax, 15, 255, 80, 0);
        set_pixel(ax - 1, 15, 255, 0, 0);
        set_pixel(ax + 1, 15, 255, 0, 0);
    }
}

} // namespace arcade
