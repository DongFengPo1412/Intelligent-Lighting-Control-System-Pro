#include "game_121_spacetaxi.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game121SpaceTaxi::Game121SpaceTaxi() {
    Reset();
}

void Game121SpaceTaxi::Init() {
    Reset();
}

void Game121SpaceTaxi::Reset() {
    score_ = 0;
    lives_ = 3;
    fares_completed_ = 0;
    InitPads();
    InitLevel();
}

void Game121SpaceTaxi::InitPads() {
    pads_[0] = {1, 1, 3, 14};   // Pad 1 (Bottom Left)
    pads_[1] = {2, 12, 14, 14}; // Pad 2 (Bottom Right)
    pads_[2] = {3, 1, 3, 6};    // Pad 3 (Top Left)
    pads_[3] = {4, 12, 14, 6};  // Pad 4 (Top Right)
}

void Game121SpaceTaxi::InitLevel() {
    state_ = STATE_FLYING;
    state_timer_ = 0.0f;
    fuel_ = 100.0f;

    px_ = 2.0f;
    py_ = 13.0f;
    vx_ = 0.0f;
    vy_ = 0.0f;
    gear_deployed_ = true;
    thrust_up_ = false;
    thrust_left_ = false;
    thrust_right_ = false;

    SpawnPassenger();
}

void Game121SpaceTaxi::SpawnPassenger() {
    int start_p = (fares_completed_ % NUM_PADS) + 1;
    int end_p = ((start_p + 1) % NUM_PADS) + 1;
    if (end_p == start_p) end_p = (start_p % NUM_PADS) + 1;

    passenger_.current_pad = start_p;
    passenger_.target_pad = end_p;
    passenger_.in_taxi = false;
    passenger_.delivered = false;
}

void Game121SpaceTaxi::ToggleGear() {
    gear_deployed_ = !gear_deployed_;
}

void Game121SpaceTaxi::SetPositionAndVelocity(float x, float y, float vx, float vy) {
    px_ = x;
    py_ = y;
    vx_ = vx;
    vy_ = vy;
}

void Game121SpaceTaxi::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_BOARDING) {
        if (state_timer_ > 1.2f) {
            state_ = STATE_FLYING;
            passenger_.in_taxi = true;
        }
        return;
    }

    if (state_ == STATE_FARE_PAID) {
        if (state_timer_ > 1.5f) {
            InitLevel();
        }
        return;
    }

    if (state_ == STATE_CRASHED) {
        if (state_timer_ > 1.4f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
            } else {
                InitLevel();
            }
        }
        return;
    }

    UpdatePhysics(dt, buttons, prev_buttons);
    CheckPadLanding();
}

void Game121SpaceTaxi::UpdatePhysics(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float city_gravity = 1.8f;
    vy_ += city_gravity * dt;

    thrust_up_ = false;
    thrust_left_ = false;
    thrust_right_ = false;

    // Up Lift Thruster
    if ((buttons & BTN_UP) && fuel_ > 0.0f) {
        thrust_up_ = true;
        vy_ -= 4.2f * dt;
        fuel_ -= 6.0f * dt;
    }

    // Turbo Pulse
    if ((buttons & BTN_A) && fuel_ > 0.0f) {
        thrust_up_ = true;
        vy_ -= 6.5f * dt;
        fuel_ -= 12.0f * dt;
    }

    // RCS Lateral Thrusters
    if ((buttons & BTN_LEFT) && fuel_ > 0.0f) {
        thrust_left_ = true;
        vx_ -= 3.2f * dt;
        fuel_ -= 4.0f * dt;
    }
    if ((buttons & BTN_RIGHT) && fuel_ > 0.0f) {
        thrust_right_ = true;
        vx_ += 3.2f * dt;
        fuel_ -= 4.0f * dt;
    }

    // Toggle Landing Gear (Button B or Down)
    if ((buttons & (BTN_B | BTN_DOWN)) && !(prev_buttons & (BTN_B | BTN_DOWN))) {
        ToggleGear();
    }

    // Air drag
    vx_ *= (1.0f - 0.4f * dt);

    px_ += vx_ * dt;
    py_ += vy_ * dt;

    // Outer screen boundaries
    if (px_ < 1.0f) { px_ = 1.0f; vx_ = 0.0f; }
    if (px_ > 14.5f) { px_ = 14.5f; vx_ = 0.0f; }
    if (py_ < 1.0f) { py_ = 1.0f; vy_ = 0.0f; }

    // Central Core obstacle: x in 6..9, y in 4..11
    if (px_ >= 5.5f && px_ <= 9.5f && py_ >= 4.0f && py_ <= 11.5f) {
        // Crash into skyscraper core!
        state_ = STATE_CRASHED;
        state_timer_ = 0.0f;
    }
}

