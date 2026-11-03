#include "game_147_crazyballoon.h"
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = (1 << 0);
static constexpr uint16_t BTN_DOWN  = (1 << 1);
static constexpr uint16_t BTN_LEFT  = (1 << 2);
static constexpr uint16_t BTN_RIGHT = (1 << 3);
static constexpr uint16_t BTN_A     = (1 << 4);
static constexpr uint16_t BTN_B     = (1 << 5);

Game147CrazyBalloon::Game147CrazyBalloon() {
    Reset();
}

void Game147CrazyBalloon::Init() {
    Reset();
}

void Game147CrazyBalloon::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game147CrazyBalloon::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    cx_ = 2.0f;
    cy_ = 13.0f;
    swing_angle_ = 0.0f;
    swing_speed_ = 3.5f;
    swing_amp_ = 0.75f;
    arm_length_ = 2.0f;
    bx_ = 2.0f;
    by_ = 11.0f;

    gx_ = 13.5f;
    gy_ = 2.0f;

    num_particles_ = 0;

    hazards_[0] = {7.0f, 7.0f, 2.2f, 0.0f, 4.0f, 11.0f, true};
    hazards_[1] = {10.0f, 10.0f, 0.0f, 1.8f, 7.0f, 12.0f, false};
    num_hazards_ = 2;
}

bool Game147CrazyBalloon::IsSpikeWall(int x, int y) const {
    if (x <= 0 || x >= 15 || y <= 0 || y >= 15) return true;

    // Barrier 1: Vertical spike wall at x=4, y in [3..11]
    if (x == 4 && y >= 3 && y <= 11) return true;
    // Barrier 2: Vertical spike wall at x=8, y in [3..11]
    if (x == 8 && y >= 3 && y <= 11) return true;
    // Barrier 3: Vertical spike wall at x=12, y in [5..13]
    if (x == 12 && y >= 5 && y <= 13) return true;

    return false;
}

void Game147CrazyBalloon::PopBalloon() {
    lives_--;
    state_ = STATE_BALLOON_POPPED;
    state_timer_ = 0.0f;

    num_particles_ = 8;
    for (int i = 0; i < 8; ++i) {
        float ang = i * (3.14159265f / 4.0f);
        particles_[i].x = bx_;
        particles_[i].y = by_;
        particles_[i].vx = std::cos(ang) * 6.0f;
        particles_[i].vy = std::sin(ang) * 6.0f;
        particles_[i].life = 0.8f;
    }
}

