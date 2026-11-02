#include "game_094_crashboys.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game094CrashBoys::Game094CrashBoys() {
    Init();
}

void Game094CrashBoys::Init() {
    ResetEvent(true);
}

void Game094CrashBoys::Reset() {
    ResetEvent(true);
}

void Game094CrashBoys::ResetEvent(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        round_ = 1;
    }
    state_ = STATE_RUNNING;
    state_timer_ = 0.0f;
    rivals_defeated_ = 0;

    px_ = 3.0f;
    py_ = 13.0f;
    run_speed_ = 6.0f;
    pole_flex_ = 0.0f;
    air_vx_ = 0.0f;
    air_vy_ = 0.0f;
    is_dropkicking_ = false;

    distance_ = 0.0f;
    stage_length_ = 300.0f + round_ * 80.0f;
    next_gap_dist_ = 50.0f;
    gap_width_ = 18.0f;

    for (int i = 0; i < MAX_RIVALS; ++i) {
        rivals_[i].active = true;
        rivals_[i].knocked_down = false;
        rivals_[i].x = 6.0f + i * 4.0f;
        rivals_[i].y = 13.0f;
        rivals_[i].vx = 5.2f + (i * 0.8f);
    }
}

void Game094CrashBoys::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_HERO_FALL) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetEvent(false);
            }
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.0f) {
            round_++;
            ResetEvent(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetEvent(true);
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateRivals(dt);
    CheckAirCombat();

    if (distance_ >= stage_length_) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1500;
    }
}

void Game094CrashBoys::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (state_ == STATE_RUNNING) {
        // Accelerate with Right
        if (buttons & BTN_RIGHT) {
            run_speed_ = std::min(10.5f, run_speed_ + 12.0f * dt);
        } else if (buttons & BTN_LEFT) {
            run_speed_ = std::max(4.0f, run_speed_ - 8.0f * dt);
        }

        distance_ += run_speed_ * dt;

        // Check if hero ran off rooftop into gap without vaulting
        if (distance_ >= next_gap_dist_ && distance_ <= next_gap_dist_ + gap_width_) {
            state_ = STATE_HERO_FALL;
            state_timer_ = 0.0f;
            return;
        }

        // Button B: Plant Vaulting Pole
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            state_ = STATE_VAULTING;
            pole_flex_ = 0.1f;
        }
    } else if (state_ == STATE_VAULTING) {
        // Bend the pole while Button B is held
        if (buttons & BTN_B) {
            pole_flex_ = std::min(1.0f, pole_flex_ + 2.4f * dt);
            // Hero continues moving forward while planting pole
            distance_ += (run_speed_ * 0.4f) * dt;
        }

        // Release Button B or tap Button A: Launch into air!
        if (!(buttons & BTN_B) || ((buttons & BTN_A) && !(prev_buttons & BTN_A))) {
            state_ = STATE_AIRBORNE;
            air_vx_ = run_speed_ * (0.8f + pole_flex_ * 0.7f);
            air_vy_ = -(6.5f + pole_flex_ * 7.5f);
            score_ += (int)(pole_flex_ * 100);
            is_dropkicking_ = false;
        }
    } else if (state_ == STATE_AIRBORNE) {
        air_vy_ += 14.5f * dt;
        py_ += air_vy_ * dt;
        distance_ += air_vx_ * dt;

        // Button A in mid-air: Aerial Dropkick!
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            is_dropkicking_ = true;
            air_vx_ += 1.8f;
        }

        // Landing check when descending
        if (air_vy_ >= 0.0f && py_ >= 13.0f) {
            py_ = 13.0f;
            // Check if landed inside alley gap
            if (distance_ >= next_gap_dist_ && distance_ <= next_gap_dist_ + gap_width_) {
                // Fell into gap!
                state_ = STATE_HERO_FALL;
                state_timer_ = 0.0f;
            } else {
                // Safely landed on next rooftop!
                state_ = STATE_RUNNING;
                score_ += 200;
                is_dropkicking_ = false;
                next_gap_dist_ = distance_ + 65.0f + (rand() % 35);
            }
        }
    }
}

void Game094CrashBoys::UpdateRivals(float dt) {
    for (int i = 0; i < MAX_RIVALS; ++i) {
        Rival& r = rivals_[i];
        if (!r.active) continue;

        if (r.knocked_down) {
            r.y += 12.0f * dt;
            if (r.y > 18.0f) {
                r.active = false;
            }
            continue;
        }

        r.x += (r.vx - run_speed_) * dt;
        if (r.x < -3.0f) {
            r.x = 18.0f;
        } else if (r.x > 18.0f) {
            r.x = -2.0f;
        }
    }
}

