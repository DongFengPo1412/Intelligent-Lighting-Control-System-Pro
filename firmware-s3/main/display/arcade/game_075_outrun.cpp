#include "game_075_outrun.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game075OutRun::Game075OutRun()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(10000),
      car_x_(0.0f),
      car_speed_(0.0f),
      high_gear_(false),
      radio_station_(0),
      road_curve_(0.0f),
      stage_distance_(0.0f),
      stage_length_(1500.0f),
      current_stage_(1),
      time_remaining_(45.0f),
      is_at_fork_(false) {
}

void Game075OutRun::Init() {
    Reset();
}

void Game075OutRun::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    current_stage_ = 1;
    time_remaining_ = 45.0f;
    InitStage();
}

void Game075OutRun::InitStage() {
    car_x_ = 0.0f;
    car_speed_ = 40.0f;
    high_gear_ = false;
    road_curve_ = 0.0f;
    stage_distance_ = 0.0f;
    is_at_fork_ = false;

    // Traffic cars ahead
    traffic_[0] = {-0.4f, 40.0f, 75.0f, 0, true};
    traffic_[1] = {0.3f, 80.0f, 90.0f, 1, true};
    traffic_[2] = {-0.2f, 130.0f, 80.0f, 0, true};

    // Scenery palm trees
    scenery_[0] = {-1.3f, 20.0f, 0, true};
    scenery_[1] = {1.3f, 50.0f, 0, true};
    scenery_[2] = {-1.3f, 80.0f, 0, true};
    scenery_[3] = {1.3f, 110.0f, 1, true};
}

void Game075OutRun::CycleRadio() {
    radio_station_ = (radio_station_ + 1) % 3;
}

void Game075OutRun::ShiftGear() {
    high_gear_ = !high_gear_;
    CycleRadio();
}

void Game075OutRun::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_CRASH) {
        if (state_timer_ > 2.0f) {
            if (time_remaining_ > 0.0f) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                car_speed_ = 30.0f;
                car_x_ = 0.0f;
            } else {
                state_ = STATE_START;
            }
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ > 3.0f) {
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            Reset();
        }
        return;
    }

    time_remaining_ -= dt;
    if (time_remaining_ <= 0.0f) {
        time_remaining_ = 0.0f;
        state_ = STATE_CRASH;
        state_timer_ = 0.0f;
        return;
    }

    UpdateDriving(dt, buttons, prev_buttons);
    UpdateRoad(dt);
    UpdateTraffic(dt);
    CheckCollisions();
}

void Game075OutRun::UpdateDriving(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Steer Ferrari
    float steer_speed = 1.4f;
    if (buttons & BUTTON_LEFT)  car_x_ -= steer_speed * dt;
    if (buttons & BUTTON_RIGHT) car_x_ += steer_speed * dt;

    // Centrifugal curve pull on car
    car_x_ -= road_curve_ * (car_speed_ / 180.0f) * 1.2f * dt;

    // Accelerate / Brake
    float top_speed = high_gear_ ? 180.0f : 105.0f;
    bool accelerating = (buttons & BUTTON_A);

    if (accelerating) {
        car_speed_ = std::min(top_speed, car_speed_ + 50.0f * dt);
    } else {
        car_speed_ = std::max(0.0f, car_speed_ - 30.0f * dt); // Engine braking
    }

    // Off-road grass friction
    if (std::abs(car_x_) > 0.85f) {
        car_speed_ = std::max(0.0f, car_speed_ - 70.0f * dt);
    }

    // Button B: Gear shift & radio
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        ShiftGear();
    }

    // Distance progress & score
    float dist_step = (car_speed_ * 0.28f) * dt;
    stage_distance_ += dist_step;
    score_ += int(dist_step * 2.0f);
    if (score_ > high_score_) high_score_ = score_;
}

