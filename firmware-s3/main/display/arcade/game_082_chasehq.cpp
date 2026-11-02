#include "game_082_chasehq.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace arcade {

Game082ChaseHQ::Game082ChaseHQ() {
    Reset();
}

void Game082ChaseHQ::Init() {
    Reset();
}

void Game082ChaseHQ::Reset() {
    state_ = STATE_APPROACH;
    state_timer_ = 0.0f;
    time_remaining_ = 45.0f;
    score_ = 0;
    turbos_left_ = 3;
    turbo_timer_ = 0.0f;
    suspect_damage_ = 0.0f;
    distance_to_suspect_ = 100.0f;
    ResetMission();
}

void Game082ChaseHQ::ResetMission() {
    px_ = 7.5f;
    py_ = 13.0f;
    p_speed_ = 11.0f;

    sx_ = 7.5f;
    sy_ = 6.0f;
    s_speed_ = 9.0f;
    s_swerve_timer_ = 0.0f;

    for (int i = 0; i < MAX_TRAFFIC; ++i) {
        traffic_[i].active = false;
    }
}

void Game082ChaseHQ::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_ARRESTED || state_ == STATE_TIME_UP) {
        if (state_timer_ > 2.5f && (buttons & (BUTTON_A | BUTTON_B))) {
            Reset();
        }
        return;
    }

    time_remaining_ = std::max(0.0f, time_remaining_ - dt);
    if (time_remaining_ <= 0.0f) {
        state_ = STATE_TIME_UP;
        state_timer_ = 0.0f;
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);

    if (state_ == STATE_APPROACH) {
        distance_to_suspect_ -= (p_speed_ - 8.0f) * dt * 2.0f;
        score_ += static_cast<int>(p_speed_ * dt * 5.0f);

        if (distance_to_suspect_ <= 0.0f) {
            state_ = STATE_PURSUIT;
            state_timer_ = 0.0f;
            time_remaining_ += 25.0f; // Mission extension!
            score_ += 2000;
        }
    } else if (state_ == STATE_PURSUIT) {
        UpdateSuspect(dt);
        CheckRamming();
    }

    UpdateTraffic(dt);
    road_scroll_ += p_speed_ * dt;
}

void Game082ChaseHQ::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Steering
    float steer_speed = 7.5f;
    if (buttons & BUTTON_LEFT)  px_ -= steer_speed * dt;
    if (buttons & BUTTON_RIGHT) px_ += steer_speed * dt;

    px_ = std::max(2.0f, std::min(13.0f, px_));

    // Turbo Boost (Button B)
    if (turbo_timer_ > 0.0f) {
        turbo_timer_ -= dt;
        p_speed_ = 20.0f;
    } else {
        if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B) && turbos_left_ > 0) {
            turbos_left_--;
            turbo_timer_ = 2.5f;
            p_speed_ = 20.0f;
        } else if (buttons & BUTTON_A) {
            p_speed_ = 12.0f;
        } else {
            p_speed_ = 9.0f;
        }
    }
}

void Game082ChaseHQ::UpdateSuspect(float dt) {
    s_swerve_timer_ += dt;
    if (s_swerve_timer_ > 0.8f) {
        s_swerve_timer_ = 0.0f;
        // Aggressive swerving
        float target_dir = (std::rand() % 2 == 0) ? -1.0f : 1.0f;
        sx_ += target_dir * 1.5f;
        sx_ = std::max(3.0f, std::min(12.0f, sx_));
    }

    // Suspect tries to stay ahead around y = 6..8
    float speed_diff = p_speed_ - s_speed_;
    sy_ += speed_diff * 0.1f * dt;
    sy_ = std::max(5.0f, std::min(10.0f, sy_));
}

void Game082ChaseHQ::CheckRamming() {
    float dx = std::abs(px_ - sx_);
    float dy = std::abs(py_ - sy_);

    // Ramming collision
    if (dx < 1.6f && dy < 1.6f) {
        float dmg = (turbo_timer_ > 0.0f) ? 25.0f : 15.0f;
        suspect_damage_ = std::min(100.0f, suspect_damage_ + dmg);
        score_ += static_cast<int>(dmg * 100.0f);

        // Rebound displacement
        if (px_ < sx_) {
            px_ -= 0.6f;
            sx_ += 0.6f;
        } else {
            px_ += 0.6f;
            sx_ -= 0.6f;
        }

        if (suspect_damage_ >= 100.0f) {
            state_ = STATE_ARRESTED;
            state_timer_ = 0.0f;
            score_ += 10000;
        }
    }
}

