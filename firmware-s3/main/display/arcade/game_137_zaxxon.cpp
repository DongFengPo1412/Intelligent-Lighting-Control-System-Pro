#include "game_137_zaxxon.h"
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

Game137Zaxxon::Game137Zaxxon()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      fuel_(100.0f),
      px_(7.5f),
      py_(12.0f),
      pz_(2.0f),
      distance_traveled_(0.0f),
      boss_active_(false),
      boss_y_(-10.0f),
      boss_hp_(3),
      has_missile_(false) {
    Reset();
}

void Game137Zaxxon::Init() {
    Reset();
}

void Game137Zaxxon::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game137Zaxxon::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    fuel_ = 100.0f;
    px_ = 7.5f;
    py_ = 12.0f;
    pz_ = 2.0f;
    distance_traveled_ = 0.0f;

    boss_active_ = false;
    boss_y_ = -10.0f;
    boss_hp_ = 3;
    has_missile_ = false;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    float wy[NUM_WALLS] = {-4.0f, -16.0f, -28.0f};
    float wz[NUM_WALLS] = {2.0f, 3.0f, 1.0f};
    for (int i = 0; i < NUM_WALLS; ++i) {
        walls_[i].y = wy[i];
        walls_[i].gate_z = wz[i];
        walls_[i].cleared = false;
    }

    float tx[NUM_TARGETS] = {4.0f, 11.0f, 5.0f, 10.0f, 6.0f};
    float ty[NUM_TARGETS] = {-2.0f, -8.0f, -14.0f, -22.0f, -26.0f};
    uint8_t tt[NUM_TARGETS] = {0, 1, 0, 1, 0};
    for (int i = 0; i < NUM_TARGETS; ++i) {
        targets_[i].x = tx[i];
        targets_[i].y = ty[i];
        targets_[i].type = tt[i];
        targets_[i].alive = true;
    }
}

void Game137Zaxxon::CrashShip() {
    if (lives_ > 0) lives_--;
    state_ = STATE_SHIP_CRASH;
    state_timer_ = 0.0f;
}

