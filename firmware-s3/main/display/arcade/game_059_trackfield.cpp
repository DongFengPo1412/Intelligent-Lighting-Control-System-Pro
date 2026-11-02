#include "game_059_trackfield.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr float DEG2RAD = 3.14159265f / 180.0f;

Game059TrackField::Game059TrackField()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(3000),
      attempt_(1),
      athlete_x_(1.0f),
      athlete_y_(13.0f),
      speed_(0.0f),
      last_button_pressed_(0),
      throw_angle_(0.0f),
      angle_rising_(false),
      javelin_x_(0.0f),
      javelin_y_(0.0f),
      javelin_vx_(0.0f),
      javelin_vy_(0.0f),
      throw_distance_(0.0f),
      best_distance_(0.0f),
      qualify_distance_(65.0f) {
}

void Game059TrackField::Init() {
    Reset();
}

void Game059TrackField::Reset() {
    state_ = STATE_RUNNING;
    state_timer_ = 0.0f;
    score_ = 0;
    attempt_ = 1;
    best_distance_ = 0.0f;
    InitAttempt();
}

void Game059TrackField::InitAttempt() {
    athlete_x_ = 1.0f;
    athlete_y_ = 13.0f;
    speed_ = 0.0f;
    last_button_pressed_ = 0;
    throw_angle_ = 0.0f;
    angle_rising_ = false;
    throw_distance_ = 0.0f;
    state_ = STATE_RUNNING;
    state_timer_ = 0.0f;
}

void Game059TrackField::TriggerRelease(float angle) {
    throw_angle_ = angle;
    state_ = STATE_FLIGHT;
    state_timer_ = 0.0f;

    float v0 = std::max(6.0f, speed_) * 2.8f;
    float rad = throw_angle_ * DEG2RAD;
    javelin_x_ = athlete_x_;
    javelin_y_ = athlete_y_ - 1.0f;
    javelin_vx_ = v0 * std::cos(rad);
    javelin_vy_ = -v0 * std::sin(rad);

    // Ballistic distance
    throw_distance_ = (v0 * v0 * std::sin(2.0f * rad)) / 9.8f;
    if (throw_distance_ > best_distance_) {
        best_distance_ = throw_distance_;
    }
}

void Game059TrackField::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 2.0f) {
            state_ = STATE_START;
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f) {
            state_ = STATE_RUNNING;
            state_timer_ = 0.0f;
            attempt_ = 1;
            InitAttempt();
        }
        return;
    }

    if (state_ == STATE_FOUL || state_ == STATE_RESULT) {
        if (state_timer_ > 1.8f) {
            if (throw_distance_ >= qualify_distance_) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                score_ += static_cast<int>(throw_distance_ * 50.0f);
                if (score_ > high_score_) high_score_ = score_;
            } else {
                attempt_++;
                if (attempt_ > 3) {
                    state_ = STATE_DEAD;
                    state_timer_ = 0.0f;
                } else {
                    InitAttempt();
                }
            }
        }
        return;
    }

    if (state_ == STATE_RUNNING) {
        UpdateRunning(dt, buttons, prev_buttons);
    } else if (state_ == STATE_ANGLE_AIM) {
        UpdateAiming(dt, buttons, prev_buttons);
    } else if (state_ == STATE_FLIGHT) {
        UpdateFlight(dt);
    }
}

void Game059TrackField::UpdateRunning(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Alternating button-mashing sprint (A and B)
    bool btn_a = (buttons & BUTTON_A) && !(prev_buttons & BUTTON_A);
    bool btn_b = (buttons & BUTTON_B) && !(prev_buttons & BUTTON_B);

    if (btn_a) {
        if (last_button_pressed_ == 2) {
            speed_ = std::min(12.0f, speed_ + 2.0f); // High rhythm boost
        } else {
            speed_ = std::max(0.0f, speed_ - 0.4f); // Stumble
        }
        last_button_pressed_ = 1;
    } else if (btn_b) {
        if (last_button_pressed_ == 1) {
            speed_ = std::min(12.0f, speed_ + 2.0f);
        } else {
            speed_ = std::max(0.0f, speed_ - 0.4f);
        }
        last_button_pressed_ = 2;
    }

    // Natural running drag
    speed_ = std::max(0.0f, speed_ - 3.5f * dt);
    athlete_x_ += speed_ * dt;

    // Approaching foul line: Holding UP initiates Angle Aiming
    if (buttons & BUTTON_UP) {
        state_ = STATE_ANGLE_AIM;
        throw_angle_ = 10.0f;
    }

    // Foul check (Crossed line at x=11.5 without throwing)
    if (athlete_x_ >= 11.5f) {
        state_ = STATE_FOUL;
        state_timer_ = 0.0f;
        throw_distance_ = 0.0f;
        speed_ = 0.0f;
    }
}