void Game082ChaseHQ::UpdateTraffic(float dt) {
    for (int i = 0; i < MAX_TRAFFIC; ++i) {
        if (!traffic_[i].active) {
            if (std::rand() % 60 == 0) {
                traffic_[i].active = true;
                traffic_[i].x = 3.0f + (std::rand() % 10);
                traffic_[i].y = 4.0f;
                traffic_[i].speed = 5.0f;
            }
            continue;
        }

        // Relative motion toward player
        traffic_[i].y += (p_speed_ - traffic_[i].speed) * 0.6f * dt;

        // Player hits civilian traffic car -> spin out slowdown
        if (std::abs(traffic_[i].x - px_) < 1.4f && std::abs(traffic_[i].y - py_) < 1.2f) {
            traffic_[i].active = false;
            p_speed_ = 4.0f; // crash slowdown penalty!
            turbo_timer_ = 0.0f;
        }

        if (traffic_[i].y > 15.0f) {
            traffic_[i].active = false;
        }
    }
}

void Game082ChaseHQ::Render(uint8_t* fb) {
    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Horizon & Night City Skyline (y: 0..3)
    for (int y = 0; y < 4; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 10, 20, 40);
        }
    }

    // 2. Highway Asphalt (y: 4..15)
    for (int y = 4; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 50, 50, 55);
        }
    }

    // 3. Scrolling Highway Curbs & Striped Edges
    int scroll_offset = static_cast<int>(road_scroll_) % 4;
    for (int y = 4; y < 16; ++y) {
        bool stripe = ((y + scroll_offset) % 4 < 2);
        // Left grass/curb
        set_pixel(0, y, stripe ? 255 : 20, stripe ? 30 : 120, 20);
        set_pixel(1, y, stripe ? 255 : 20, stripe ? 30 : 120, 20);
        // Right grass/curb
        set_pixel(14, y, stripe ? 255 : 20, stripe ? 30 : 120, 20);
        set_pixel(15, y, stripe ? 255 : 20, stripe ? 30 : 120, 20);
        // Center dashed line (x = 7 or 8)
        if (stripe) {
            set_pixel(7, y, 255, 255, 100);
            set_pixel(8, y, 255, 255, 100);
        }
    }

    // 4. Civilian Traffic Cars
    for (int i = 0; i < MAX_TRAFFIC; ++i) {
        if (!traffic_[i].active) continue;
        int tx = static_cast<int>(std::round(traffic_[i].x));
        int ty = static_cast<int>(std::round(traffic_[i].y));
        set_pixel(tx, ty, 200, 200, 200);     // Grey sedan
        set_pixel(tx, ty - 1, 150, 150, 160);
        set_pixel(tx - 1, ty, 255, 30, 30);   // Tail lights
        set_pixel(tx + 1, ty, 255, 30, 30);
    }

    // 5. Suspect Vehicle (In PURSUIT mode: Red/Black Sports Coupe)
    if (state_ == STATE_PURSUIT || state_ == STATE_ARRESTED) {
        int sx = static_cast<int>(std::round(sx_));
        int sy = static_cast<int>(std::round(sy_));
        set_pixel(sx, sy, 220, 30, 30);       // Red body
        set_pixel(sx, sy - 1, 20, 20, 20);    // Black roof
        set_pixel(sx - 1, sy, 255, 50, 50);
        set_pixel(sx + 1, sy, 255, 50, 50);

        if (state_ == STATE_ARRESTED || suspect_damage_ > 60.0f) {
            // Smoke / Fire particles
            set_pixel(sx, sy - 2, 80, 80, 80);
            set_pixel(sx + 1, sy - 2, 255, 120, 0);
        }
    }

    // 6. Police Cruiser (Porsche 928)
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));

    set_pixel(px, py, 20, 20, 20);         // Black lower chassis
    set_pixel(px, py - 1, 240, 240, 245);  // White police hood/roof
    set_pixel(px - 1, py, 20, 20, 20);
    set_pixel(px + 1, py, 20, 20, 20);

    // Flashing Red & Blue Police Lightbar on top
    bool siren_flash = (static_cast<int>(state_timer_ * 8.0f) % 2 == 0);
    set_pixel(px - 1, py - 1, siren_flash ? 255 : 20, 20, siren_flash ? 20 : 255);
    set_pixel(px + 1, py - 1, siren_flash ? 20 : 255, 20, siren_flash ? 255 : 20);

    // Turbo flames
    if (turbo_timer_ > 0.0f) {
        set_pixel(px - 1, py + 1, 255, 140, 0);
        set_pixel(px + 1, py + 1, 255, 140, 0);
    }

    // 7. HUD (y = 0)
    // Turbo Boost dots (left side)
    for (int t = 0; t < turbos_left_; ++t) {
        set_pixel(t * 2, 0, 255, 200, 0);
    }

    // Suspect Damage Meter (right side in pursuit)
    if (state_ == STATE_PURSUIT) {
        int dmg_bars = static_cast<int>((suspect_damage_ / 100.0f) * 6.0f);
        for (int d = 0; d < dmg_bars; ++d) {
            set_pixel(15 - d, 0, 255, 30, 30);
        }
    }
}

} // namespace arcade