void Game094CrashBoys::CheckAirCombat() {
    for (int i = 0; i < MAX_RIVALS; ++i) {
        Rival& r = rivals_[i];
        if (!r.active || r.knocked_down) continue;

        float dx = std::fabs(r.x - px_);
        float dy = std::fabs(r.y - py_);

        if (dx < 1.3f && dy < 1.4f) {
            if (is_dropkicking_ || state_ == STATE_AIRBORNE) {
                // Mid-air kick or vault collision knocks rival off building!
                r.knocked_down = true;
                score_ += 300;
                rivals_defeated_++;
            }
        }
    }
}

void Game094CrashBoys::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Sunset Skyline
    for (int y = 0; y < 10; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 160 + y * 6, 70 + y * 4, 30);
        }
    }

    // Distant skyscraper silhouettes (y=7 to 9)
    for (int x = 0; x < 16; ++x) {
        if ((x % 4) != 0) {
            set_pixel(x, 7, 50, 40, 60);
            set_pixel(x, 8, 50, 40, 60);
            set_pixel(x, 9, 50, 40, 60);
        }
    }

    // Rooftop Surface (y=14 and 15)
    // Check if current view is over an alley gap
    bool is_in_gap = (distance_ >= next_gap_dist_ && distance_ <= next_gap_dist_ + gap_width_);

    for (int y = 14; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (is_in_gap && x >= 4 && x <= 12) {
                // Black alley void
                set_pixel(x, y, 10, 10, 15);
            } else {
                // Dark gray concrete rooftop
                set_pixel(x, y, 70, 75, 80);
            }
        }
    }

    // Rooftop Antennas & Vents
    set_pixel(1, 13, 140, 140, 140);
    set_pixel(14, 13, 180, 80, 40);

    // Render Rivals
    for (int i = 0; i < MAX_RIVALS; ++i) {
        const Rival& r = rivals_[i];
        if (!r.active) continue;

        int rx = (int)std::round(r.x);
        int ry = (int)std::round(r.y);

        if (r.knocked_down) {
            set_pixel(rx, ry, 40, 80, 220); // Blue athlete tumbling down
            set_pixel(rx, ry - 1, 255, 200, 140);
        } else {
            set_pixel(rx, ry, 40, 80, 220); // Blue tracksuit
            set_pixel(rx, ry - 1, 255, 200, 140);
            set_pixel(rx - 1, ry - 1, 40, 80, 220); // arms
        }
    }

    // Render Hero (Kunio / Crash)
    int px = (int)std::round(px_);
    int py = (int)std::round(py_);

    if (state_ == STATE_HERO_FALL) {
        set_pixel(px, py, 255, 50, 50);
        set_pixel(px, py - 1, 255, 220, 0);
    } else if (state_ == STATE_VAULTING) {
        // Bending bamboo pole
        int bend_x = px + 1 + (int)std::round(pole_flex_ * 2.0f);
        set_pixel(bend_x, py, 220, 180, 80);
        set_pixel(px, py - 1, 255, 255, 255); // White uniform
        set_pixel(px, py - 2, 255, 200, 140); // Face
        set_pixel(px, py, 220, 40, 40);       // Red shorts
    } else if (state_ == STATE_AIRBORNE) {
        if (is_dropkicking_) {
            // Extended aerial dropkick pose
            set_pixel(px, py, 255, 255, 255);
            set_pixel(px + 1, py, 220, 40, 40);   // Extended kicking foot
            set_pixel(px + 2, py, 255, 220, 0);   // Kick spark
            set_pixel(px - 1, py - 1, 255, 200, 140);
        } else {
            // High altitude leap
            set_pixel(px, py, 220, 40, 40);
            set_pixel(px, py - 1, 255, 255, 255);
            set_pixel(px, py - 2, 255, 200, 140);
        }
    } else {
        // Sprinting on rooftop
        set_pixel(px, py, 220, 40, 40);
        set_pixel(px, py - 1, 255, 255, 255);
        set_pixel(px, py - 2, 255, 200, 140);
        set_pixel(px + 1, py - 1, 220, 180, 80); // Carrying pole
    }

    // Top HUD
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 255, 60, 60);
    }
    int flex_bars = (int)(pole_flex_ * 4.0f);
    for (int f = 0; f < flex_bars; ++f) {
        set_pixel(15 - f, 0, 255, 220, 0);
    }
}

} // namespace arcade
