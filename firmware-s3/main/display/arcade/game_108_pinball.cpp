#include "game_108_pinball.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game108Pinball::Game108Pinball() {
    Reset();
}

void Game108Pinball::Init() {
    Reset();
}

void Game108Pinball::Reset() {
    score_ = 0;
    balls_left_ = 3;
    multiplier_ = 1;
    InitTable();
    ResetBallToPlunger();
}

void Game108Pinball::InitTable() {
    state_ = STATE_PLUNGER_READY;
    state_timer_ = 0.0f;
    plunger_charge_ = 0.0f;
    left_flipper_up_ = false;
    right_flipper_up_ = false;

    // 3 Triangular Bumpers
    bumpers_[0].x = 5.0f;
    bumpers_[0].y = 5.0f;
    bumpers_[0].flash_timer = 0.0f;

    bumpers_[1].x = 9.0f;
    bumpers_[1].y = 5.0f;
    bumpers_[1].flash_timer = 0.0f;

    bumpers_[2].x = 7.0f;
    bumpers_[2].y = 8.0f;
    bumpers_[2].flash_timer = 0.0f;

    // 3 Rollover lanes at top
    rollovers_[0].x = 4; rollovers_[0].y = 3; rollovers_[0].lit = false;
    rollovers_[1].x = 7; rollovers_[1].y = 3; rollovers_[1].lit = false;
    rollovers_[2].x = 10; rollovers_[2].y = 3; rollovers_[2].lit = false;
}

void Game108Pinball::ResetBallToPlunger() {
    state_ = STATE_PLUNGER_READY;
    state_timer_ = 0.0f;
    ball_x_ = 14.5f;
    ball_y_ = 14.0f;
    ball_vx_ = 0.0f;
    ball_vy_ = 0.0f;
    plunger_charge_ = 0.0f;
}

void Game108Pinball::LaunchBall(float power) {
    if (state_ == STATE_PLUNGER_READY) {
        state_ = STATE_BALL_IN_PLAY;
        ball_vx_ = 0.0f;
        ball_vy_ = -std::max(10.0f, std::min(18.0f, power));
    }
}

