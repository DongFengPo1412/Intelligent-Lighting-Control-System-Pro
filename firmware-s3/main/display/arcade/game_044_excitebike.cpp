#include "game_044_excitebike.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

Game044Excitebike::Game044Excitebike()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      world_x_(0.0f),
      speed_(0.0f),
      lane_(1),
      altitude_(0.0f),
      vertical_vy_(0.0f),
      pitch_angle_(0.0f),
      is_airborne_(false),
      engine_temp_(0.0f),
      crash_recovery_timer_(0.0f) {
}

void Game044Excitebike::Init() {
    Reset();
}

void Game044Excitebike::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    world_x_ = 0.0f;
    speed_ = 0.0f;
    lane_ = 1;
    altitude_ = 0.0f;
    vertical_vy_ = 0.0f;
    pitch_angle_ = 0.0f;
    is_airborne_ = false;
    engine_temp_ = 0.0f;
    crash_recovery_timer_ = 0.0f;

    InitTrack();
}

void Game044Excitebike::InitTrack() {
    // Layout 16 obstacles along the 120-tile dirt track
    static const struct {
        float wx;
        int lane;
        ObstacleType type;
    } track_data[NUM_OBSTACLES] = {
        {12.0f, 1, OBS_SMALL_RAMP},
        {18.0f, 2, OBS_MUD_PUDDLE},
        {25.0f, 1, OBS_COOLING_STRIP},
        {32.0f, 0, OBS_BIG_RAMP},
        {38.0f, 3, OBS_MUD_PUDDLE},
        {45.0f, 2, OBS_SMALL_RAMP},
        {52.0f, 1, OBS_COOLING_STRIP},
        {58.0f, 2, OBS_BIG_RAMP},
        {66.0f, 0, OBS_MUD_PUDDLE},
        {74.0f, 3, OBS_SMALL_RAMP},
        {80.0f, 1, OBS_COOLING_STRIP},
        {88.0f, 2, OBS_BIG_RAMP},
        {95.0f, 0, OBS_MUD_PUDDLE},
        {102.0f, 1, OBS_SMALL_RAMP},
        {108.0f, 2, OBS_COOLING_STRIP},
        {114.0f, 3, OBS_BIG_RAMP}
    };

    for (int i = 0; i < NUM_OBSTACLES; ++i) {
        obstacles_[i].world_x = track_data[i].wx;
        obstacles_[i].lane = track_data[i].lane;
        obstacles_[i].type = track_data[i].type;
    }
}

void Game044Excitebike::TriggerCrash() {
    state_ = STATE_CRASH;
    speed_ = 0.0f;
    is_airborne_ = false;
    altitude_ = 0.0f;
    vertical_vy_ = 0.0f;
    pitch_angle_ = 0.0f;
    crash_recovery_timer_ = 1.8f;
}

void Game044Excitebike::CheckTerrainCollisions() {
    if (is_airborne_) return; // Flying above terrain

    for (int i = 0; i < NUM_OBSTACLES; ++i) {
        if (obstacles_[i].lane != lane_) continue;

        float dist = fabsf(world_x_ - obstacles_[i].world_x);
        if (dist <= 0.65f) {
            switch (obstacles_[i].type) {
                case OBS_SMALL_RAMP:
                    is_airborne_ = true;
                    altitude_ = 0.1f;
                    vertical_vy_ = 7.5f;
                    pitch_angle_ = -0.3f; // Slight nose-up launch
                    break;
                case OBS_BIG_RAMP:
                    is_airborne_ = true;
                    altitude_ = 0.1f;
                    vertical_vy_ = 11.5f;
                    pitch_angle_ = -0.45f; // Steep launch
                    break;
                case OBS_MUD_PUDDLE:
                    speed_ *= 0.4f; // Severe mud drag
                    break;
                case OBS_COOLING_STRIP:
                    engine_temp_ = 0.0f; // Rapid cooling
                    score_ += 20;
                    if (score_ > high_score_) high_score_ = score_;
                    break;
                default:
                    break;
            }
        }
    }
}