void Game075OutRun::UpdateRoad(float dt) {
    // Dynamic road curving using sine wave
    road_curve_ = std::sin(stage_distance_ * 0.005f) * 0.7f;

    // Checkpoint / Fork detection
    if (stage_distance_ >= 1350.0f) {
        is_at_fork_ = true;
    }

    if (stage_distance_ >= stage_length_) {
        // Stage checkpoint reached!
        time_remaining_ += 25.0f;
        score_ += 1000;
        current_stage_++;

        if (current_stage_ > 3) {
            // Reached goal finish arch!
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            score_ += 5000;
            if (score_ > high_score_) high_score_ = score_;
            return;
        } else {
            // Enter chosen branched stage!
            stage_distance_ = 0.0f;
            is_at_fork_ = false;
        }
    }
}

void Game075OutRun::UpdateTraffic(float dt) {
    float player_vel = car_speed_ * 0.28f;

    for (int i = 0; i < MAX_CARS; ++i) {
        if (!traffic_[i].active) continue;

        float rel_speed = (traffic_[i].speed * 0.28f) - player_vel;
        traffic_[i].distance += rel_speed * dt;

        // Respawn ahead or behind
        if (traffic_[i].distance < -10.0f) {
            traffic_[i].distance = 120.0f + (i * 30.0f);
            traffic_[i].x = ((i % 2 == 0) ? -0.4f : 0.4f);
        } else if (traffic_[i].distance > 180.0f) {
            traffic_[i].distance = 120.0f;
        }
    }

    // Scenery motion
    for (int i = 0; i < MAX_SCENERY; ++i) {
        if (!scenery_[i].active) continue;
        scenery_[i].distance -= player_vel * dt;
        if (scenery_[i].distance < 0.0f) {
            scenery_[i].distance = 120.0f;
        }
    }
}

void Game075OutRun::CheckCollisions() {
    // Traffic collision
    for (int i = 0; i < MAX_CARS; ++i) {
        if (!traffic_[i].active) continue;

        if (std::abs(traffic_[i].distance) < 2.0f && std::abs(car_x_ - traffic_[i].x) < 0.35f) {
            // Collision crash!
            state_ = STATE_CRASH;
            state_timer_ = 0.0f;
            car_speed_ = 0.0f;
            time_remaining_ = std::max(0.0f, time_remaining_ - 3.0f);
            return;
        }
    }

    // Roadside obstacle crash
    if (std::abs(car_x_) > 1.25f) {
        state_ = STATE_CRASH;
        state_timer_ = 0.0f;
        car_speed_ = 0.0f;
        time_remaining_ = std::max(0.0f, time_remaining_ - 3.0f);
        return;
    }
}