void Game108Pinball::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_BALL_DRAINED) {
        if (state_timer_ > 1.8f) {
            balls_left_--;
            if (balls_left_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetBallToPlunger();
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    UpdateFlippersAndPlunger(dt, buttons, prev_buttons);

    if (state_ == STATE_BALL_IN_PLAY) {
        UpdateBallPhysics(dt);
        CheckBumperCollisions();
        CheckFlipperCollisions();
        CheckRollovers();
    }

    // Flash timers
    for (int i = 0; i < NUM_BUMPERS; ++i) {
        if (bumpers_[i].flash_timer > 0.0f) {
            bumpers_[i].flash_timer -= dt;
        }
    }
}

void Game108Pinball::UpdateFlippersAndPlunger(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Left Flipper (Button A)
    left_flipper_up_ = (buttons & BTN_A) != 0;

    // Right Flipper (Button B)
    right_flipper_up_ = (buttons & BTN_B) != 0;

    // Plunger (Pull back with KEY_DOWN, release to launch)
    if (state_ == STATE_PLUNGER_READY) {
        if (buttons & BTN_DOWN) {
            plunger_charge_ = std::min(18.0f, plunger_charge_ + 14.0f * dt);
        } else if (prev_buttons & BTN_DOWN) {
            // Released!
            LaunchBall(plunger_charge_);
        } else if ((buttons & BTN_UP) && !(prev_buttons & BTN_UP)) {
            // Quick launch
            LaunchBall(15.0f);
        }
    }
}

void Game108Pinball::UpdateBallPhysics(float dt) {
    // Gravity pulls down
    ball_vy_ += 14.0f * dt;

    ball_x_ += ball_vx_ * dt;
    ball_y_ += ball_vy_ * dt;

    // Shooter Lane curve to main table at top
    if (ball_x_ >= 13.5f) {
        if (ball_y_ <= 1.5f && ball_vy_ < 0.0f) {
            // Apex curve: deflects left into table
            ball_x_ = 12.5f;
            ball_vx_ = -4.5f;
            ball_vy_ = 2.0f;
        }
    } else {
        // Table Boundaries: Left wall at x=1.0, Right wall at x=13.0
        if (ball_x_ <= 1.0f) {
            ball_x_ = 1.0f;
            ball_vx_ = std::abs(ball_vx_) * 0.8f;
        } else if (ball_x_ >= 13.0f) {
            ball_x_ = 13.0f;
            ball_vx_ = -std::abs(ball_vx_) * 0.8f;
        }

        // Top Wall at y=1.0
        if (ball_y_ <= 1.0f) {
            ball_y_ = 1.0f;
            ball_vy_ = std::abs(ball_vy_) * 0.8f;
        }
    }

    // Drain at bottom (y >= 15.5)
    if (ball_y_ >= 15.5f) {
        state_ = STATE_BALL_DRAINED;
        state_timer_ = 0.0f;
    }
}

void Game108Pinball::CheckBumperCollisions() {
    for (int i = 0; i < NUM_BUMPERS; ++i) {
        float dx = ball_x_ - bumpers_[i].x;
        float dy = ball_y_ - bumpers_[i].y;
        float dist = std::sqrt(dx * dx + dy * dy);

        if (dist < 1.3f && dist > 0.01f) {
            // Bumper repels ball strongly!
            float nx = dx / dist;
            float ny = dy / dist;
            ball_vx_ = nx * 10.0f;
            ball_vy_ = ny * 10.0f;
            bumpers_[i].flash_timer = 0.25f;
            score_ += 100 * multiplier_;
        }
    }
}

void Game108Pinball::CheckFlipperCollisions() {
    // Left Flipper: spans x in [4.0, 7.0], y around 14.0
    if (ball_y_ >= 13.2f && ball_y_ <= 14.6f && ball_vy_ > 0.0f) {
        if (ball_x_ >= 3.8f && ball_x_ <= 7.0f) {
            if (left_flipper_up_) {
                // Flipper strikes ball UP and RIGHT!
                ball_vy_ = -13.0f;
                ball_vx_ = 3.5f + (ball_x_ - 3.8f) * 2.0f;
                score_ += 20 * multiplier_;
            } else {
                // Passive bounce off slope
                ball_vy_ = -std::abs(ball_vy_) * 0.5f;
                ball_vx_ = 2.0f;
            }
            return;
        }
    }

    // Right Flipper: spans x in [8.5, 11.8], y around 14.0
    if (ball_y_ >= 13.2f && ball_y_ <= 14.6f && ball_vy_ > 0.0f) {
        if (ball_x_ >= 8.5f && ball_x_ <= 11.8f) {
            if (right_flipper_up_) {
                // Flipper strikes ball UP and LEFT!
                ball_vy_ = -13.0f;
                ball_vx_ = -3.5f - (11.8f - ball_x_) * 2.0f;
                score_ += 20 * multiplier_;
            } else {
                // Passive bounce
                ball_vy_ = -std::abs(ball_vy_) * 0.5f;
                ball_vx_ = -2.0f;
            }
            return;
        }
    }
}

void Game108Pinball::CheckRollovers() {
    for (int i = 0; i < NUM_ROLLOVERS; ++i) {
        if (std::abs(ball_x_ - static_cast<float>(rollovers_[i].x)) < 1.0f &&
            std::abs(ball_y_ - static_cast<float>(rollovers_[i].y)) < 1.0f) {
            if (!rollovers_[i].lit) {
                rollovers_[i].lit = true;
                score_ += 200;

                // Check if all 3 rollovers lit
                bool all_lit = true;
                for (int j = 0; j < NUM_ROLLOVERS; ++j) {
                    if (!rollovers_[j].lit) { all_lit = false; break; }
                }

                if (all_lit) {
                    score_ += 1000;
                    multiplier_ = std::min(4, multiplier_ + 1);
                    for (int j = 0; j < NUM_ROLLOVERS; ++j) {
                        rollovers_[j].lit = false;
                    }
                }
            }
        }
    }
}

void Game108Pinball::Render(uint8_t* fb) {
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

    // Table Felt / Playfield (Deep blue neon table)
    for (int y = 0; y < 16; ++y) {
        for (int x = 1; x <= 13; ++x) {
            set_pixel(x, y, 10, 15, 40);
        }
    }

    // Outer Walls (Silver metal rails)
    for (int y = 0; y < 16; ++y) {
        set_pixel(0, y, 180, 180, 200);   // Left wall
        set_pixel(13, y, 180, 180, 200);  // Shooter lane divider
        set_pixel(15, y, 180, 180, 200);  // Right wall
    }
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 0, 180, 180, 200);   // Top arch
    }

    // Rollover Lanes at y=3
    for (int i = 0; i < NUM_ROLLOVERS; ++i) {
        int rx = rollovers_[i].x;
        int ry = rollovers_[i].y;
        if (rollovers_[i].lit) {
            set_pixel(rx, ry, 255, 220, 0); // Bright gold
        } else {
            set_pixel(rx, ry, 80, 80, 120); // Dim light
        }
    }

    // 3 Bumpers
    for (int i = 0; i < NUM_BUMPERS; ++i) {
        int bx = static_cast<int>(std::round(bumpers_[i].x));
        int by = static_cast<int>(std::round(bumpers_[i].y));

        if (bumpers_[i].flash_timer > 0.0f) {
            // Flash white/yellow
            set_pixel(bx, by, 255, 255, 255);
            set_pixel(bx - 1, by, 255, 220, 0);
            set_pixel(bx + 1, by, 255, 220, 0);
            set_pixel(bx, by - 1, 255, 220, 0);
            set_pixel(bx, by + 1, 255, 220, 0);
        } else {
            // Glowing neon red bumper
            set_pixel(bx, by, 240, 40, 40);
            set_pixel(bx - 1, by, 200, 20, 20);
            set_pixel(bx + 1, by, 200, 20, 20);
            set_pixel(bx, by - 1, 200, 20, 20);
            set_pixel(bx, by + 1, 200, 20, 20);
        }
    }

    // Left Flipper at y=14
    int l_tip_y = left_flipper_up_ ? 13 : 14;
    set_pixel(4, 14, 255, 140, 20);
    set_pixel(5, 14, 255, 140, 20);
    set_pixel(6, l_tip_y, 255, 200, 40); // Flipper tip

    // Right Flipper at y=14
    int r_tip_y = right_flipper_up_ ? 13 : 14;
    set_pixel(9, r_tip_y, 255, 200, 40); // Flipper tip
    set_pixel(10, 14, 255, 140, 20);
    set_pixel(11, 14, 255, 140, 20);

    // Drain Hole at x=7..8, y=15
    set_pixel(7, 15, 0, 0, 0);
    set_pixel(8, 15, 0, 0, 0);

    // Plunger Spring at bottom of shooter lane (x=14, y=15)
    if (state_ == STATE_PLUNGER_READY) {
        int compress = static_cast<int>(plunger_charge_ / 6.0f);
        set_pixel(14, 15, 255, 60, 20);
        set_pixel(14, 15 - compress, 255, 200, 0);
    }

    // Silver Ball
    int px = static_cast<int>(std::round(ball_x_));
    int py = static_cast<int>(std::round(ball_y_));
    if (state_ != STATE_BALL_DRAINED) {
        set_pixel(px, py, 255, 255, 255); // Ball core
    }

    // Multiplier indicator on top left
    if (multiplier_ > 1) {
        for (int m = 0; m < multiplier_; ++m) {
            set_pixel(0, m * 2, 0, 255, 150);
        }
    }

    // Balls remaining on top right
    for (int b = 0; b < std::min(balls_left_, 3); ++b) {
        set_pixel(15, b * 2, 255, 220, 0);
    }
}

} // namespace arcade