void Game044Excitebike::UpdateBike(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // 1. Lane switching on ground
    if (!is_airborne_) {
        if ((buttons & KEY_UP) && !(prev_buttons & KEY_UP)) {
            if (lane_ > 0) lane_--;
        }
        if ((buttons & KEY_DOWN) && !(prev_buttons & KEY_DOWN)) {
            if (lane_ < 3) lane_++;
        }
    }

    // 2. Throttle & Engine heat
    if (!is_airborne_) {
        if (buttons & KEY_B) {
            // Turbo boost
            float target_speed = 18.0f;
            speed_ += (target_speed - speed_) * 4.0f * dt;
            engine_temp_ += 25.0f * dt;
        } else if (buttons & KEY_A) {
            // Normal throttle
            float target_speed = 11.0f;
            speed_ += (target_speed - speed_) * 5.0f * dt;
            engine_temp_ += 6.0f * dt;
        } else {
            // Coasting deceleration & cooling
            speed_ = std::max(0.0f, speed_ - 8.0f * dt);
            engine_temp_ = std::max(0.0f, engine_temp_ - 15.0f * dt);
        }
    } else {
        // In air: engine continues cooling
        engine_temp_ = std::max(0.0f, engine_temp_ - 10.0f * dt);
    }

    // Engine overheat check
    if (engine_temp_ >= 100.0f) {
        engine_temp_ = 100.0f;
        state_ = STATE_OVERHEAT;
        speed_ = 0.0f;
        state_timer_ = 0.0f;
        return;
    }

    // 3. World distance advance
    world_x_ += speed_ * dt;
    score_ += static_cast<int32_t>(speed_ * dt * 5.0f);
    if (score_ > high_score_) high_score_ = score_;

    // 4. Airborne dynamics and pitch control
    if (is_airborne_) {
        const float gravity = 22.0f;
        vertical_vy_ -= gravity * dt;
        altitude_ += vertical_vy_ * dt;

        // Pitch attitude adjustments
        if (buttons & KEY_LEFT)  pitch_angle_ -= 2.6f * dt; // Tilt tail down / nose up
        if (buttons & KEY_RIGHT) pitch_angle_ += 2.6f * dt; // Tilt nose down

        pitch_angle_ = std::max(-1.0f, std::min(1.0f, pitch_angle_));

        // Touchdown landing check
        if (altitude_ <= 0.0f) {
            altitude_ = 0.0f;
            vertical_vy_ = 0.0f;
            is_airborne_ = false;

            // Check landing angle: safe tolerance between -0.4 and +0.4
            if (fabsf(pitch_angle_) > 0.42f) {
                TriggerCrash();
                return;
            } else {
                // Smooth landing bonus
                score_ += 50;
                if (score_ > high_score_) high_score_ = score_;
                pitch_angle_ = 0.0f;
            }
        }
    } else {
        pitch_angle_ = 0.0f;
    }

    // Check terrain collisions
    CheckTerrainCollisions();

    // Finish line check
    if (world_x_ >= static_cast<float>(TRACK_LENGTH)) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 2000;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game044Excitebike::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_CRASH) {
        crash_recovery_timer_ -= dt;
        if (crash_recovery_timer_ <= 0.0f) {
            state_ = STATE_PLAYING;
            speed_ = 3.0f; // Initial push restart
        }
        return;
    }

    if (state_ == STATE_OVERHEAT) {
        engine_temp_ = std::max(0.0f, engine_temp_ - 35.0f * dt);
        if (engine_temp_ <= 0.0f) {
            state_ = STATE_PLAYING;
            speed_ = 2.0f;
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ >= 2.5f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    UpdateBike(dt, buttons, prev_buttons);
}

void Game044Excitebike::Render(uint8_t* fb) {
    // 1. Sky & Bleachers background (rows 0..6)
    for (int y = 0; y < 7; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx + 0] = 20;
            fb[idx + 1] = 30;
            fb[idx + 2] = 55; // Deep stadium navy
        }
    }

    // Top Row HUD: Engine Temp gauge (x: 0..7) & Track Progress (x: 9..15)
    int temp_bars = static_cast<int>(std::round((engine_temp_ / 100.0f) * 7.0f));
    for (int x = 0; x < 8; ++x) {
        int idx = (0 * 16 + x) * 3;
        if (x < temp_bars) {
            if (engine_temp_ > 80.0f) {
                fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Flashing Red
            } else if (engine_temp_ > 50.0f) {
                fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15; // Warning Yellow
            } else {
                fb[idx + 0] = 46; fb[idx + 1] = 204; fb[idx + 2] = 113; // Safe Green
            }
        }
    }

    // Track Progress on row 0 right side
    int prog_x = 9 + static_cast<int>(std::round((world_x_ / static_cast<float>(TRACK_LENGTH)) * 6.0f));
    prog_x = std::min(15, std::max(9, prog_x));
    int p_idx = (0 * 16 + prog_x) * 3;
    fb[p_idx + 0] = 255; fb[p_idx + 1] = 255; fb[p_idx + 2] = 255; // White marker

    // 2. Track Turf & Grass (row 7 and rows 12..15)
    for (int y = 7; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (y >= 8 && y <= 11) {
                // Dirt Lanes (Golden Brown #784212 / #A04000)
                fb[idx + 0] = 120;
                fb[idx + 1] = 66;
                fb[idx + 2] = 18;
            } else {
                // Stadium green turf
                fb[idx + 0] = 30;
                fb[idx + 1] = 100;
                fb[idx + 2] = 40;
            }
        }
    }

    // 3. Render Obstacles relative to Camera (Player fixed at screen column x = 3)
    float cam_left = world_x_ - 3.0f;
    for (int i = 0; i < NUM_OBSTACLES; ++i) {
        float rel_x = obstacles_[i].world_x - cam_left;
        int sx = static_cast<int>(std::round(rel_x));
        int sy = 8 + obstacles_[i].lane;

        if (sx >= 0 && sx < 16 && sy >= 8 && sy <= 11) {
            int idx = (sy * 16 + sx) * 3;
            switch (obstacles_[i].type) {
                case OBS_SMALL_RAMP:
                case OBS_BIG_RAMP:
                    fb[idx + 0] = 243; fb[idx + 1] = 156; fb[idx + 2] = 18; // Yellow Ramp
                    break;
                case OBS_MUD_PUDDLE:
                    fb[idx + 0] = 52;  fb[idx + 1] = 73;  fb[idx + 2] = 94;  // Mud Puddle
                    break;
                case OBS_COOLING_STRIP:
                    fb[idx + 0] = 41;  fb[idx + 1] = 128; fb[idx + 2] = 185; // Cool Blue
                    break;
                default:
                    break;
            }
        }
    }

    // 4. Render Motocross Bike (Screen column x = 3, y = 8 + lane - altitude)
    int px = 3;
    int py = 8 + lane_ - static_cast<int>(std::round(altitude_));
    py = std::max(1, std::min(15, py));

    int b_idx = (py * 16 + px) * 3;
    if (state_ == STATE_CRASH) {
        fb[b_idx + 0] = 255; fb[b_idx + 1] = 80; fb[b_idx + 2] = 0; // Orange tumble
    } else if (state_ == STATE_OVERHEAT) {
        // Flashing steam / smoke
        fb[b_idx + 0] = 180; fb[b_idx + 1] = 180; fb[b_idx + 2] = 180;
    } else {
        // Red Motocross Bike
        fb[b_idx + 0] = 231; fb[b_idx + 1] = 76; fb[b_idx + 2] = 60;
    }
}

} // namespace arcade
