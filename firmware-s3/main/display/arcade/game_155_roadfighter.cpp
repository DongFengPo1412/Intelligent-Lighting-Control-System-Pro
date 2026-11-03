#include "game_155_roadfighter.h"
#include <cstring>
#include <cmath>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = (1 << 0);
static constexpr uint16_t BTN_DOWN  = (1 << 1);
static constexpr uint16_t BTN_LEFT  = (1 << 2);
static constexpr uint16_t BTN_RIGHT = (1 << 3);
static constexpr uint16_t BTN_A     = (1 << 4);
static constexpr uint16_t BTN_B     = (1 << 5);

Game155RoadFighter::Game155RoadFighter() {
    Reset();
}

void Game155RoadFighter::Init() {
    Reset();
}

void Game155RoadFighter::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitRace();
}

void Game155RoadFighter::InitRace() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    speed_ = 100.0f;
    distance_ = 0.0f;
    fuel_ = 100.0f;

    is_slipping_ = false;
    slip_dir_ = 0.0f;
    slip_counter_steer_time_ = 0.0f;
    road_scroll_ = 0.0f;

    traffic_[0] = {5.0f, 2.0f, 140.0f, false};
    traffic_[1] = {10.0f, -4.0f, 120.0f, true};
    traffic_[2] = {7.0f, -12.0f, 150.0f, false};

    oil_slicks_[0] = {6.5f, -8.0f};
    oil_slicks_[1] = {9.0f, -22.0f};

    rainbow_car_ = {8.5f, -18.0f, 160.0f, true};
}

void Game155RoadFighter::Crash() {
    lives_--;
    fuel_ = std::max(0.0f, fuel_ - 15.0f);
    speed_ = 0.0f;
    state_ = STATE_CAR_CRASHED;
    state_timer_ = 0.0f;
}

