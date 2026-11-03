#include "game_116_lunarlander.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game116LunarLander::Game116LunarLander() {
    Reset();
}

void Game116LunarLander::Init() {
    Reset();
}

void Game116LunarLander::Reset() {
    score_ = 0;
    lives_ = 3;
    fuel_ = 450.0f;
    BuildTerrain();
    InitSite();
}

void Game116LunarLander::BuildTerrain() {
    // Terrain height map across 16 columns (11..15)
    // Jagged crater rims and designated flat pads:
    // Pad 0 (1X): columns 1, 2, 3 at y = 14
    // Pad 1 (3X): columns 7, 8 at y = 15
    // Pad 2 (5X): column 13 at y = 12

    terrain_y_[0] = 12;
    terrain_y_[1] = 14; terrain_y_[2] = 14; terrain_y_[3] = 14; // Pad 0 (1X)
    terrain_y_[4] = 13;
    terrain_y_[5] = 11;
    terrain_y_[6] = 13;
    terrain_y_[7] = 15; terrain_y_[8] = 15; // Pad 1 (3X)
    terrain_y_[9] = 14;
    terrain_y_[10] = 12;
    terrain_y_[11] = 11;
    terrain_y_[12] = 11;
    terrain_y_[13] = 12; // Pad 2 (5X)
    terrain_y_[14] = 13;
    terrain_y_[15] = 14;

    pads_[0] = {1, 3, 14, 1};
    pads_[1] = {7, 8, 15, 3};
    pads_[2] = {13, 13, 12, 5};
}

void Game116LunarLander::InitSite() {
    state_ = STATE_FLYING;
    state_timer_ = 0.0f;
    px_ = 8.0f;
    py_ = 1.5f;
    vx_ = 0.0f;
    vy_ = 0.0f;
    thrusting_ = false;
}

void Game116LunarLander::SetPositionAndVelocity(float x, float y, float vx, float vy) {
    px_ = x;
    py_ = y;
    vx_ = vx;
    vy_ = vy;
}

void Game116LunarLander::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_TOUCHDOWN_SAFE) {
        if (state_timer_ > 1.6f) {
            InitSite();
        }
        return;
    }

    if (state_ == STATE_CRASHED) {
        if (state_timer_ > 1.6f) {
            lives_--;
            if (lives_ <= 0 || fuel_ <= 0.0f) {
                state_ = STATE_GAME_OVER;
            } else {
                InitSite();
            }
        }
        return;
    }

    UpdatePhysics(dt, buttons);
    CheckTouchdown();
}

void Game116LunarLander::UpdatePhysics(float dt, uint32_t buttons) {
    float lunar_gravity = 1.6f;
    vy_ += lunar_gravity * dt;

    thrusting_ = false;

    // Main Engine Thrust (Button A or Up)
    if ((buttons & (BTN_A | BTN_UP)) && fuel_ > 0.0f) {
        thrusting_ = true;
        float main_thrust = 4.0f;
        vy_ -= main_thrust * dt;
        fuel_ -= 25.0f * dt;
    }

    // Lateral RCS Thrusters (Left / Right)
    if ((buttons & BTN_LEFT) && fuel_ > 0.0f) {
        vx_ -= 2.4f * dt;
        fuel_ -= 10.0f * dt;
    }
    if ((buttons & BTN_RIGHT) && fuel_ > 0.0f) {
        vx_ += 2.4f * dt;
        fuel_ -= 10.0f * dt;
    }

    if (fuel_ < 0.0f) fuel_ = 0.0f;

    // Apply Velocity
    px_ += vx_ * dt;
    py_ += vy_ * dt;

    // Boundary constraints
    if (px_ < 1.0f) { px_ = 1.0f; vx_ = 0.0f; }
    if (px_ > 14.0f) { px_ = 14.0f; vx_ = 0.0f; }
    if (py_ < 1.0f) { py_ = 1.0f; vy_ = 0.0f; }
}