void Game075OutRun::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Sky & Horizon (Blue sky / Orange sunset gradient)
    for (int y = 0; y < 8; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (y <= 3) set_pixel(x, y, 40, 100, 220); // Sky
            else set_pixel(x, y, 240, 140, 60);        // Sunset horizon
        }
    }

    // 2. Road Perspective (y=8 to 15)
    for (int y = 8; y < 16; ++y) {
        float t = float(y - 8) / 7.0f; // 0.0 (horizon) to 1.0 (hood)
        float road_half_width = 1.5f + t * 5.5f;
        float curve_offset = road_curve_ * (1.0f - t) * 4.0f;
        float center_x = 7.5f + curve_offset;

        for (int x = 0; x < 16; ++x) {
            float dist_from_center = std::abs(float(x) - center_x);
            if (dist_from_center <= road_half_width) {
                // Tarmac road
                bool stripe = (int(stage_distance_ * 0.15f + y) % 2 == 0);
                if (dist_from_center >= road_half_width - 0.8f) {
                    // Red/white kerb rumble strips
                    set_pixel(x, y, stripe ? 255 : 255, stripe ? 30 : 255, stripe ? 30 : 255);
                } else if (dist_from_center <= 0.6f) {
                    // White dashed center line
                    set_pixel(x, y, stripe ? 240 : 80, stripe ? 240 : 80, stripe ? 240 : 90);
                } else {
                    // Dark grey asphalt
                    set_pixel(x, y, 70, 75, 85);
                }
            } else {
                // Roadside grass / sand
                bool grass_stripe = (int(stage_distance_ * 0.15f + y) % 2 == 0);
                set_pixel(x, y, 40, grass_stripe ? 150 : 130, 40);
            }
        }
    }

    // 3. Fork Banner Arch
    if (is_at_fork_) {
        for (int x = 3; x <= 12; ++x) {
            set_pixel(x, 7, 255, 215, 0); // Yellow checkpoint arch
        }
    }

    // 4. Scenery (Palm Trees)
    for (int i = 0; i < MAX_SCENERY; ++i) {
        if (!scenery_[i].active) continue;
        float t = std::max(0.0f, std::min(1.0f, 1.0f - (scenery_[i].distance / 120.0f)));
        if (t > 0.1f) {
            int sy = 8 + int(t * 6.0f);
            int sx = int(std::round(7.5f + scenery_[i].x * (2.0f + t * 5.0f)));
            set_pixel(sx, sy, 30, 160, 40);     // Green palm frond
            set_pixel(sx, sy - 1, 30, 180, 50);
            set_pixel(sx, sy + 1, 140, 90, 40); // Trunk
        }
    }

    // 5. Traffic Cars Ahead
    for (int i = 0; i < MAX_CARS; ++i) {
        if (!traffic_[i].active || traffic_[i].distance <= 0.0f) continue;
        float t = std::max(0.0f, std::min(1.0f, 1.0f - (traffic_[i].distance / 120.0f)));
        if (t > 0.15f) {
            int cy = 8 + int(t * 5.5f);
            int cx = int(std::round(7.5f + traffic_[i].x * (2.0f + t * 5.0f)));
            if (traffic_[i].color_type == 0) {
                set_pixel(cx, cy, 40, 100, 240); // Blue car
                set_pixel(cx + 1, cy, 40, 100, 240);
            } else {
                set_pixel(cx, cy, 255, 220, 20); // Yellow truck
                set_pixel(cx + 1, cy, 255, 220, 20);
            }
        }
    }

    // 6. Player Ferrari Testarossa (Red convertible)
    if (state_ != STATE_CRASH) {
        int fx = int(std::round(7.5f + car_x_ * 5.0f));
        int fy = 14;

        // Red body
        set_pixel(fx - 1, fy, 230, 20, 20);
        set_pixel(fx,     fy, 255, 30, 30);
        set_pixel(fx + 1, fy, 230, 20, 20);

        // Black rear grille & dual exhaust
        set_pixel(fx - 1, fy + 1, 20, 20, 20);
        set_pixel(fx + 1, fy + 1, 20, 20, 20);
        set_pixel(fx,     fy + 1, 255, 140, 0); // Tail lights

        // Driver & Passenger (Brown hair & blond passenger)
        set_pixel(fx - 1, fy - 1, 120, 60, 20);  // Brown hair driver
        set_pixel(fx + 1, fy - 1, 255, 220, 50); // Blond passenger
    } else {
        // Crash spin-out explosion
        int fx = int(std::round(7.5f + car_x_ * 5.0f));
        int fy = 14;
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dx = -1; dx <= 1; ++dx) {
                set_pixel(fx + dx, fy + dy, 255, 100, 20);
            }
        }
    }

    // 7. HUD (Top line)
    // Speed gauge (bars)
    int spd_bars = int((car_speed_ / 180.0f) * 6.0f);
    for (int b = 0; b < spd_bars; ++b) {
        set_pixel(b, 0, 40, 255, 60);
    }
    // High gear indicator (H)
    if (high_gear_) set_pixel(7, 0, 255, 215, 0);

    // Radio cassette color indicator
    uint8_t rr = (radio_station_ == 0) ? 255 : 50;
    uint8_t rg = (radio_station_ == 1) ? 255 : 50;
    uint8_t rb = (radio_station_ == 2) ? 255 : 50;
    set_pixel(15, 0, rr, rg, rb);
}

} // namespace arcade