void Game155RoadFighter::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // 1. Gears
        float target_max_speed = 0.0f;
        float accel = 0.0f;
        if (buttons & BTN_A) {
            target_max_speed = 400.0f;
            accel = 120.0f;
        } else if (buttons & BTN_B) {
            target_max_speed = 200.0f;
            accel = 150.0f;
        } else {
            target_max_speed = 0.0f;
            accel = -80.0f;
        }

        if (speed_ < target_max_speed) {
            speed_ = std::min(target_max_speed, speed_ + accel * dt);
        } else if (speed_ > target_max_speed) {
            speed_ = std::max(0.0f, speed_ - 90.0f * dt);
        }

        // 2. Fuel & Distance
        float fuel_rate = 1.2f + (speed_ / 400.0f) * 3.5f;
        fuel_ = std::max(0.0f, fuel_ - fuel_rate * dt);
        if (fuel_ <= 0.0f && speed_ < 10.0f) {
            lives_ = 0;
            state_ = STATE_CAR_CRASHED;
            return;
        }

        float dist_advance = (speed_ / 36.0f) * dt;
        distance_ += dist_advance;
        road_scroll_ += (speed_ / 20.0f) * dt;

        // 3. Steering & Slip
        float steer_speed = 6.0f;
        if (!is_slipping_) {
            if (buttons & BTN_LEFT)  px_ -= steer_speed * dt;
            if (buttons & BTN_RIGHT) px_ += steer_speed * dt;
        } else {
            px_ += slip_dir_ * 8.5f * dt;

            bool counter_steer = false;
            if (slip_dir_ > 0.0f && (buttons & BTN_LEFT)) counter_steer = true;
            else if (slip_dir_ < 0.0f && (buttons & BTN_RIGHT)) counter_steer = true;

            if (counter_steer) {
                slip_counter_steer_time_ += dt;
                if (slip_counter_steer_time_ >= 0.2f) {
                    is_slipping_ = false;
                    slip_dir_ = 0.0f;
                    slip_counter_steer_time_ = 0.0f;
                    score_ += 200;
                }
            } else {
                slip_counter_steer_time_ = std::max(0.0f, slip_counter_steer_time_ - dt * 2.0f);
            }
        }

        if (px_ <= ROAD_LEFT || px_ >= ROAD_RIGHT) {
            Crash();
            return;
        }

        // 4. Traffic
        for (int i = 0; i < MAX_TRAFFIC; ++i) {
            float rel_speed = (speed_ - traffic_[i].speed) / 25.0f;
            traffic_[i].y += rel_speed * dt;

            if (std::abs(traffic_[i].y - 13.0f) < 1.2f && std::abs(traffic_[i].x - px_) < 1.0f) {
                if (!is_slipping_) {
                    is_slipping_ = true;
                    slip_dir_ = (px_ < traffic_[i].x) ? 1.0f : -1.0f;
                    slip_counter_steer_time_ = 0.0f;
                    speed_ = std::max(60.0f, speed_ - 50.0f);
                }
            }

            if (traffic_[i].y > 18.0f) {
                traffic_[i].y = -5.0f - (i * 4.0f);
                traffic_[i].x = ROAD_LEFT + 1.0f + static_cast<int>(distance_) % 8;
                score_ += 50;
            }
        }

        // 5. Oil Slicks
        for (int i = 0; i < MAX_OIL; ++i) {
            oil_slicks_[i].y += (speed_ / 25.0f) * dt;
            if (std::abs(oil_slicks_[i].y - 13.0f) < 0.9f && std::abs(oil_slicks_[i].x - px_) < 1.0f) {
                if (!is_slipping_) {
                    is_slipping_ = true;
                    slip_dir_ = (px_ <= 7.5f) ? 1.0f : -1.0f;
                    slip_counter_steer_time_ = 0.0f;
                }
            }
            if (oil_slicks_[i].y > 18.0f) {
                oil_slicks_[i].y = -15.0f;
                oil_slicks_[i].x = ROAD_LEFT + 2.0f + (static_cast<int>(distance_ * 3) % 6);
            }
        }

        // 6. Rainbow Car
        if (rainbow_car_.active) {
            float rel_speed = (speed_ - rainbow_car_.speed) / 25.0f;
            rainbow_car_.y += rel_speed * dt;

            if (std::abs(rainbow_car_.y - 13.0f) < 1.2f && std::abs(rainbow_car_.x - px_) < 1.2f) {
                rainbow_car_.active = false;
                fuel_ = std::min(100.0f, fuel_ + 30.0f);
                score_ += 1000;
            }

            if (rainbow_car_.y > 18.0f) {
                rainbow_car_.y = -25.0f;
                rainbow_car_.active = true;
            }
        }

        // 7. Finish
        if (distance_ >= TOTAL_DISTANCE) {
            score_ += 3000;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
        }

    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_CAR_CRASHED) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitRace();
            } else {
                if (lives_ > 0 && fuel_ > 5.0f) {
                    px_ = 7.5f;
                    speed_ = 80.0f;
                    is_slipping_ = false;
                    slip_dir_ = 0.0f;
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

void Game155RoadFighter::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Road Surface & Curbs
    for (int y = 0; y < 16; ++y) {
        set_pixel(0, y, 40, 140, 40);
        set_pixel(1, y, 50, 160, 50);
        set_pixel(14, y, 50, 160, 50);
        set_pixel(15, y, 40, 140, 40);

        uint8_t curb_r = (static_cast<int>(y + road_scroll_) % 2 == 0) ? 240 : 240;
        uint8_t curb_g = (static_cast<int>(y + road_scroll_) % 2 == 0) ? 40 : 240;
        uint8_t curb_b = (static_cast<int>(y + road_scroll_) % 2 == 0) ? 40 : 240;
        set_pixel(2, y, curb_r, curb_g, curb_b);
        set_pixel(13, y, curb_r, curb_g, curb_b);

        for (int x = 3; x <= 12; ++x) set_pixel(x, y, 50, 50, 55);

        if (static_cast<int>(y + road_scroll_ * 1.5f) % 4 < 2) {
            set_pixel(7, y, 220, 220, 220);
            set_pixel(8, y, 220, 220, 220);
        }
    }

    // 2. Oil
    for (int i = 0; i < MAX_OIL; ++i) {
        int ox = static_cast<int>(std::round(oil_slicks_[i].x));
        int oy = static_cast<int>(std::round(oil_slicks_[i].y));
        set_pixel(ox, oy, 20, 20, 25);
        if (ox + 1 < 16) set_pixel(ox + 1, oy, 20, 20, 25);
    }

    // 3. Traffic
    for (int i = 0; i < MAX_TRAFFIC; ++i) {
        int cx = static_cast<int>(std::round(traffic_[i].x));
        int cy = static_cast<int>(std::round(traffic_[i].y));
        if (!traffic_[i].is_truck) {
            set_pixel(cx, cy, 240, 200, 30);
            if (cy - 1 >= 0) set_pixel(cx, cy - 1, 200, 160, 20);
        } else {
            set_pixel(cx, cy, 60, 140, 220);
            if (cy - 1 >= 0) set_pixel(cx, cy - 1, 40, 100, 180);
        }
    }

    // 4. Rainbow Car
    if (rainbow_car_.active) {
        int rx = static_cast<int>(std::round(rainbow_car_.x));
        int ry = static_cast<int>(std::round(rainbow_car_.y));
        set_pixel(rx, ry, 255, 60, 220);
        if (ry - 1 >= 0) set_pixel(rx, ry - 1, 80, 255, 200);
    }

    // 5. Player Car
    int px = static_cast<int>(std::round(px_));
    int py = 13;
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 240, 30, 30);
        set_pixel(px, py - 1, 255, 60, 60);
        if (px - 1 >= 0) set_pixel(px - 1, py, 40, 40, 40);
        if (px + 1 < 16) set_pixel(px + 1, py, 40, 40, 40);
        if (is_slipping_) {
            if (px - 1 >= 0 && py + 1 < 16) set_pixel(px - 1, py + 1, 255, 200, 50);
            if (px + 1 < 16 && py + 1 < 16) set_pixel(px + 1, py + 1, 255, 200, 50);
        }
    } else if (state_ == STATE_CAR_CRASHED) {
        set_pixel(px, py, 255, 120, 30);
        set_pixel(px, py - 1, 255, 220, 50);
    }

    // 6. Fuel & Distance Gauges
    int fuel_h = static_cast<int>((fuel_ / 100.0f) * 8.0f);
    for (int fy = 0; fy < fuel_h; ++fy) set_pixel(0, 15 - fy, 40, 220, 80);

    int dist_h = static_cast<int>((distance_ / TOTAL_DISTANCE) * 8.0f);
    for (int dy = 0; dy < dist_h; ++dy) set_pixel(15, 15 - dy, 255, 200, 40);
}

} // namespace arcade

