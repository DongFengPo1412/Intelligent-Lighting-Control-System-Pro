#include "game_141_firetruck.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = (1 << 0);
static constexpr uint16_t BTN_DOWN  = (1 << 1);
static constexpr uint16_t BTN_LEFT  = (1 << 2);
static constexpr uint16_t BTN_RIGHT = (1 << 3);
static constexpr uint16_t BTN_A     = (1 << 4);
static constexpr uint16_t BTN_B     = (1 << 5);

Game141FireTruck::Game141FireTruck()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      time_left_(40.0f),
      distance_(0.0f),
      target_distance_(100.0f),
      speed_(6.0f),
      cx_(7.5f),
      cy_(9.0f),
      cab_vx_(0.0f),
      tx_(7.5f),
      ty_(12.0f),
      hitch_angle_(0.0f),
      road_width_(7.0f) {
    Reset();
}

void Game141FireTruck::Init() {
    Reset();
}

void Game141FireTruck::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game141FireTruck::InitRoad() {
    for (int y = 0; y < 16; ++y) {
        road_center_[y] = 7.5f + std::sin((y + distance_) * 0.3f) * 2.5f;
    }
}

void Game141FireTruck::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    time_left_ = 40.0f;
    distance_ = 0.0f;
    speed_ = 6.0f;

    cx_ = 7.5f;
    cy_ = 9.0f;
    cab_vx_ = 0.0f;

    tx_ = 7.5f;
    ty_ = 12.0f;
    hitch_angle_ = 0.0f;

    InitRoad();

    float ox[NUM_OBSTACLES] = {6.5f, 9.0f, 7.0f, 8.5f};
    float oy[NUM_OBSTACLES] = {-5.0f, -15.0f, -25.0f, -35.0f};
    uint8_t ot[NUM_OBSTACLES] = {0, 1, 0, 1};

    for (int i = 0; i < NUM_OBSTACLES; ++i) {
        obstacles_[i].x = ox[i];
        obstacles_[i].y = oy[i];
        obstacles_[i].type = ot[i];
        obstacles_[i].alive = true;
    }
}

void Game141FireTruck::Crash() {
    if (lives_ > 0) lives_--;
    state_ = STATE_CRASH;
    state_timer_ = 0.0f;
}