void Game121SpaceTaxi::CheckPadLanding() {
    int col = static_cast<int>(std::round(px_));

    for (int i = 0; i < NUM_PADS; ++i) {
        if (col >= pads_[i].x_start && col <= pads_[i].x_end) {
            float pad_y = static_cast<float>(pads_[i].y);
            // Touchpad detection
            if (py_ >= pad_y - 1.2f && py_ <= pad_y + 0.2f && vy_ >= 0.0f) {
                py_ = pad_y - 1.0f;

                // Check gear & velocity
                if (!gear_deployed_ || std::abs(vy_) > 1.4f || std::abs(vx_) > 0.9f) {
                    // Crashed on landing!
                    state_ = STATE_CRASHED;
                    state_timer_ = 0.0f;
                } else {
                    // Safe Soft Docking!
                    vx_ = 0.0f;
                    vy_ = 0.0f;

                    if (!passenger_.in_taxi && pads_[i].id == passenger_.current_pad) {
                        // Boarding Passenger
                        state_ = STATE_BOARDING;
                        state_timer_ = 0.0f;
                        score_ += 50;
                    } else if (passenger_.in_taxi && pads_[i].id == passenger_.target_pad) {
                        // Successful Delivery!
                        state_ = STATE_FARE_PAID;
                        state_timer_ = 0.0f;
                        fares_completed_++;
                        score_ += 250 + static_cast<int>(fuel_) * 2;
                    }
                }
                break;
            }
        }
    }
}

void Game121SpaceTaxi::Render(uint8_t* fb) {
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

    // 1. Skyscraper Core Obstacle (x in 6..9, y in 4..11)
    for (int y = 4; y <= 11; ++y) {
        for (int x = 6; x <= 9; ++x) {
            set_pixel(x, y, 60, 60, 75); // Dark skyscraper window concrete
            if ((x + y) % 2 == 0) set_pixel(x, y, 100, 120, 140);
        }
    }

    // 2. Landing Pads
    for (int i = 0; i < NUM_PADS; ++i) {
        for (int x = pads_[i].x_start; x <= pads_[i].x_end; ++x) {
            set_pixel(x, pads_[i].y, 40, 220, 80); // Green landing surface
            set_pixel(x, pads_[i].y + 1, 30, 100, 40);
        }
    }

    // 3. Passenger Waiting on Pad
    if (!passenger_.in_taxi && state_ != STATE_FARE_PAID) {
        int pad_idx = passenger_.current_pad - 1;
        int px = pads_[pad_idx].x_start + 1;
        int py = pads_[pad_idx].y - 1;
        set_pixel(px, py, 255, 60, 200);     // Magenta passenger coat
        set_pixel(px, py - 1, 255, 200, 140); // Flesh head waving
    }

    // 4. Space Taxi
    int tx = static_cast<int>(std::round(px_));
    int ty = static_cast<int>(std::round(py_));

    if (state_ == STATE_FLYING || state_ == STATE_BOARDING || state_ == STATE_FARE_PAID) {
        // Yellow Taxi body
        set_pixel(tx, ty, 255, 220, 0);
        set_pixel(tx - 1, ty, 255, 200, 0);
        set_pixel(tx + 1, ty, 255, 200, 0);

        // Roof Checker / Taxi Sign
        set_pixel(tx, ty - 1, 40, 40, 40);

        // Landing Gear
        if (gear_deployed_) {
            set_pixel(tx - 1, ty + 1, 220, 220, 240); // Left strut
            set_pixel(tx + 1, ty + 1, 220, 220, 240); // Right strut
        }

        // Thruster flames
        if (thrust_up_) {
            set_pixel(tx, ty + 1, 0, 220, 255); // Cyan rocket flame
        }
        if (thrust_left_) {
            set_pixel(tx + 2, ty, 255, 120, 20); // Right thruster plume
        }
        if (thrust_right_) {
            set_pixel(tx - 2, ty, 255, 120, 20); // Left thruster plume
        }
    } else if (state_ == STATE_CRASHED) {
        set_pixel(tx, ty, 255, 40, 20);
        set_pixel(tx - 1, ty - 1, 255, 180, 0);
        set_pixel(tx + 1, ty + 1, 255, 220, 50);
        set_pixel(tx + 1, ty - 1, 255, 60, 20);
    }

    // 5. HUD: Target Pad & Gear status on top row
    // Gear indicator at x=0 (Green = Down/Safe, Red = Up)
    if (gear_deployed_) set_pixel(0, 0, 40, 255, 80);
    else set_pixel(0, 0, 255, 40, 20);

    // Fuel indicator (x = 2..8)
    int f_bars = static_cast<int>((fuel_ / 100.0f) * 6.0f);
    for (int f = 0; f < f_bars; ++f) {
        set_pixel(2 + f, 0, 0, 200, 255);
    }

    // Target pad indicator (x = 10..13)
    int target = passenger_.in_taxi ? passenger_.target_pad : passenger_.current_pad;
    set_pixel(10 + target, 0, 255, 220, 0);

    // Lives (x = 15)
    for (int l = 0; l < lives_; ++l) {
        set_pixel(15, l, 255, 255, 255);
    }
}

} // namespace arcade