void Game059TrackField::UpdateAiming(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Angle continues rising as long as UP or Button is held
    throw_angle_ += 95.0f * dt;
    if (throw_angle_ > 80.0f) throw_angle_ = 80.0f;

    athlete_x_ += speed_ * dt;

    // Check foul line breach
    if (athlete_x_ >= 11.5f) {
        state_ = STATE_FOUL;
        state_timer_ = 0.0f;
        throw_distance_ = 0.0f;
        speed_ = 0.0f;
        return;
    }

    // Release trigger when UP released, or pressing A/B again
    if (!(buttons & BUTTON_UP) || ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A))) {
        TriggerRelease(throw_angle_);
    }
}

void Game059TrackField::UpdateFlight(float dt) {
    javelin_x_ += javelin_vx_ * dt;
    javelin_y_ += javelin_vy_ * dt;
    javelin_vy_ += 20.0f * dt; // Gravity

    // Hits ground
    if (javelin_y_ >= 13.0f) {
        javelin_y_ = 13.0f;
        state_ = STATE_RESULT;
        state_timer_ = 0.0f;
    }
}

void Game059TrackField::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Stadium Crowd (y=0..4: Spectator stands)
    for (int y = 0; y < 5; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            // Spectators (Random colorful crowd)
            fb[idx] = 60 + ((x * 17 + y * 23) % 180);
            fb[idx + 1] = 40 + ((x * 11 + y * 31) % 150);
            fb[idx + 2] = 80 + ((x * 7 + y * 13) % 150);
        }
    }

    // Stadium Field (Green grass y=5..11)
    for (int y = 5; y < 12; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = 30;
            fb[idx + 1] = 160 + (y % 2) * 20;
            fb[idx + 2] = 30; // Emerald turf
        }
    }

    // Tartan Track Runway (Red-orange rubber track y=12..14)
    for (int y = 12; y < 15; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = 200;
            fb[idx + 1] = 60;
            fb[idx + 2] = 40; // Brick red track

            // White runway lines
            if (y == 12 || y == 14) {
                fb[idx] = 240;
                fb[idx + 1] = 240;
                fb[idx + 2] = 240;
            }

            // White Foul Line at x=11
            if (x == 11) {
                fb[idx] = 255;
                fb[idx + 1] = 255;
                fb[idx + 2] = 255;
            }
        }
    }

    // Athlete (White singlet / Blue shorts)
    int ax = static_cast<int>(std::round(athlete_x_));
    int ay = static_cast<int>(std::round(athlete_y_));
    if (ax >= 0 && ax < 16 && ay >= 0 && ay < 16) {
        int idx = (ay * 16 + ax) * 3;
        fb[idx] = 40;
        fb[idx + 1] = 80;
        fb[idx + 2] = 220; // Blue shorts

        if (ay > 0) {
            int body_idx = ((ay - 1) * 16 + ax) * 3;
            fb[body_idx] = 255;
            fb[body_idx + 1] = 255;
            fb[body_idx + 2] = 255; // White shirt
        }
    }

    // Render Javelin
    if (state_ == STATE_FLIGHT || state_ == STATE_RESULT) {
        int jx = static_cast<int>(std::round(javelin_x_));
        int jy = static_cast<int>(std::round(javelin_y_));
        if (jx >= 0 && jx < 16 && jy >= 0 && jy < 16) {
            int idx = (jy * 16 + jx) * 3;
            fb[idx] = 255;
            fb[idx + 1] = 240;
            fb[idx + 2] = 0; // Yellow javelin
        }
    }

    // Foul flag: Red banner
    if (state_ == STATE_FOUL) {
        int idx = (11 * 16 + 11) * 3;
        fb[idx] = 255;
        fb[idx + 1] = 0;
        fb[idx + 2] = 0; // Red foul flag
    }

    // Top HUD: Speed Gauge / Attempt Counter on row 0
    int speed_bars = static_cast<int>((speed_ / 12.0f) * 8.0f);
    for (int s = 0; s < speed_bars && s < 8; ++s) {
        int idx = s * 3;
        fb[idx] = (s > 5) ? 255 : 0;
        fb[idx + 1] = (s > 5) ? 100 : 255;
        fb[idx + 2] = 0;
    }

    // Attempt pips (3 attempts on top-right)
    for (int a = 0; a < 3; ++a) {
        int idx = (15 - a) * 3;
        if (a < attempt_) {
            fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255;
        } else {
            fb[idx] = 60;  fb[idx + 1] = 60;  fb[idx + 2] = 60;
        }
    }
}

} // namespace arcade