void Game147CrazyBalloon::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        bool is_stabilized = (buttons & BTN_A) != 0;
        float base_speed = is_stabilized ? 2.2f : 4.2f;
        float target_amp = is_stabilized ? 0.25f : 0.75f;

        // Button B: Quick flip oscillation impulse
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            swing_angle_ = -swing_angle_;
        }

        swing_amp_ += (target_amp - swing_amp_) * std::min(1.0f, dt * 6.0f);

        float dx = 0.0f;
        float dy = 0.0f;
        if (buttons & BTN_LEFT)  dx -= base_speed;
        if (buttons & BTN_RIGHT) dx += base_speed;
        if (buttons & BTN_UP)    dy -= base_speed;
        if (buttons & BTN_DOWN)  dy += base_speed;

        // Wind corridor between y=5 and y=8
        if (cy_ >= 5.0f && cy_ <= 8.0f) {
            dx += 1.5f;
        }

        float new_cx = cx_ + dx * dt;
        float new_cy = cy_ + dy * dt;

        int tile_new_cx = static_cast<int>(std::round(new_cx));
        int tile_cy     = static_cast<int>(std::round(cy_));
        int tile_cx     = static_cast<int>(std::round(cx_));
        int tile_new_cy = static_cast<int>(std::round(new_cy));

        if (!IsSpikeWall(tile_new_cx, tile_cy)) {
            cx_ = std::max(1.0f, std::min(14.0f, new_cx));
        }
        if (!IsSpikeWall(tile_cx, tile_new_cy)) {
            cy_ = std::max(1.0f, std::min(14.0f, new_cy));
        }

        // Pendulum harmonic motion
        swing_angle_ += swing_speed_ * dt;
        float actual_theta = swing_amp_ * std::sin(swing_angle_);

        bx_ = cx_ + arm_length_ * std::sin(actual_theta);
        by_ = cy_ - arm_length_ * std::cos(actual_theta);

        // Spike wall collisions
        int b_tile_x = static_cast<int>(std::round(bx_));
        int b_tile_y = static_cast<int>(std::round(by_));
        int c_tile_x = static_cast<int>(std::round(cx_));
        int c_tile_y = static_cast<int>(std::round(cy_));

        if (IsSpikeWall(b_tile_x, b_tile_y) || IsSpikeWall(c_tile_x, c_tile_y)) {
            PopBalloon();
            return;
        }

        // Hazards collision
        for (int i = 0; i < num_hazards_; ++i) {
            auto& h = hazards_[i];
            h.x += h.vx * dt;
            h.y += h.vy * dt;
            if (h.horizontal) {
                if (h.x <= h.min_val || h.x >= h.max_val) h.vx = -h.vx;
            } else {
                if (h.y <= h.min_val || h.y >= h.max_val) h.vy = -h.vy;
            }

            if (std::hypot(bx_ - h.x, by_ - h.y) < 1.0f) {
                PopBalloon();
                return;
            }
        }

        // Goal reached
        if (std::hypot(bx_ - gx_, by_ - gy_) < 1.4f) {
            score_ += 1500;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
        }

    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_BALLOON_POPPED) {
        state_timer_ += dt;
        for (int i = 0; i < num_particles_; ++i) {
            particles_[i].x += particles_[i].vx * dt;
            particles_[i].y += particles_[i].vy * dt;
            particles_[i].life -= dt;
        }

        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else {
                if (lives_ > 0) {
                    cx_ = 2.0f;
                    cy_ = 13.0f;
                    state_ = STATE_PLAYING;
                    state_timer_ = 0.0f;
                } else {
                    state_ = STATE_GAME_OVER;
                    state_timer_ = 0.0f;
                }
            }
        }
    } else if (state_ == STATE_GAME_OVER) {
        state_timer_ += dt;
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
    }
}

void Game147CrazyBalloon::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Spikes
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsSpikeWall(x, y)) {
                set_pixel(x, y, 40, 160, 40);
            }
        }
    }

    // 2. Goal
    set_pixel(static_cast<int>(std::round(gx_)), static_cast<int>(std::round(gy_)), 255, 220, 30);

    // 3. Wind corridor indicator
    for (int wy = 5; wy <= 8; ++wy) {
        set_pixel(1, wy, 20, 60, 120);
    }

    // 4. Moving hazards
    for (int i = 0; i < num_hazards_; ++i) {
        set_pixel(static_cast<int>(std::round(hazards_[i].x)),
                  static_cast<int>(std::round(hazards_[i].y)), 255, 30, 30);
    }

    // 5. Trolley & Stick
    int cx = static_cast<int>(std::round(cx_));
    int cy = static_cast<int>(std::round(cy_));
    set_pixel(cx, cy, 140, 140, 160);

    int bx = static_cast<int>(std::round(bx_));
    int by = static_cast<int>(std::round(by_));
    int mid_x = static_cast<int>(std::round((cx_ + bx_) * 0.5f));
    int mid_y = static_cast<int>(std::round((cy_ + by_) * 0.5f));
    set_pixel(mid_x, mid_y, 180, 180, 100);

    // 6. Balloon
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(bx, by, 255, 40, 60);
        if (bx + 1 < 16) set_pixel(bx + 1, by, 255, 120, 120);
    } else if (state_ == STATE_BALLOON_POPPED) {
        for (int i = 0; i < num_particles_; ++i) {
            if (particles_[i].life > 0.0f) {
                set_pixel(static_cast<int>(std::round(particles_[i].x)),
                          static_cast<int>(std::round(particles_[i].y)), 255, 200, 50);
            }
        }
    }

    // 7. Lives
    for (int l = 0; l < std::min((int)lives_, 3); ++l) {
        set_pixel(1 + l, 0, 255, 60, 80);
    }
}

} // namespace arcade