void Game116LunarLander::CheckTouchdown() {
    int col = static_cast<int>(std::round(px_));
    if (col < 0) col = 0;
    if (col > 15) col = 15;

    int surface_y = terrain_y_[col];

    // Lander feet contact at py + 1.0
    if (py + 1.0f >= static_cast<float>(surface_y)) {
        py_ = static_cast<float>(surface_y) - 1.0f;

        // Check landing pad alignment
        int matched_pad = -1;
        for (int i = 0; i < NUM_PADS; ++i) {
            if (col >= pads_[i].x_start && col <= pads_[i].x_end && surface_y == pads_[i].y) {
                matched_pad = i;
                break;
            }
        }

        if (matched_pad >= 0) {
            // Landing on Pad: evaluate touchdown velocities
            if (std::abs(vy_) <= SAFE_MAX_VY && std::abs(vx_) <= SAFE_MAX_VX) {
                // Perfect soft landing!
                state_ = STATE_TOUCHDOWN_SAFE;
                state_timer_ = 0.0f;
                score_ += 100 * pads_[matched_pad].multiplier;
                fuel_ += 120.0f; // Bonus fuel
            } else {
                // Hard landing crash!
                state_ = STATE_CRASHED;
                state_timer_ = 0.0f;
            }
        } else {
            // Hit jagged crater rocks: crash!
            state_ = STATE_CRASHED;
            state_timer_ = 0.0f;
        }

        vx_ = 0.0f;
        vy_ = 0.0f;
    }
}

void Game116LunarLander::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Lunar Terrain & Designated Flat Landing Pads
    for (int x = 0; x < 16; ++x) {
        int ty = terrain_y_[x];
        // Surface crest
        set_pixel(x, ty, 80, 80, 95);
        // Sub-surface rock bedrock down to y=15
        for (int y = ty + 1; y < 16; ++y) {
            set_pixel(x, y, 40, 40, 50);
        }
    }

    // Highlight Landing Pads
    for (int i = 0; i < NUM_PADS; ++i) {
        for (int x = pads_[i].x_start; x <= pads_[i].x_end; ++x) {
            int py = pads_[i].y;
            if (pads_[i].multiplier == 1) {
                set_pixel(x, py, 40, 220, 60); // Green (1X)
            } else if (pads_[i].multiplier == 3) {
                set_pixel(x, py, 40, 200, 255); // Cyan (3X)
            } else {
                set_pixel(x, py, 255, 200, 30); // Gold (5X)
            }
        }
    }

    // 2. Lunar Lander
    int lx = static_cast<int>(std::round(px_));
    int ly = static_cast<int>(std::round(py_));

    if (state_ == STATE_FLYING || state_ == STATE_TOUCHDOWN_SAFE) {
        // Cockpit
        set_pixel(lx, ly, 255, 255, 255);
        // Left & right landing pads / legs
        set_pixel(lx - 1, ly + 1, 160, 180, 220);
        set_pixel(lx + 1, ly + 1, 160, 180, 220);

        // Rocket exhaust plume
        if (thrusting_) {
            set_pixel(lx, ly + 1, 255, 120, 20); // Orange main flame
            set_pixel(lx, ly + 2, 255, 220, 40); // Yellow spark
        }

        if (state_ == STATE_TOUCHDOWN_SAFE) {
            // Touchdown celebration glow
            set_pixel(lx, ly - 1, 40, 255, 80);
        }
    } else if (state_ == STATE_CRASHED) {
        // Explosion shrapnel
        set_pixel(lx, ly, 255, 60, 20);
        set_pixel(lx - 1, ly - 1, 255, 180, 0);
        set_pixel(lx + 1, ly + 1, 255, 220, 50);
        set_pixel(lx + 1, ly - 1, 255, 60, 20);
    }

    // 3. HUD: Fuel Gauge on top row (y = 0)
    int fuel_bars = static_cast<int>((fuel_ / 450.0f) * 10.0f);
    if (fuel_bars > 10) fuel_bars = 10;
    for (int f = 0; f < fuel_bars; ++f) {
        if (fuel_bars > 5) {
            set_pixel(f, 0, 40, 220, 80); // Green fuel
        } else if (fuel_bars > 2) {
            set_pixel(f, 0, 255, 200, 30); // Yellow caution
        } else {
            set_pixel(f, 0, 255, 40, 20); // Red critical
        }
    }

    // Lives on top right (y = 0, x = 13..15)
    for (int l = 0; l < lives_; ++l) {
        set_pixel(15 - l, 0, 255, 255, 255);
    }
}

} // namespace arcade
