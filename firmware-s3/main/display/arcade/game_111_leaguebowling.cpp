#include "game_111_leaguebowling.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game111LeagueBowling::Game111LeagueBowling() {
    Reset();
}

void Game111LeagueBowling::Init() {
    Reset();
}

void Game111LeagueBowling::Reset() {
    score_ = 0;
    current_frame_ = 1;
    current_roll_ = 1;
    InitFrame();
}

void Game111LeagueBowling::InitFrame() {
    state_ = STATE_AIMING;
    state_timer_ = 0.0f;
    bowler_x_ = 7.5f;
    gauge_val_ = 0.0f;
    gauge_dir_ = 1.0f;
    hook_spin_ = 0;
    pins_knocked_down_ = 0;

    ball_x_ = 7.5f;
    ball_y_ = 13.0f;
    ball_vx_ = 0.0f;
    ball_vy_ = 0.0f;
    in_gutter_ = false;

    if (current_roll_ == 1) {
        ResetPins();
    }
}

void Game111LeagueBowling::ResetPins() {
    // 10-pin Bowling Triangle Coordinates:
    // Headpin
    pins_[0].x = 7.5f;  pins_[0].y = 5.0f; pins_[0].standing = true;

    // Row 2
    pins_[1].x = 6.5f;  pins_[1].y = 4.0f; pins_[1].standing = true;
    pins_[2].x = 8.5f;  pins_[2].y = 4.0f; pins_[2].standing = true;

    // Row 3
    pins_[3].x = 5.5f;  pins_[3].y = 3.0f; pins_[3].standing = true;
    pins_[4].x = 7.5f;  pins_[4].y = 3.0f; pins_[4].standing = true;
    pins_[5].x = 9.5f;  pins_[5].y = 3.0f; pins_[5].standing = true;

    // Row 4 (Back row)
    pins_[6].x = 4.5f;  pins_[6].y = 2.0f; pins_[6].standing = true;
    pins_[7].x = 6.5f;  pins_[7].y = 2.0f; pins_[7].standing = true;
    pins_[8].x = 8.5f;  pins_[8].y = 2.0f; pins_[8].standing = true;
    pins_[9].x = 10.5f; pins_[9].y = 2.0f; pins_[9].standing = true;
}

void Game111LeagueBowling::ForceThrow(float power, int hook) {
    throw_power_ = power;
    hook_spin_ = hook;
    ball_x_ = bowler_x_;
    ball_y_ = 13.0f;
    ball_vy_ = -throw_power_;
    ball_vx_ = static_cast<float>(hook_spin_) * 0.5f;
    state_ = STATE_BALL_ROLLING;
}

void Game111LeagueBowling::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_FRAME_RESULT) {
        if (state_timer_ > 1.8f) {
            if (current_roll_ == 1 && pins_knocked_down_ < 10) {
                // Roll 2 (Attempt Spare)
                current_roll_ = 2;
                InitFrame();
            } else {
                // Next Frame
                current_frame_++;
                current_roll_ = 1;
                if (current_frame_ > TOTAL_FRAMES) {
                    state_ = STATE_GAME_OVER;
                    state_timer_ = 0.0f;
                } else {
                    InitFrame();
                }
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

    if (state_ == STATE_AIMING || state_ == STATE_POWER_GAUGE) {
        UpdateAimingAndGauge(dt, buttons, prev_buttons);
    } else if (state_ == STATE_BALL_ROLLING) {
        UpdateBallRoll(dt);
        CheckPinCollisions();
    }
}

void Game111LeagueBowling::UpdateAimingAndGauge(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (state_ == STATE_AIMING) {
        // Lateral positioning
        float move_spd = 5.0f;
        if (buttons & BTN_LEFT)  bowler_x_ = std::max(4.0f, bowler_x_ - move_spd * dt);
        if (buttons & BTN_RIGHT) bowler_x_ = std::min(11.0f, bowler_x_ + move_spd * dt);

        // Button B: Cycle hook spin (-1 = Left hook, 0 = Straight, 1 = Right hook)
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            if (hook_spin_ == 0) hook_spin_ = -1;
            else if (hook_spin_ == -1) hook_spin_ = 1;
            else hook_spin_ = 0;
        }

        // Button A: Confirm aim and enter power gauge
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            state_ = STATE_POWER_GAUGE;
            gauge_val_ = 0.2f;
            gauge_dir_ = 1.0f;
        }
    } else if (state_ == STATE_POWER_GAUGE) {
        // Power gauge oscillates
        gauge_val_ += gauge_dir_ * 2.8f * dt;
        if (gauge_val_ >= 1.0f) {
            gauge_val_ = 1.0f;
            gauge_dir_ = -1.0f;
        } else if (gauge_val_ <= 0.1f) {
            gauge_val_ = 0.1f;
            gauge_dir_ = 1.0f;
        }

        // Button A: Release Ball!
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            throw_power_ = 8.0f + gauge_val_ * 10.0f;
            ForceThrow(throw_power_, hook_spin_);
        }
    }
}

