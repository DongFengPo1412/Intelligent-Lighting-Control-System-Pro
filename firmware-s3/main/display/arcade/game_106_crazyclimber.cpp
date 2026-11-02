#include "game_106_crazyclimber.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr int WINDOW_X[Game106CrazyClimber::NUM_WINDOW_COLS] = {3, 6, 9, 12};
static constexpr int WINDOW_Y[Game106CrazyClimber::NUM_WINDOW_ROWS] = {2, 4, 6, 8, 10, 12};

Game106CrazyClimber::Game106CrazyClimber() {
    Reset();
}

void Game106CrazyClimber::Init() {
    Reset();
}

void Game106CrazyClimber::Reset() {
    score_ = 0;
    lives_ = 3;
    altitude_ = 0;
    InitBuilding();
}

void Game106CrazyClimber::InitBuilding() {
    state_ = STATE_CLIMBING;
    state_timer_ = 0.0f;
    climber_col_ = 1; // Col 1 (x=6)
    climber_y_ = 13.0f;
    left_hand_grip_ = true;
    right_hand_grip_ = true;
    slip_recovery_timer_ = 0.0f;
    last_pull_hand_ = 0;

    condor_x_ = 2.0f;
    condor_vx_ = 3.2f;
    condor_egg_timer_ = 1.5f;

    for (int r = 0; r < NUM_WINDOW_ROWS; ++r) {
        for (int c = 0; c < NUM_WINDOW_COLS; ++c) {
            windows_[r][c].is_open = ((r + c) % 3 != 0);
            windows_[r][c].toggle_timer = 1.5f + static_cast<float>((r * 2 + c) % 3) * 0.8f;
            windows_[r][c].has_hazard = (r == 1 && c == 2);
        }
    }

    for (int i = 0; i < MAX_HAZARDS; ++i) {
        hazards_[i].active = false;
    }
}

