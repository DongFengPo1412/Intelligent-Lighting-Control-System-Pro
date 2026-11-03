#include "game_138_rocnrope.h"
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

Game138RocnRope::Game138RocnRope()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      px_(2.0f),
      py_(14.0f),
      facing_(1),
      rope_active_(false),
      rope_start_x_(0.0f),
      rope_start_y_(0.0f),
      rope_end_x_(0.0f),
      rope_end_y_(0.0f),
      on_rope_(false),
      rope_t_(0.0f),
      flashlight_timer_(0.0f) {
    Reset();
}

void Game138RocnRope::Init() {
    Reset();
}

void Game138RocnRope::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game138RocnRope::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 2.0f;
    py_ = 14.0f;
    facing_ = 1;

    rope_active_ = false;
    on_rope_ = false;
    rope_t_ = 0.0f;
    flashlight_timer_ = 0.0f;

    ledges_[0] = {14.0f, 1.0f, 6.0f};
    ledges_[1] = {14.0f, 9.0f, 14.0f};
    ledges_[2] = {10.0f, 1.0f, 6.0f};
    ledges_[3] = {10.0f, 9.0f, 14.0f};
    ledges_[4] = {6.0f, 4.0f, 11.0f};
    ledges_[5] = {2.0f, 6.0f, 9.0f};

    enemies_[0] = {4.0f, 10.0f, 1.5f, 1.0f, 6.0f, 0.0f, true};
    enemies_[1] = {11.0f, 10.0f, -1.5f, 9.0f, 14.0f, 0.0f, true};
    enemies_[2] = {7.5f, 6.0f, 1.8f, 4.0f, 11.0f, 0.0f, true};
}

void Game138RocnRope::LoseLife() {
    if (lives_ > 0) lives_--;
    state_ = STATE_FALLEN;
    state_timer_ = 0.0f;
}

bool Game138RocnRope::GetCurrentLedge(float px, float py, Ledge& out_ledge) {
    for (int i = 0; i < NUM_LEDGES; ++i) {
        if (std::abs(py - ledges_[i].y) < 0.3f &&
            px >= ledges_[i].x1 - 0.4f && px <= ledges_[i].x2 + 0.4f) {
            out_ledge = ledges_[i];
            return true;
        }
    }
    return false;
}