void Game111LeagueBowling::UpdateBallRoll(float dt) {
    // Apply hook curve spin if not in gutter
    if (!in_gutter_) {
        ball_vx_ += static_cast<float>(hook_spin_) * 3.8f * dt;
    }

    ball_x_ += ball_vx_ * dt;
    ball_y_ += ball_vy_ * dt;

    // Check Gutter collision (Left gutter at x <= 2.8, Right gutter at x >= 12.2)
    if (ball_x_ <= 2.8f) {
        ball_x_ = 2.4f;
        ball_vx_ = 0.0f;
        in_gutter_ = true;
    } else if (ball_x_ >= 12.2f) {
        ball_x_ = 12.6f;
        ball_vx_ = 0.0f;
        in_gutter_ = true;
    }

    // Ball reaches back pit
    if (ball_y_ <= 1.0f) {
        ConcludeRoll();
    }
}

void Game111LeagueBowling::CheckPinCollisions() {
    if (in_gutter_) return;

    for (int i = 0; i < NUM_PINS; ++i) {
        if (!pins_[i].standing) continue;

        float dx = std::abs(ball_x_ - pins_[i].x);
        float dy = std::abs(ball_y_ - pins_[i].y);

        if (dx < 0.9f && dy < 0.9f) {
            // Direct pin hit!
            pins_[i].standing = false;
            pins_knocked_down_++;
            score_ += 10;

            // Kinetic scatter to neighbor pins
            for (int j = 0; j < NUM_PINS; ++j) {
                if (pins_[j].standing) {
                    float ndx = std::abs(pins_[i].x - pins_[j].x);
                    float ndy = std::abs(pins_[i].y - pins_[j].y);
                    if (ndx <= 1.4f && ndy <= 1.4f) {
                        // Knock down neighbor pin in chain reaction
                        pins_[j].standing = false;
                        pins_knocked_down_++;
                        score_ += 10;
                    }
                }
            }
        }
    }
}

void Game111LeagueBowling::ConcludeRoll() {
    state_ = STATE_FRAME_RESULT;
    state_timer_ = 0.0f;

    if (current_roll_ == 1 && pins_knocked_down_ == 10) {
        // STRIKE!
        score_ += 300;
    } else if (current_roll_ == 2 && pins_knocked_down_ == 10) {
        // SPARE!
        score_ += 150;
    }
}

void Game111LeagueBowling::Render(uint8_t* fb) {
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

    // Alley Architecture
    for (int y = 0; y < 16; ++y) {
        // Gutters (Dark slate gray)
        set_pixel(1, y, 40, 40, 45);
        set_pixel(2, y, 25, 25, 30);
        set_pixel(13, y, 25, 25, 30);
        set_pixel(14, y, 40, 40, 45);

        // Oiled Hardwood Lane (Golden amber planks)
        for (int x = 3; x <= 12; ++x) {
            uint8_t plank = (x % 2 == 0) ? 220 : 200;
            set_pixel(x, y, plank, plank - 40, 80);
        }
    }

    // Lane Range Finder Arrows at y=8
    set_pixel(5, 8, 120, 60, 20);
    set_pixel(7, 8, 120, 60, 20);
    set_pixel(8, 8, 120, 60, 20);
    set_pixel(10, 8, 120, 60, 20);

    // 10 Bowling Pins
    for (int i = 0; i < NUM_PINS; ++i) {
        if (!pins_[i].standing) continue;
        int px = static_cast<int>(std::round(pins_[i].x));
        int py = static_cast<int>(std::round(pins_[i].y));
        set_pixel(px, py, 255, 255, 255); // White pin body
        set_pixel(px, py - 1, 255, 30, 30); // Red stripe neck
    }

    // Bowling Ball
    if (state_ == STATE_BALL_ROLLING) {
        int bx = static_cast<int>(std::round(ball_x_));
        int by = static_cast<int>(std::round(ball_y_));
        // Glossy blue bowling ball with finger holes
        set_pixel(bx, by, 30, 60, 200);
        set_pixel(bx, by - 1, 200, 220, 255); // Specular reflection
    }

    // Bowler Stance at y=14..15
    if (state_ == STATE_AIMING || state_ == STATE_POWER_GAUGE) {
        int bx = static_cast<int>(std::round(bowler_x_));
        // Bowler in red shirt & blue trousers
        set_pixel(bx, 14, 230, 40, 30);
        set_pixel(bx, 15, 40, 80, 220);
        set_pixel(bx, 13, 255, 220, 160); // Head

        // Ball held in hand
        int hand_x = (hook_spin_ <= 0) ? (bx - 1) : (bx + 1);
        set_pixel(hand_x, 14, 30, 60, 200);

        // Power Gauge Bar on Left Gutter (x=0)
        if (state_ == STATE_POWER_GAUGE) {
            int bars = static_cast<int>(gauge_val_ * 8.0f);
            for (int b = 0; b < bars; ++b) {
                set_pixel(0, 15 - b * 2, 255, 220, 0);
            }
        }
    }

    // Frame Result Splash: STRIKE / SPARE
    if (state_ == STATE_FRAME_RESULT) {
        if (pins_knocked_down_ == 10) {
            // Neon celebration flash on top row
            for (int x = 3; x <= 12; ++x) {
                set_pixel(x, 1, 255, 220, 0);
            }
        }
    }

    // Hook indicator on top row
    if (hook_spin_ == -1) set_pixel(4, 0, 0, 255, 255); // Left spin arrow
    else if (hook_spin_ == 1) set_pixel(11, 0, 0, 255, 255); // Right spin arrow

    // Current Frame on top left
    for (int f = 0; f < current_frame_; ++f) {
        set_pixel(0, f * 3, 255, 100, 0);
    }
}

} // namespace arcade