void Game106CrazyClimber::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_FALL_OFF) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                InitBuilding();
            }
        }
        return;
    }

    if (state_ == STATE_ROOFTOP_CLEAR) {
        if (state_timer_ > 2.2f) {
            altitude_ = 0;
            InitBuilding();
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    UpdateClimber(dt, buttons, prev_buttons);
    UpdateWindows(dt);
    UpdateCondorAndHazards(dt);
    CheckCollisions();

    // Check rooftop arrival
    if (altitude_ >= 80 && climber_y_ <= 2.2f && state_ != STATE_ROOFTOP_CLEAR) {
        state_ = STATE_ROOFTOP_CLEAR;
        state_timer_ = 0.0f;
        score_ += 3000;
    }
}

void Game106CrazyClimber::UpdateClimber(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (state_ == STATE_SLIPPED_ONE_HAND) {
        slip_recovery_timer_ -= dt;
        // Press the slipped hand button to regain grip!
        if (!left_hand_grip_ && (buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            left_hand_grip_ = true;
            state_ = STATE_CLIMBING;
            score_ += 50;
        } else if (!right_hand_grip_ && (buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            right_hand_grip_ = true;
            state_ = STATE_CLIMBING;
            score_ += 50;
        }

        if (slip_recovery_timer_ <= 0.0f) {
            state_ = STATE_FALL_OFF;
            state_timer_ = 0.0f;
        }
        return;
    }

    // Lateral column shifting
    if ((buttons & BTN_LEFT) && !(prev_buttons & BTN_LEFT)) {
        if (climber_col_ > 0) climber_col_--;
    } else if ((buttons & BTN_RIGHT) && !(prev_buttons & BTN_RIGHT)) {
        if (climber_col_ < NUM_WINDOW_COLS - 1) climber_col_++;
    }

    // Alternating Hand Climb:
    // Button A = Left hand pull, Button B = Right hand pull
    bool pull_left = (buttons & BTN_A) && !(prev_buttons & BTN_A);
    bool pull_right = (buttons & BTN_B) && !(prev_buttons & BTN_B);

    if (pull_left || pull_right) {
        float ascend = 0.4f;
        if ((pull_left && last_pull_hand_ == 2) || (pull_right && last_pull_hand_ == 1)) {
            // Perfect alternating rhythm! Bonus ascent speed
            ascend = 0.75f;
            score_ += 20;
        } else {
            score_ += 5;
        }

        last_pull_hand_ = pull_left ? 1 : 2;
        climber_y_ -= ascend;

        // Scroll building facade when climbing up high
        if (climber_y_ <= 3.0f && altitude_ < 80) {
            climber_y_ += 4.0f;
            altitude_ += 10;
            score_ += 200;

            // Shift windows and toggle new states
            for (int r = NUM_WINDOW_ROWS - 1; r >= 2; --r) {
                for (int c = 0; c < NUM_WINDOW_COLS; ++c) {
                    windows_[r][c] = windows_[r - 2][c];
                }
            }
            for (int r = 0; r < 2; ++r) {
                for (int c = 0; c < NUM_WINDOW_COLS; ++c) {
                    windows_[r][c].is_open = ((altitude_ + r + c) % 2 == 0);
                    windows_[r][c].toggle_timer = 1.0f + static_cast<float>(c) * 0.5f;
                    windows_[r][c].has_hazard = ((r + c + altitude_) % 5 == 0);
                }
            }
        }
    }
}

void Game106CrazyClimber::UpdateWindows(float dt) {
    for (int r = 0; r < NUM_WINDOW_ROWS; ++r) {
        for (int c = 0; c < NUM_WINDOW_COLS; ++c) {
            windows_[r][c].toggle_timer -= dt;
            if (windows_[r][c].toggle_timer <= 0.0f) {
                windows_[r][c].is_open = !windows_[r][c].is_open;
                windows_[r][c].toggle_timer = 2.0f + static_cast<float>((r * 3 + c) % 4) * 0.6f;

                // Window slams shut while climber is on it!
                if (!windows_[r][c].is_open && c == climber_col_) {
                    float wy = static_cast<float>(WINDOW_Y[r]);
                    if (std::abs(climber_y_ - wy) < 0.9f && state_ == STATE_CLIMBING) {
                        // Smashes hand!
                        state_ = STATE_SLIPPED_ONE_HAND;
                        slip_recovery_timer_ = 1.6f;
                        if (last_pull_hand_ == 1) left_hand_grip_ = false;
                        else right_hand_grip_ = false;
                    }
                }

                // If window opened and has hazard, drop flowerpot!
                if (windows_[r][c].is_open && windows_[r][c].has_hazard) {
                    for (int h = 0; h < MAX_HAZARDS; ++h) {
                        if (!hazards_[h].active) {
                            hazards_[h].active = true;
                            hazards_[h].x = static_cast<float>(WINDOW_X[c]);
                            hazards_[h].y = static_cast<float>(WINDOW_Y[r] + 1);
                            hazards_[h].vy = 6.5f;
                            hazards_[h].is_condor_egg = false;
                            break;
                        }
                    }
                }
            }
        }
    }
}

void Game106CrazyClimber::UpdateCondorAndHazards(float dt) {
    // Swooping Condor across rooftop
    condor_x_ += condor_vx_ * dt;
    if (condor_x_ <= 1.0f) {
        condor_x_ = 1.0f;
        condor_vx_ = std::abs(condor_vx_);
    } else if (condor_x_ >= 14.0f) {
        condor_x_ = 14.0f;
        condor_vx_ = -std::abs(condor_vx_);
    }

    condor_egg_timer_ -= dt;
    if (condor_egg_timer_ <= 0.0f) {
        condor_egg_timer_ = 2.2f;
        for (int h = 0; h < MAX_HAZARDS; ++h) {
            if (!hazards_[h].active) {
                hazards_[h].active = true;
                hazards_[h].x = condor_x_;
                hazards_[h].y = 2.0f;
                hazards_[h].vy = 5.5f;
                hazards_[h].is_condor_egg = true;
                break;
            }
        }
    }

    // Update falling hazards (eggs / flowerpots)
    for (int h = 0; h < MAX_HAZARDS; ++h) {
        if (!hazards_[h].active) continue;
        hazards_[h].y += hazards_[h].vy * dt;
        if (hazards_[h].y > 15.5f) {
            hazards_[h].active = false;
        }
    }
}

void Game106CrazyClimber::CheckCollisions() {
    float cx = static_cast<float>(WINDOW_X[climber_col_]);
    float cy = climber_y_;

    for (int h = 0; h < MAX_HAZARDS; ++h) {
        if (!hazards_[h].active) continue;
        float dx = std::abs(cx - hazards_[h].x);
        float dy = std::abs(cy - hazards_[h].y);
        if (dx < 0.9f && dy < 1.1f) {
            hazards_[h].active = false;
            if (state_ == STATE_CLIMBING) {
                // Hit causes hand slip!
                state_ = STATE_SLIPPED_ONE_HAND;
                slip_recovery_timer_ = 1.6f;
                left_hand_grip_ = false;
            } else if (state_ == STATE_SLIPPED_ONE_HAND) {
                // Second hit while slipping causes fatal plunge!
                state_ = STATE_FALL_OFF;
                state_timer_ = 0.0f;
            }
            return;
        }
    }
}

void Game106CrazyClimber::Render(uint8_t* fb) {
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

    // Skyscraper brick facade background (Dark brown/gray brick facade)
    for (int y = 0; y < 16; ++y) {
        for (int x = 1; x <= 14; ++x) {
            uint8_t b_col = ((x + y) % 2 == 0) ? 60 : 45;
            set_pixel(x, y, b_col + 10, b_col, b_col - 5);
        }
    }

    // Windows
    for (int r = 0; r < NUM_WINDOW_ROWS; ++r) {
        int wy = WINDOW_Y[r];
        for (int c = 0; c < NUM_WINDOW_COLS; ++c) {
            int wx = WINDOW_X[c];
            if (windows_[r][c].is_open) {
                // Open window: dark interior room with light blue glass frame
                set_pixel(wx, wy, 15, 20, 35);
                set_pixel(wx + 1, wy, 15, 20, 35);
                set_pixel(wx, wy + 1, 100, 180, 240); // Window sill
                set_pixel(wx + 1, wy + 1, 100, 180, 240);
                if (windows_[r][c].has_hazard) {
                    set_pixel(wx, wy, 255, 140, 20); // Flowerpot in window
                }
            } else {
                // Closed window: amber reflective window panes
                set_pixel(wx, wy, 220, 200, 120);
                set_pixel(wx + 1, wy, 200, 180, 100);
                set_pixel(wx, wy + 1, 180, 160, 90);
                set_pixel(wx + 1, wy + 1, 180, 160, 90);
            }
        }
    }

    // Rooftop & Helicopter (if altitude >= 80)
    if (altitude_ >= 80) {
        for (int x = 1; x <= 14; ++x) {
            set_pixel(x, 1, 200, 40, 30); // Rooftop ledge
        }
        // Rescue Helicopter at x=7..9, y=0..1
        set_pixel(7, 0, 255, 255, 255); // Rotor blade
        set_pixel(8, 0, 255, 220, 0);   // Cockpit
        set_pixel(9, 0, 255, 255, 255);
        set_pixel(8, 1, 255, 200, 50);  // Runner skid
    } else {
        // Swooping Condor at condor_x_, y=1
        int cx = static_cast<int>(std::round(condor_x_));
        set_pixel(cx, 1, 180, 120, 40);
        set_pixel(cx - 1, 0, 220, 160, 60); // Wing
        set_pixel(cx + 1, 0, 220, 160, 60);
    }

    // Falling Hazards (Eggs / Flowerpots)
    for (int h = 0; h < MAX_HAZARDS; ++h) {
        if (!hazards_[h].active) continue;
        int hx = static_cast<int>(std::round(hazards_[h].x));
        int hy = static_cast<int>(std::round(hazards_[h].y));
        if (hazards_[h].is_condor_egg) {
            set_pixel(hx, hy, 255, 255, 240); // White egg
        } else {
            set_pixel(hx, hy, 200, 80, 20);   // Terracotta flowerpot
        }
    }

    // Climber
    int px = WINDOW_X[climber_col_];
    int py = static_cast<int>(std::round(climber_y_));

    if (state_ == STATE_FALL_OFF) {
        // Tumbling climber
        set_pixel(px, py, 255, 40, 30);
        set_pixel(px, py + 1, 255, 180, 0);
    } else if (state_ == STATE_SLIPPED_ONE_HAND) {
        // Dangling by one hand
        set_pixel(px, py, 255, 200, 40); // Yellow shirt
        set_pixel(px, py + 1, 40, 80, 240); // Blue trousers
        if (left_hand_grip_) set_pixel(px - 1, py - 1, 255, 255, 255); // Left hand up
        if (right_hand_grip_) set_pixel(px + 1, py - 1, 255, 255, 255); // Right hand up
    } else {
        // Normal climbing pose
        set_pixel(px, py, 255, 220, 40); // Yellow climber shirt
        set_pixel(px, py + 1, 40, 80, 240); // Blue trousers
        set_pixel(px - 1, py - 1, 255, 255, 255); // Left hand holding sill
        set_pixel(px + 1, py - 1, 255, 255, 255); // Right hand holding sill
    }

    // Altitude indicator on left column (x=0)
    int alt_bar = altitude_ / 10;
    for (int a = 0; a < std::min(alt_bar, 8); ++a) {
        set_pixel(0, 15 - a * 2, 0, 220, 255);
    }

    // Lives on top right
    for (int l = 0; l < std::min(lives_, 3); ++l) {
        set_pixel(15, l * 2, 255, 200, 0);
    }
}

} // namespace arcade
