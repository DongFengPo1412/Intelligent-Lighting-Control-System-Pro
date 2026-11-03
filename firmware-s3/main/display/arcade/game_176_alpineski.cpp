#include "game_176_alpineski.h"
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

Game176AlpineSki::Game176AlpineSki() {
    Reset();
}

void Game176AlpineSki::Init() {
    Reset();
}

void Game176AlpineSki::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game176AlpineSki::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 12.0f;
    steer_speed_ = 7.0f;
    base_speed_ = 8.0f;
    speed_ = 8.0f;
    in_air_ = false;
    jump_timer_ = 0.0f;
    time_left_ = 60.0f + stage_ * 5.0f;
    distance_ = 0.0f;
    target_distance_ = 250.0f + stage_ * 50.0f;

    SpawnTrack();
}

void Game176AlpineSki::SpawnTrack() {
    for (int i = 0; i < MAX_ELEMENTS; ++i) elements_[i].active = false;

    float y = -4.0f;
    int count = 0;
    while (y > -target_distance_ && count < MAX_ELEMENTS) {
        int idx = static_cast<int>(std::abs(y) / 6.0f) % 4;
        if (idx == 0) {
            float gx = 5.0f + (static_cast<int>(std::abs(y) * 3.0f) % 6);
            elements_[count] = {y, ELEM_GATE, gx - 1.5f, gx + 1.5f, false, true};
        } else if (idx == 1) {
            float tx = 3.0f + (static_cast<int>(std::abs(y) * 5.0f) % 10);
            elements_[count] = {y, ELEM_TREE, tx, 0.0f, false, true};
        } else if (idx == 2) {
            float rx = 6.0f + (static_cast<int>(std::abs(y) * 2.0f) % 4);
            elements_[count] = {y, ELEM_RAMP, rx, 0.0f, false, true};
        } else {
            float ox = 4.0f + (static_cast<int>(std::abs(y) * 7.0f) % 8);
            elements_[count] = {y, ELEM_ROCK, ox, 0.0f, false, true};
        }
        count++;
        y -= 7.0f;
    }
}

void Game176AlpineSki::Wipeout() {
    lives_--;
    state_ = STATE_WIPEOUT;
    state_timer_ = 1.0f;
}

void Game176AlpineSki::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_WIPEOUT) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                in_air_ = false;
            } else {
                state_ = STATE_GAME_OVER;
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if (((buttons & BTN_A) && !(prev_buttons & BTN_A)) ||
            ((buttons & BTN_B) && !(prev_buttons & BTN_B))) {
            Reset();
        }
        return;
    }

    time_left_ -= dt;
    if (time_left_ <= 0.0f) {
        Wipeout();
        return;
    }

    // Steering
    if (buttons & BTN_LEFT)  px_ -= steer_speed_ * dt;
    if (buttons & BTN_RIGHT) px_ += steer_speed_ * dt;
    px_ = std::max(2.0f, std::min(13.0f, px_));

    // Tuck / Acceleration (Button A)
    if (buttons & BTN_A) {
        speed_ = base_speed_ * 1.6f;
        score_ += static_cast<uint32_t>(100.0f * dt);
    } else {
        speed_ = base_speed_;
        score_ += static_cast<uint32_t>(50.0f * dt);
    }

    // Ski Jump (Button B)
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B) && !in_air_) {
        in_air_ = true;
        jump_timer_ = 0.6f;
    }

    if (in_air_) {
        jump_timer_ -= dt;
        if (jump_timer_ <= 0.0f) in_air_ = false;
    }

    // Track scroll
    float scroll_dist = speed_ * dt;
    distance_ += scroll_dist;

    for (int i = 0; i < MAX_ELEMENTS; ++i) {
        if (!elements_[i].active) continue;

        elements_[i].y += scroll_dist;

        if (!elements_[i].cleared && std::abs(elements_[i].y - py_) < 0.8f) {
            if (elements_[i].type == ELEM_GATE) {
                if (px_ >= elements_[i].x && px_ <= elements_[i].x2) {
                    elements_[i].cleared = true;
                    score_ += 200;
                    time_left_ += 2.0f;
                } else if (std::abs(px_ - elements_[i].x) < 0.6f || std::abs(px_ - elements_[i].x2) < 0.6f) {
                    elements_[i].cleared = true;
                    if (!in_air_) {
                        Wipeout();
                        return;
                    }
                }
            } else if (elements_[i].type == ELEM_RAMP) {
                if (std::abs(px_ - elements_[i].x) < 1.0f) {
                    elements_[i].cleared = true;
                    in_air_ = true;
                    jump_timer_ = 0.8f;
                    score_ += 300;
                }
            } else if (elements_[i].type == ELEM_ROCK || elements_[i].type == ELEM_TREE) {
                if (std::abs(px_ - elements_[i].x) < 0.8f) {
                    elements_[i].cleared = true;
                    if (!in_air_) {
                        Wipeout();
                        return;
                    }
                }
            }
        }
    }

    if (distance_ >= target_distance_) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 2.0f;
        score_ += 2000 + static_cast<uint32_t>(time_left_ * 50.0f);
    }
}

void Game176AlpineSki::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Snow course
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 1 || x == 14 || x == 15) {
                set_pixel(x, y, 10, 80, 20); // Pines
            } else {
                set_pixel(x, y, 220, 235, 255); // Snow
            }
        }
    }

    // Elements
    for (int i = 0; i < MAX_ELEMENTS; ++i) {
        if (!elements_[i].active) continue;
        int ey = static_cast<int>(std::round(elements_[i].y));
        if (ey >= 0 && ey < 16) {
            if (elements_[i].type == ELEM_GATE) {
                set_pixel(static_cast<int>(std::round(elements_[i].x)), ey, 255, 30, 30);
                set_pixel(static_cast<int>(std::round(elements_[i].x2)), ey, 30, 80, 255);
            } else if (elements_[i].type == ELEM_TREE) {
                int tx = static_cast<int>(std::round(elements_[i].x));
                set_pixel(tx, ey, 20, 140, 30);
                set_pixel(tx, ey + 1, 100, 60, 20);
            } else if (elements_[i].type == ELEM_ROCK) {
                int rx = static_cast<int>(std::round(elements_[i].x));
                set_pixel(rx, ey, 120, 120, 130);
            } else if (elements_[i].type == ELEM_RAMP) {
                int rx = static_cast<int>(std::round(elements_[i].x));
                set_pixel(rx, ey, 255, 200, 0);
                set_pixel(rx + 1, ey, 255, 160, 0);
            }
        }
    }

    // Skier
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        if (in_air_) {
            set_pixel(px, py, 255, 80, 0);
            set_pixel(px, py - 1, 255, 255, 0);
            set_pixel(px - 1, py + 1, 200, 200, 200);
            set_pixel(px + 1, py + 1, 200, 200, 200);
            set_pixel(px, py + 2, 160, 180, 200);
        } else {
            set_pixel(px, py, 220, 40, 30);
            set_pixel(px, py - 1, 255, 220, 40);
            set_pixel(px - 1, py, 200, 200, 200);
            set_pixel(px + 1, py, 200, 200, 200);
        }
    } else if (state_ == STATE_WIPEOUT) {
        set_pixel(px, py, 255, 80, 0);
        set_pixel(px - 1, py, 255, 0, 0);
        set_pixel(px + 1, py, 255, 0, 0);
    }
}

} // namespace arcade
