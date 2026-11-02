#include "game_060_marblemadness.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game060MarbleMadness::Game060MarbleMadness()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(3500),
      time_remaining_(35.0f),
      marble_x_(2.5f),
      marble_y_(2.0f),
      marble_vx_(0.0f),
      marble_vy_(0.0f),
      is_on_ice_(false),
      evil_x_(8.0f),
      evil_y_(8.5f),
      evil_vx_(-2.0f),
      evil_vy_(1.5f),
      acid_x_(8.5f),
      acid_y_(11.5f),
      goal_x_(12.5f),
      goal_y_(14.0f) {
}

void Game060MarbleMadness::Init() {
    Reset();
}

void Game060MarbleMadness::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    time_remaining_ = 35.0f;
    InitCourse();
}

void Game060MarbleMadness::InitCourse() {
    marble_x_ = 2.5f;
    marble_y_ = 2.0f;
    marble_vx_ = 0.0f;
    marble_vy_ = 0.0f;
    is_on_ice_ = false;

    evil_x_ = 8.0f;
    evil_y_ = 8.5f;
    evil_vx_ = -2.0f;
    evil_vy_ = 1.0f;

    acid_x_ = 8.5f;
    acid_y_ = 11.5f;
    goal_x_ = 12.5f;
    goal_y_ = 14.0f;
}

void Game060MarbleMadness::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 2.0f) {
            state_ = STATE_START;
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f) {
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            InitCourse();
        }
        return;
    }

    if (state_ == STATE_SHATTERED) {
        if (state_timer_ > 1.2f) {
            if (time_remaining_ > 0.0f) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                marble_x_ = 2.5f;
                marble_y_ = 2.0f;
                marble_vx_ = 0.0f;
                marble_vy_ = 0.0f;
            } else {
                state_ = STATE_DEAD;
            }
        }
        return;
    }

    time_remaining_ -= dt;
    if (time_remaining_ <= 0.0f) {
        time_remaining_ = 0.0f;
        state_ = STATE_DEAD;
        state_timer_ = 0.0f;
        return;
    }

    UpdateMarblePhysics(dt, buttons);
    UpdateEvilMarble(dt);
    CheckTrackHazards();

    // Check Goal
    if (std::abs(marble_x_ - goal_x_) < 1.4f && std::abs(marble_y_ - goal_y_) < 1.4f) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 1000 + static_cast<int>(time_remaining_ * 100.0f);
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game060MarbleMadness::UpdateMarblePhysics(float dt, uint32_t buttons) {
    // Check if on ice sheet
    is_on_ice_ = (marble_y_ >= 5.5f && marble_y_ <= 9.5f && marble_x_ >= 4.0f && marble_x_ <= 10.5f);

    float ax = 0.0f;
    float ay = 0.0f;

    // Rolling inputs
    float torque = is_on_ice_ ? 6.0f : 14.0f;
    if (buttons & BUTTON_LEFT)  ax -= torque;
    if (buttons & BUTTON_RIGHT) ax += torque;
    if (buttons & BUTTON_UP)    ay -= torque;
    if (buttons & BUTTON_DOWN)  ay += torque;

    // Downhill gravitational pull along slope (toward down-right)
    ax += 1.8f;
    ay += 3.0f;

    marble_vx_ += ax * dt;
    marble_vy_ += ay * dt;

    // Surface friction damping
    float friction = is_on_ice_ ? 0.3f : 2.8f;
    marble_vx_ *= (1.0f - friction * dt);
    marble_vy_ *= (1.0f - friction * dt);

    marble_x_ += marble_vx_ * dt;
    marble_y_ += marble_vy_ * dt;

    score_ += static_cast<int>((std::abs(marble_vx_) + std::abs(marble_vy_)) * dt * 1.5f);
}

void Game060MarbleMadness::UpdateEvilMarble(float dt) {
    evil_x_ += evil_vx_ * dt;
    evil_y_ += evil_vy_ * dt;

    if (evil_x_ < 5.0f) {
        evil_x_ = 5.0f;
        evil_vx_ = std::abs(evil_vx_);
    } else if (evil_x_ > 10.5f) {
        evil_x_ = 10.5f;
        evil_vx_ = -std::abs(evil_vx_);
    }

    if (evil_y_ < 6.0f) {
        evil_y_ = 6.0f;
        evil_vy_ = std::abs(evil_vy_);
    } else if (evil_y_ > 9.5f) {
        evil_y_ = 9.5f;
        evil_vy_ = -std::abs(evil_vy_);
    }

    // Elastic collision with player marble
    float dx = marble_x_ - evil_x_;
    float dy = marble_y_ - evil_y_;
    float dist = std::hypot(dx, dy);
    if (dist < 1.2f && dist > 0.05f) {
        // Bounce player violently outward!
        marble_vx_ += (dx / dist) * 12.0f;
        marble_vy_ += (dy / dist) * 12.0f;
    }
}