void Game138RocnRope::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // Flashlight timer
        if (flashlight_timer_ > 0.0f) {
            flashlight_timer_ -= dt;
            if (flashlight_timer_ < 0.0f) flashlight_timer_ = 0.0f;
        }

        // Stun flashlight (BTN_B)
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            flashlight_timer_ = 0.4f;
            for (int i = 0; i < NUM_ENEMIES; ++i) {
                if (enemies_[i].alive && std::abs(enemies_[i].y - py_) < 1.0f) {
                    if ((facing_ > 0 && enemies_[i].x - px_ >= 0.0f && enemies_[i].x - px_ <= 5.0f) ||
                        (facing_ < 0 && px_ - enemies_[i].x >= 0.0f && px_ - enemies_[i].x <= 5.0f)) {
                        enemies_[i].stun_timer = 3.0f;
                        score_ += 50;
                    }
                }
            }
        }

        // Harpoon fire (BTN_A)
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            if (!on_rope_) {
                for (int i = 0; i < NUM_LEDGES; ++i) {
                    if (ledges_[i].y < py_ - 1.5f) {
                        float dy = py_ - ledges_[i].y;
                        float tx = px_ + facing_ * dy;
                        if (tx >= ledges_[i].x1 && tx <= ledges_[i].x2) {
                            rope_active_ = true;
                            rope_start_x_ = px_;
                            rope_start_y_ = py_;
                            rope_end_x_ = tx;
                            rope_end_y_ = ledges_[i].y;
                            on_rope_ = false;
                            rope_t_ = 0.0f;
                            break;
                        }
                    }
                }
            }
        }

        // Movement
        if (on_rope_) {
            float climb_speed = 2.0f;
            if ((buttons & BTN_UP) || (facing_ > 0 && (buttons & BTN_RIGHT)) || (facing_ < 0 && (buttons & BTN_LEFT))) {
                rope_t_ += climb_speed * dt;
                if (rope_t_ >= 1.0f) {
                    rope_t_ = 1.0f;
                    px_ = rope_end_x_;
                    py_ = rope_end_y_;
                    on_rope_ = false;
                    rope_active_ = false;
                    score_ += 100;

                    if (py_ <= 2.2f) {
                        score_ += 1000;
                        state_ = STATE_STAGE_CLEAR;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            } else if (buttons & BTN_DOWN) {
                rope_t_ -= climb_speed * dt;
                if (rope_t_ <= 0.0f) {
                    rope_t_ = 0.0f;
                    px_ = rope_start_x_;
                    py_ = rope_start_y_;
                    on_rope_ = false;
                }
            }

            px_ = rope_start_x_ + (rope_end_x_ - rope_start_x_) * rope_t_;
            py_ = rope_start_y_ + (rope_end_y_ - rope_start_y_) * rope_t_;
        } else {
            float move_speed = 5.0f;
            if (buttons & BTN_LEFT) {
                px_ = std::max(1.0f, px_ - move_speed * dt);
                facing_ = -1;
            }
            if (buttons & BTN_RIGHT) {
                px_ = std::min(14.0f, px_ + move_speed * dt);
                facing_ = 1;
            }

            // Mount rope
            if (rope_active_ && (buttons & BTN_UP)) {
                if (std::abs(px_ - rope_start_x_) < 1.0f && std::abs(py_ - rope_start_y_) < 0.6f) {
                    on_rope_ = true;
                    rope_t_ = 0.05f;
                }
            }

            // Gravity
            Ledge current_ledge;
            if (!GetCurrentLedge(px_, py_, current_ledge)) {
                py_ += 10.0f * dt;
                bool landed = false;
                for (int i = 0; i < NUM_LEDGES; ++i) {
                    if (std::abs(py_ - ledges_[i].y) < 0.6f &&
                        px_ >= ledges_[i].x1 && px_ <= ledges_[i].x2) {
                        py_ = ledges_[i].y;
                        landed = true;
                        break;
                    }
                }
                if (!landed && py_ >= 15.0f) {
                    LoseLife();
                    return;
                }
            }
        }

        // Enemies
        for (int i = 0; i < NUM_ENEMIES; ++i) {
            if (enemies_[i].alive) {
                if (enemies_[i].stun_timer > 0.0f) {
                    enemies_[i].stun_timer -= dt;
                    if (enemies_[i].stun_timer < 0.0f) enemies_[i].stun_timer = 0.0f;
                } else {
                    enemies_[i].x += enemies_[i].vx * dt;
                    if (enemies_[i].x <= enemies_[i].min_x) {
                        enemies_[i].x = enemies_[i].min_x;
                        enemies_[i].vx = -enemies_[i].vx;
                    } else if (enemies_[i].x >= enemies_[i].max_x) {
                        enemies_[i].x = enemies_[i].max_x;
                        enemies_[i].vx = -enemies_[i].vx;
                    }
                }

                if (std::abs(px_ - enemies_[i].x) < 0.9f && std::abs(py_ - enemies_[i].y) < 0.9f) {
                    if (enemies_[i].stun_timer <= 0.0f) {
                        LoseLife();
                        return;
                    }
                }
            }
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_FALLEN) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_FALLEN) {
                if (lives_ > 0) {
                    px_ = 2.0f;
                    py_ = 14.0f;
                    facing_ = 1;
                    rope_active_ = false;
                    on_rope_ = false;
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

void Game138RocnRope::Render(uint8_t* fb) {
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

    // Ledges
    for (int i = 0; i < NUM_LEDGES; ++i) {
        int ly = static_cast<int>(std::round(ledges_[i].y));
        for (int x = static_cast<int>(std::round(ledges_[i].x1)); x <= static_cast<int>(std::round(ledges_[i].x2)); ++x) {
            set_pixel(x, ly, 140, 80, 40);
            set_pixel(x, ly + 1, 90, 50, 25);
        }
    }

    // Golden Bird
    set_pixel(7, 1, 255, 230, 40);
    set_pixel(8, 1, 255, 230, 40);
    set_pixel(7, 2, 255, 180, 30);
    set_pixel(8, 2, 255, 180, 30);

    // Rope
    if (rope_active_) {
        for (int s = 0; s <= 10; ++s) {
            float t = s / 10.0f;
            int rx = static_cast<int>(std::round(rope_start_x_ + (rope_end_x_ - rope_start_x_) * t));
            int ry = static_cast<int>(std::round(rope_start_y_ + (rope_end_y_ - rope_start_y_) * t));
            set_pixel(rx, ry, 220, 200, 150);
        }
    }

    // Flashlight
    if (flashlight_timer_ > 0.0f) {
        int py = static_cast<int>(std::round(py_));
        int px = static_cast<int>(std::round(px_));
        for (int dist = 1; dist <= 4; ++dist) {
            set_pixel(px + facing_ * dist, py, 255, 255, 160);
        }
    }

    // Enemies
    for (int i = 0; i < NUM_ENEMIES; ++i) {
        if (enemies_[i].alive) {
            int ex = static_cast<int>(std::round(enemies_[i].x));
            int ey = static_cast<int>(std::round(enemies_[i].y));
            if (enemies_[i].stun_timer > 0.0f) {
                set_pixel(ex, ey, 255, 255, 50);
                set_pixel(ex, ey - 1, 100, 200, 255);
            } else {
                set_pixel(ex, ey, 220, 50, 40);
                set_pixel(ex, ey - 1, 255, 150, 100);
            }
        }
    }

    // Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 40, 120, 240);
        set_pixel(px, py - 1, 240, 180, 60);
        set_pixel(px + facing_, py, 200, 200, 200);
    } else if (state_ == STATE_FALLEN) {
        set_pixel(px, py, 255, 60, 40);
    }

    // Lives
    for (int l = 0; l < std::min(static_cast<int>(lives_), 3); ++l) {
        set_pixel(l * 2, 0, 40, 120, 240);
    }
}

} // namespace arcade