void Game137Zaxxon::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // Fuel
        fuel_ -= 3.0f * dt;
        if (fuel_ <= 0.0f) {
            fuel_ = 0.0f;
            CrashShip();
            return;
        }

        // Horizontal position
        float move_speed_x = 7.5f;
        if (buttons & BTN_LEFT)  px_ = std::max(1.5f, px_ - move_speed_x * dt);
        if (buttons & BTN_RIGHT) px_ = std::min(13.5f, px_ + move_speed_x * dt);

        // Altitude
        float alt_speed = 3.5f;
        if (buttons & BTN_UP)   pz_ = std::min(MAX_ALTITUDE, pz_ + alt_speed * dt);
        if (buttons & BTN_DOWN) pz_ = std::max(MIN_ALTITUDE, pz_ - alt_speed * dt);

        // Scroll speed
        float scroll_speed = 4.0f;
        if (buttons & BTN_B) scroll_speed = 2.0f;
        distance_traveled_ += scroll_speed * dt;

        // Fire cannon (BTN_A)
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            for (int i = 0; i < MAX_BULLETS; ++i) {
                if (!bullets_[i].active) {
                    bullets_[i].x = px_;
                    bullets_[i].y = py_ - 1.0f;
                    bullets_[i].z = pz_;
                    bullets_[i].active = true;
                    break;
                }
            }
        }

        // Bullets update
        for (int i = 0; i < MAX_BULLETS; ++i) {
            if (bullets_[i].active) {
                bullets_[i].y -= 14.0f * dt;
                if (bullets_[i].y < -2.0f) {
                    bullets_[i].active = false;
                    continue;
                }

                if (bullets_[i].z <= 1.2f) {
                    for (int k = 0; k < NUM_TARGETS; ++k) {
                        if (targets_[k].alive &&
                            std::abs(bullets_[i].x - targets_[k].x) < 1.1f &&
                            std::abs(bullets_[i].y - targets_[k].y) < 1.1f) {
                            targets_[k].alive = false;
                            bullets_[i].active = false;
                            if (targets_[k].type == 0) {
                                fuel_ = std::min(100.0f, fuel_ + 30.0f);
                                score_ += 150;
                            } else {
                                score_ += 200;
                            }
                            break;
                        }
                    }
                }

                if (boss_active_ && boss_hp_ > 0 && bullets_[i].active) {
                    if (std::abs(bullets_[i].x - 7.5f) < 1.8f && std::abs(bullets_[i].y - boss_y_) < 1.5f) {
                        if (std::abs(bullets_[i].z - 2.0f) < 1.2f) {
                            bullets_[i].active = false;
                            boss_hp_--;
                            score_ += 300;
                            if (boss_hp_ <= 0) {
                                score_ += 1000;
                                state_ = STATE_STAGE_CLEAR;
                                state_timer_ = 0.0f;
                                return;
                            }
                        }
                    }
                }
            }
        }

        // Walls
        for (int i = 0; i < NUM_WALLS; ++i) {
            walls_[i].y += scroll_speed * dt;
            if (!walls_[i].cleared && std::abs(walls_[i].y - py_) < 0.6f) {
                if (std::abs(pz_ - walls_[i].gate_z) > 0.6f) {
                    CrashShip();
                    return;
                } else {
                    walls_[i].cleared = true;
                    score_ += 100;
                }
            }
        }

        // Targets scroll
        for (int i = 0; i < NUM_TARGETS; ++i) {
            targets_[i].y += scroll_speed * dt;
        }

        // Boss Zaxxon
        if (distance_traveled_ >= 35.0f && !boss_active_) {
            boss_active_ = true;
            boss_y_ = 1.0f;
        }

        if (boss_active_) {
            boss_y_ = std::min(3.5f, boss_y_ + 1.0f * dt);
            if (!has_missile_ && boss_hp_ > 0) {
                boss_missile_.x = 7.5f;
                boss_missile_.y = boss_y_ + 1.0f;
                boss_missile_.active = true;
                has_missile_ = true;
            } else if (has_missile_ && boss_missile_.active) {
                boss_missile_.y += 6.0f * dt;
                if (boss_missile_.x < px_) boss_missile_.x += 1.5f * dt;
                else boss_missile_.x -= 1.5f * dt;

                if (std::abs(boss_missile_.x - px_) < 0.9f && std::abs(boss_missile_.y - py_) < 0.9f) {
                    boss_missile_.active = false;
                    CrashShip();
                    return;
                }
                if (boss_missile_.y > 16.0f) {
                    has_missile_ = false;
                }
            }
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_SHIP_CRASH) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_SHIP_CRASH) {
                if (lives_ > 0) {
                    fuel_ = 100.0f;
                    px_ = 7.5f;
                    py_ = 12.0f;
                    pz_ = 2.0f;
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

void Game137Zaxxon::Render(uint8_t* fb) {
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

    // Ground grid lines
    for (int y = 0; y < 16; y += 4) {
        int offset_y = static_cast<int>(std::fmod(distance_traveled_ + y, 16.0f));
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, offset_y, 10, 20, 40);
        }
    }

    // Targets
    for (int i = 0; i < NUM_TARGETS; ++i) {
        if (targets_[i].alive && targets_[i].y >= 0.0f && targets_[i].y < 16.0f) {
            int tx = static_cast<int>(std::round(targets_[i].x));
            int ty = static_cast<int>(std::round(targets_[i].y));
            if (targets_[i].type == 0) {
                set_pixel(tx, ty, 255, 180, 20);
                set_pixel(tx, ty - 1, 255, 60, 20);
            } else {
                set_pixel(tx, ty, 220, 40, 40);
                set_pixel(tx + 1, ty, 180, 20, 20);
            }
        }
    }

    // Walls
    for (int i = 0; i < NUM_WALLS; ++i) {
        int wy = static_cast<int>(std::round(walls_[i].y));
        if (wy >= 0 && wy < 16) {
            for (int x = 0; x < 16; ++x) set_pixel(x, wy, 160, 80, 180);
            set_pixel(7, wy, 60, 240, 255);
            set_pixel(8, wy, 60, 240, 255);
        }
    }

    // Boss
    if (boss_active_ && boss_y_ >= 0.0f && boss_y_ < 16.0f) {
        int by = static_cast<int>(std::round(boss_y_));
        for (int ox = -2; ox <= 2; ++ox) set_pixel(7 + ox, by, 220, 40, 60);
        set_pixel(7, by - 1, 255, 255, 255);
        set_pixel(8, by - 1, 255, 255, 255);

        if (has_missile_ && boss_missile_.active) {
            set_pixel(static_cast<int>(std::round(boss_missile_.x)),
                      static_cast<int>(std::round(boss_missile_.y)), 255, 120, 40);
        }
    }

    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (bullets_[i].active) {
            int by_screen = static_cast<int>(std::round(bullets_[i].y - bullets_[i].z * 0.7f));
            set_pixel(static_cast<int>(std::round(bullets_[i].x)), by_screen, 255, 255, 200);
        }
    }

    // Player & Shadow
    int px = static_cast<int>(std::round(px_));
    int py_ground = static_cast<int>(std::round(py_));
    int py_ship = static_cast<int>(std::round(py_ - pz_ * 0.7f));

    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        // Shadow
        set_pixel(px, py_ground, 30, 45, 65);
        set_pixel(px - 1, py_ground, 20, 30, 50);
        set_pixel(px + 1, py_ground, 20, 30, 50);

        // Ship
        set_pixel(px, py_ship, 255, 255, 255);
        set_pixel(px - 1, py_ship, 60, 200, 255);
        set_pixel(px + 1, py_ship, 60, 200, 255);
        set_pixel(px, py_ship + 1, 255, 140, 40);
    } else if (state_ == STATE_SHIP_CRASH) {
        set_pixel(px, py_ground, 255, 100, 30);
        set_pixel(px - 1, py_ground, 255, 40, 20);
        set_pixel(px + 1, py_ground, 255, 40, 20);
    }

    // Altitude gauge on col 0
    int alt_bar = static_cast<int>(std::round((pz_ / MAX_ALTITUDE) * 6.0f));
    for (int h = 0; h <= alt_bar && h < 7; ++h) {
        set_pixel(0, 15 - h, 60, 220, 255);
    }

    // Fuel gauge
    int fuel_pixels = static_cast<int>(std::round((fuel_ / 100.0f) * 13.0f));
    for (int x = 0; x <= fuel_pixels && x < 14; ++x) {
        set_pixel(2 + x, 15, 240, 180, 40);
    }
}

} // namespace arcade