void Game060MarbleMadness::CheckTrackHazards() {
    // 1. Acid puddle
    if (std::abs(marble_x_ - acid_x_) < 0.9f && std::abs(marble_y_ - acid_y_) < 0.9f) {
        state_ = STATE_SHATTERED;
        state_timer_ = 0.0f;
        time_remaining_ = std::max(0.0f, time_remaining_ - 5.0f);
        return;
    }

    // 2. Track boundaries check (Cliff drop-off)
    bool on_track = false;

    // Segment 1 (Top entry plateau)
    if (marble_y_ >= 0.5f && marble_y_ <= 5.5f) {
        if (marble_x_ >= 1.0f && marble_x_ <= 8.0f) on_track = true;
    }

    // Segment 2 (Middle Ice bridge)
    if (marble_y_ >= 5.0f && marble_y_ <= 10.5f) {
        if (marble_x_ >= 3.5f && marble_x_ <= 11.5f) on_track = true;
    }

    // Segment 3 (Lower Canyon to Goal)
    if (marble_y_ >= 10.0f && marble_y_ <= 15.5f) {
        if (marble_x_ >= 6.5f && marble_x_ <= 15.0f) on_track = true;
    }

    if (!on_track) {
        state_ = STATE_SHATTERED;
        state_timer_ = 0.0f;
        time_remaining_ = std::max(0.0f, time_remaining_ - 5.0f);
    }
}

void Game060MarbleMadness::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Abyss / Void background (Dark deep navy)
    for (int i = 0; i < 16 * 16 * 3; i += 3) {
        fb[i] = 10;
        fb[i + 1] = 10;
        fb[i + 2] = 20;
    }

    // Isometric Geometric Track Tiles:
    // Segment 1: Blue grid tiles
    // Segment 2: Cyan ice sheet
    // Segment 3: Bronze/Orange slope
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;

            // Track plateau 1
            if (y >= 1 && y <= 5 && x >= 1 && x <= 7) {
                fb[idx] = 40;
                fb[idx + 1] = 80;
                fb[idx + 2] = 180;
                if ((x + y) % 2 == 0) {
                    fb[idx] += 20; fb[idx + 1] += 20; fb[idx + 2] += 20;
                }
            }
            // Ice bridge 2
            else if (y >= 6 && y <= 10 && x >= 4 && x <= 11) {
                fb[idx] = 150;
                fb[idx + 1] = 220;
                fb[idx + 2] = 255; // Pale icy cyan
            }
            // Canyon slope 3
            else if (y >= 11 && y <= 15 && x >= 7 && x <= 14) {
                fb[idx] = 180;
                fb[idx + 1] = 110;
                fb[idx + 2] = 40; // Copper track
                if ((x + y) % 2 == 0) {
                    fb[idx] -= 30; fb[idx + 1] -= 20;
                }
            }
        }
    }

    // Acid puddle (x=8, y=11: toxic neon green)
    int ax = static_cast<int>(std::round(acid_x_));
    int ay = static_cast<int>(std::round(acid_y_));
    if (ax >= 0 && ax < 16 && ay >= 0 && ay < 16) {
        int idx = (ay * 16 + ax) * 3;
        fb[idx] = 0;
        fb[idx + 1] = 255;
        fb[idx + 2] = 50;
    }

    // Goal Checkered Finish Pad (x=12..13, y=14)
    for (int gx = 12; gx <= 13; ++gx) {
        int idx = (14 * 16 + gx) * 3;
        if (gx % 2 == 0) {
            fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255; // White
        } else {
            fb[idx] = 0; fb[idx + 1] = 0; fb[idx + 2] = 0; // Black checkered
        }
    }

    // Evil Black Marble
    int ex = static_cast<int>(std::round(evil_x_));
    int ey = static_cast<int>(std::round(evil_y_));
    if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
        int idx = (ey * 16 + ex) * 3;
        fb[idx] = 40;
        fb[idx + 1] = 10;
        fb[idx + 2] = 10; // Dark sinister obsidian
    }

    // Player Marble (Glass red & white striped marble)
    int mx = static_cast<int>(std::round(marble_x_));
    int my = static_cast<int>(std::round(marble_y_));
    if (mx >= 0 && mx < 16 && my >= 0 && my < 16) {
        int idx = (my * 16 + mx) * 3;
        if (state_ == STATE_SHATTERED) {
            // Shattered glass shards
            fb[idx] = 255;
            fb[idx + 1] = 255;
            fb[idx + 2] = 0; // Yellow crack spark
        } else {
            fb[idx] = 255;
            fb[idx + 1] = 30;
            fb[idx + 2] = 60; // Bright crimson sphere
        }
    }

    // HUD: Timer bar on row 0 (Green to Red)
    int time_bars = static_cast<int>((time_remaining_ / 35.0f) * 16.0f);
    for (int t = 0; t < time_bars && t < 16; ++t) {
        int idx = t * 3;
        if (time_remaining_ < 10.0f) {
            fb[idx] = 255; fb[idx + 1] = 0; fb[idx + 2] = 0; // Urgent red
        } else {
            fb[idx] = 0; fb[idx + 1] = 255; fb[idx + 2] = 100; // Cyan green
        }
    }
}

} // namespace arcade