void Game141FireTruck::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        time_left_ -= dt;
        if (time_left_ <= 0.0f) {
            time_left_ = 0.0f;
            Crash();
            return;
        }

        // Acceleration
        float target_speed = 7.0f;
        if (buttons & BTN_UP) target_speed = 10.0f;
        else if (buttons & BTN_DOWN) target_speed = 3.5f;

        speed_ += (target_speed - speed_) * 4.0f * dt;
        distance_ += speed_ * dt;
        score_ += static_cast<uint32_t>(speed_ * dt * 2.0f);

        if (distance_ >= target_distance_) {
            score_ += 1000;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
            return;
        }

        // Steer front cab
        float steer_rate = 6.0f;
        if (buttons & BTN_LEFT)  cab_vx_ = -steer_rate;
        else if (buttons & BTN_RIGHT) cab_vx_ = steer_rate;
        else cab_vx_ *= 0.85f;

        cx_ += cab_vx_ * dt;

        // Rear tiller counter-steer
        float tiller_offset = 0.0f;
        if (buttons & BTN_A) tiller_offset -= 3.5f;
        if (buttons & BTN_B) tiller_offset += 3.5f;

        // Articulated trailer follow physics
        float dx = cx_ - tx_;
        float trailer_follow_rate = 4.5f;
        tx_ += (dx * trailer_follow_rate + tiller_offset) * dt;

        hitch_angle_ = (cx_ - tx_) / 2.5f;
        if (std::abs(hitch_angle_) > 1.0f) {
            Crash();
            return;
        }

        // Road curve update
        for (int y = 0; y < 16; ++y) {
            road_center_[y] = 7.5f + std::sin((y - distance_ * 0.8f) * 0.25f) * 3.0f;
        }

        // Road boundaries
        float c_mid = road_center_[9];
        if (std::abs(cx_ - c_mid) > (road_width_ / 2.0f - 0.6f)) {
            Crash();
            return;
        }
        float t_mid = road_center_[12];
        if (std::abs(tx_ - t_mid) > (road_width_ / 2.0f - 0.6f)) {
            Crash();
            return;
        }

        // Obstacles
        for (int i = 0; i < NUM_OBSTACLES; ++i) {
            if (obstacles_[i].alive) {
                obstacles_[i].y += speed_ * dt;
                if (obstacles_[i].y > 16.0f) {
                    obstacles_[i].y = -10.0f - static_cast<float>(static_cast<int>(distance_) % 20);
                    obstacles_[i].x = road_center_[0] + ((static_cast<int>(obstacles_[i].y) % 2 == 0) ? 1.0f : -1.0f);
                }

                if (std::abs(obstacles_[i].y - cy_) < 1.0f && std::abs(obstacles_[i].x - cx_) < 1.0f) {
                    if (obstacles_[i].type == 0) {
                        Crash();
                        return;
                    } else {
                        tx_ += ((cab_vx_ >= 0.0f) ? 4.0f : -4.0f) * dt * 8.0f;
                    }
                }

                if (std::abs(obstacles_[i].y - ty_) < 1.0f && std::abs(obstacles_[i].x - tx_) < 1.0f) {
                    if (obstacles_[i].type == 0) {
                        Crash();
                        return;
                    } else {
                        tx_ += 2.0f;
                    }
                }
            }
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_CRASH) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_CRASH) {
                if (lives_ > 0) {
                    cx_ = 7.5f;
                    tx_ = 7.5f;
                    cab_vx_ = 0.0f;
                    hitch_angle_ = 0.0f;
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

void Game141FireTruck::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Road & Sidewalks
    for (int y = 0; y < 16; ++y) {
        float mid = road_center_[y];
        int left_e = static_cast<int>(std::round(mid - road_width_ / 2.0f));
        int right_e = static_cast<int>(std::round(mid + road_width_ / 2.0f));

        for (int x = 0; x < left_e; ++x) set_pixel(x, y, 40, 50, 40);
        for (int x = right_e + 1; x < 16; ++x) set_pixel(x, y, 40, 50, 40);

        set_pixel(left_e, y, 220, 220, 220);
        set_pixel(right_e, y, 220, 220, 220);

        for (int x = left_e + 1; x < right_e; ++x) set_pixel(x, y, 25, 25, 30);

        if ((static_cast<int>(distance_ + y) % 4) < 2) {
            set_pixel(static_cast<int>(std::round(mid)), y, 240, 220, 60);
        }
    }

    // Obstacles
    for (int i = 0; i < NUM_OBSTACLES; ++i) {
        if (obstacles_[i].alive && obstacles_[i].y >= 0.0f && obstacles_[i].y < 16.0f) {
            int ox = static_cast<int>(std::round(obstacles_[i].x));
            int oy = static_cast<int>(std::round(obstacles_[i].y));
            if (obstacles_[i].type == 0) {
                set_pixel(ox, oy, 60, 140, 240);
                set_pixel(ox, oy - 1, 200, 200, 255);
            } else {
                set_pixel(ox, oy, 20, 20, 20);
                set_pixel(ox + 1, oy, 40, 30, 20);
            }
        }
    }

    // Coupling
    for (int s = 1; s <= 2; ++s) {
        float t = s / 3.0f;
        int hx = static_cast<int>(std::round(cx_ + (tx_ - cx_) * t));
        int hy = static_cast<int>(std::round(cy_ + (ty_ - cy_) * t));
        set_pixel(hx, hy, 180, 180, 190);
    }

    // Trailer & Cab
    int cx_i = static_cast<int>(std::round(cx_));
    int cy_i = static_cast<int>(std::round(cy_));
    int tx_i = static_cast<int>(std::round(tx_));
    int ty_i = static_cast<int>(std::round(ty_));

    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        // Trailer
        set_pixel(tx_i, ty_i, 230, 30, 30);
        set_pixel(tx_i - 1, ty_i, 180, 20, 20);
        set_pixel(tx_i, ty_i - 1, 220, 220, 240);
        set_pixel(tx_i, ty_i + 1, 220, 30, 30);
        set_pixel(tx_i + 1, ty_i, 180, 20, 20);

        // Cab
        set_pixel(cx_i, cy_i, 240, 30, 30);
        set_pixel(cx_i - 1, cy_i, 200, 25, 25);
        set_pixel(cx_i + 1, cy_i, 200, 25, 25);
        set_pixel(cx_i, cy_i - 1, 255, 255, 255);

        int flash = static_cast<int>(distance_ * 4.0f) % 2;
        if (flash == 0) set_pixel(cx_i, cy_i - 1, 255, 30, 30);
        else set_pixel(cx_i, cy_i - 1, 50, 150, 255);
    } else if (state_ == STATE_CRASH) {
        set_pixel(cx_i, cy_i, 255, 120, 20);
        set_pixel(cx_i - 1, cy_i, 255, 40, 20);
        set_pixel(tx_i, ty_i, 255, 80, 20);
    }

    // Progress bar
    int progress_h = static_cast<int>(std::round((distance_ / target_distance_) * 15.0f));
    for (int y = 0; y <= progress_h && y < 16; ++y) {
        set_pixel(0, 15 - y, 240, 60, 40);
    }
}

} // namespace arcade
