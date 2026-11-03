#include "game_177_depthcharge.h"
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

Game177Depthcharge::Game177Depthcharge() {
    Reset();
}

void Game177Depthcharge::Init() {
    Reset();
}

void Game177Depthcharge::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game177Depthcharge::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 2.0f;
    speed_ = 6.0f;

    for (int i = 0; i < MAX_CHARGES; ++i) charges_[i].active = false;
    for (int i = 0; i < MAX_TORPEDOES; ++i) torpedoes_[i].active = false;

    subs_[0] = {0, 2.0f, 6.0f, 3.2f + stage_ * 0.3f, 0, true, 1.5f};
    subs_[1] = {1, 13.0f, 10.0f, -(2.4f + stage_ * 0.25f), 1, true, 2.2f};
    subs_[2] = {2, 5.0f, 14.0f, 1.8f + stage_ * 0.2f, 2, true, 3.0f};
}

uint8_t Game177Depthcharge::GetSubsAlive() const {
    uint8_t count = 0;
    for (int i = 0; i < NUM_SUBS; ++i) {
        if (subs_[i].alive) count++;
    }
    return count;
}

void Game177Depthcharge::CheckStageClear() {
    if (GetSubsAlive() == 0) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 2.0f;
        score_ += 1500;
    }
}

void Game177Depthcharge::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_SHIP_SUNK) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                for (int i = 0; i < MAX_CHARGES; ++i) charges_[i].active = false;
                for (int i = 0; i < MAX_TORPEDOES; ++i) torpedoes_[i].active = false;
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

    // Lateral movement
    if (buttons & BTN_LEFT)  px_ -= speed_ * dt;
    if (buttons & BTN_RIGHT) px_ += speed_ * dt;
    px_ = std::max(1.5f, std::min(14.5f, px_));

    // Drop Port Charge (Btn A)
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        for (int i = 0; i < MAX_CHARGES; ++i) {
            if (!charges_[i].active) {
                charges_[i] = {px_ - 0.8f, py_ + 0.8f, 5.5f, true};
                break;
            }
        }
    }

    // Drop Starboard Charge (Btn B)
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        for (int i = 0; i < MAX_CHARGES; ++i) {
            if (!charges_[i].active) {
                charges_[i] = {px_ + 0.8f, py_ + 0.8f, 5.5f, true};
                break;
            }
        }
    }

    // Update Charges
    for (int i = 0; i < MAX_CHARGES; ++i) {
        if (!charges_[i].active) continue;

        charges_[i].y += charges_[i].vy * dt;
        if (charges_[i].y >= 15.0f) {
            charges_[i].active = false;
            continue;
        }

        for (int s = 0; s < NUM_SUBS; ++s) {
            if (subs_[s].alive && std::hypot(subs_[s].x - charges_[i].x, subs_[s].y - charges_[i].y) < 1.1f) {
                subs_[s].alive = false;
                charges_[i].active = false;
                static const uint32_t tier_pts[] = {300, 200, 100};
                score_ += tier_pts[subs_[s].tier];
                CheckStageClear();
                break;
            }
        }
    }

    // Update Subs & Torpedoes
    for (int s = 0; s < NUM_SUBS; ++s) {
        if (!subs_[s].alive) continue;

        subs_[s].x += subs_[s].vx * dt;
        if (subs_[s].x > 14.5f) {
            subs_[s].x = 14.5f;
            subs_[s].vx = -std::abs(subs_[s].vx);
        } else if (subs_[s].x < 1.5f) {
            subs_[s].x = 1.5f;
            subs_[s].vx = std::abs(subs_[s].vx);
        }

        subs_[s].reload -= dt;
        if (subs_[s].reload <= 0.0f) {
            subs_[s].reload = std::max(1.5f, 3.5f - stage_ * 0.3f);
            for (int t = 0; t < MAX_TORPEDOES; ++t) {
                if (!torpedoes_[t].active) {
                    torpedoes_[t] = {subs_[s].x, subs_[s].y - 0.8f, -5.0f, true};
                    break;
                }
            }
        }
    }

    // Update Torpedoes
    for (int t = 0; t < MAX_TORPEDOES; ++t) {
        if (!torpedoes_[t].active) continue;

        torpedoes_[t].y += torpedoes_[t].vy * dt;
        if (torpedoes_[t].y < 1.0f) {
            torpedoes_[t].active = false;
            continue;
        }

        if (std::hypot(torpedoes_[t].x - px_, torpedoes_[t].y - py_) < 1.0f) {
            torpedoes_[t].active = false;
            lives_--;
            state_ = STATE_SHIP_SUNK;
            state_timer_ = 1.2f;
            return;
        }
    }
}

void Game177Depthcharge::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Sky
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 0, 40, 40, 80);
        set_pixel(x, 1, 60, 80, 120);
        set_pixel(x, 2, 0, 140, 200); // Water surface line
    }

    // Depth water gradient
    for (int y = 3; y < 16; ++y) {
        uint8_t b_val = static_cast<uint8_t>(std::max(30, 140 - (y - 3) * 8));
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 5, 20, b_val);
        }
    }

    // Submarines
    for (int s = 0; s < NUM_SUBS; ++s) {
        if (subs_[s].alive) {
            int sx = static_cast<int>(std::round(subs_[s].x));
            int sy = static_cast<int>(std::round(subs_[s].y));
            set_pixel(sx, sy, 180, 180, 40);
            set_pixel(sx - 1, sy, 140, 140, 30);
            set_pixel(sx + 1, sy, 140, 140, 30);
            set_pixel(sx, sy - 1, 220, 220, 80);
        }
    }

    // Charges
    for (int i = 0; i < MAX_CHARGES; ++i) {
        if (charges_[i].active) {
            int cx = static_cast<int>(std::round(charges_[i].x));
            int cy = static_cast<int>(std::round(charges_[i].y));
            set_pixel(cx, cy, 255, 120, 20);
        }
    }

    // Torpedoes
    for (int t = 0; t < MAX_TORPEDOES; ++t) {
        if (torpedoes_[t].active) {
            int tx = static_cast<int>(std::round(torpedoes_[t].x));
            int ty = static_cast<int>(std::round(torpedoes_[t].y));
            set_pixel(tx, ty, 255, 40, 40);
        }
    }

    // Destroyer
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 200, 210, 220);
        set_pixel(px - 1, py, 160, 170, 180);
        set_pixel(px + 1, py, 160, 170, 180);
        set_pixel(px, py - 1, 240, 240, 250);
        set_pixel(px - 1, py - 1, 220, 80, 0);
        set_pixel(px + 1, py - 1, 220, 80, 0);
    } else if (state_ == STATE_SHIP_SUNK) {
        set_pixel(px, py, 255, 100, 0);
        set_pixel(px - 1, py, 255, 0, 0);
        set_pixel(px + 1, py, 255, 0, 0);
    }
}

} // namespace arcade

