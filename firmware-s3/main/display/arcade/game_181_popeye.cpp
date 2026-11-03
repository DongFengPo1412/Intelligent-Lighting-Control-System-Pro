#include "game_181_popeye.h"
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

Game181Popeye::Game181Popeye() {
    Reset();
}

void Game181Popeye::Init() {
    Reset();
}

void Game181Popeye::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game181Popeye::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 3.0f;
    py_ = 12.0f;
    speed_ = 5.5f;
    spinach_timer_ = 0.0f;
    spinach_available_ = true;
    spinach_x_ = 1.0f;
    spinach_y_ = 8.0f;

    bx_ = 12.0f;
    by_ = 12.0f;
    bluto_stun_ = 0.0f;
    bluto_speed_ = 2.8f + stage_ * 0.3f;

    olive_x_ = 7.5f;
    olive_y_ = 1.0f;
    drop_timer_ = 1.5f;
    hearts_collected_ = 0;
    target_hearts_ = 6 + stage_;

    for (int i = 0; i < MAX_HEARTS; ++i) hearts_[i].active = false;
}

void Game181Popeye::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_POPEYE_DEFEATED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 3.0f;
                py_ = 12.0f;
                bx_ = 12.0f;
                by_ = 12.0f;
                spinach_timer_ = 0.0f;
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

    if (spinach_timer_ > 0.0f) {
        spinach_timer_ -= dt;
    }

    // Movement
    float dx = 0.0f;
    if (buttons & BTN_LEFT)  dx -= 1.0f;
    if (buttons & BTN_RIGHT) dx += 1.0f;
    px_ += dx * speed_ * dt;
    px_ = std::max(1.0f, std::min(14.0f, px_));

    bool near_ladder = (px_ <= 3.2f || px_ >= 11.8f);
    if (near_ladder) {
        if (buttons & BTN_UP)   py_ -= speed_ * dt;
        if (buttons & BTN_DOWN) py_ += speed_ * dt;
    }

    py_ = std::max(4.0f, std::min(12.0f, py_));
    if (!near_ladder) {
        float closest_deck = (py_ < 6.0f) ? 4.0f : ((py_ < 10.0f) ? 8.0f : 12.0f);
        py_ = closest_deck;
    }

    // Punch Spinach (Button A)
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A) && spinach_available_) {
        if (std::hypot(px_ - spinach_x_, py_ - spinach_y_) < 1.5f) {
            spinach_available_ = false;
            spinach_timer_ = 7.0f;
            score_ += 200;
        }
    }

    // Olive drops hearts
    drop_timer_ -= dt;
    if (drop_timer_ <= 0.0f) {
        int active_hearts = 0;
        for (int i = 0; i < MAX_HEARTS; ++i) if (hearts_[i].active) active_hearts++;
        if (active_hearts < MAX_HEARTS) {
            drop_timer_ = std::max(1.5f, 3.0f - stage_ * 0.2f);
            for (int i = 0; i < MAX_HEARTS; ++i) {
                if (!hearts_[i].active) {
                    hearts_[i] = {
                        olive_x_ + std::sin(static_cast<float>(hearts_collected_)) * 3.0f,
                        2.0f,
                        (active_hearts % 2 == 0) ? 1.2f : -1.2f,
                        1.6f,
                        false,
                        5.0f,
                        true
                    };
                    break;
                }
            }
        }
    }

    // Update Hearts
    for (int i = 0; i < MAX_HEARTS; ++i) {
        if (!hearts_[i].active) continue;

        if (!hearts_[i].on_floor) {
            hearts_[i].x += hearts_[i].vx * dt;
            hearts_[i].y += hearts_[i].vy * dt;
            if (hearts_[i].x > 13.5f) { hearts_[i].x = 13.5f; hearts_[i].vx = -std::abs(hearts_[i].vx); }
            else if (hearts_[i].x < 1.5f) { hearts_[i].x = 1.5f; hearts_[i].vx = std::abs(hearts_[i].vx); }

            if (hearts_[i].y >= 13.0f) {
                hearts_[i].y = 13.0f;
                hearts_[i].on_floor = true;
            }
        } else {
            hearts_[i].floor_timer -= dt;
            if (hearts_[i].floor_timer <= 0.0f) {
                hearts_[i].active = false;
                lives_--;
                state_ = STATE_POPEYE_DEFEATED;
                state_timer_ = 1.0f;
                return;
            }
        }

        if (std::hypot(px_ - hearts_[i].x, py_ - hearts_[i].y) < 1.2f) {
            hearts_[i].active = false;
            hearts_collected_++;
            score_ += 100;
            if (hearts_collected_ >= target_hearts_) {
                state_ = STATE_STAGE_CLEAR;
                state_timer_ = 2.0f;
                score_ += 2000;
                return;
            }
        }
    }

    // Update Bluto
    if (bluto_stun_ > 0.0f) {
        bluto_stun_ -= dt;
    } else {
        float bdx = px_ - bx_;
        float bdy = py_ - by_;
        if (std::abs(bdx) > 0.2f) {
            bx_ += ((bdx > 0) ? 1.0f : -1.0f) * bluto_speed_ * dt;
        }

        if (std::abs(bdy) > 0.5f && (bx_ <= 3.5f || bx_ >= 11.5f)) {
            by_ += ((bdy > 0) ? 1.0f : -1.0f) * bluto_speed_ * dt;
        } else {
            float closest_deck = (by_ < 6.0f) ? 4.0f : ((by_ < 10.0f) ? 8.0f : 12.0f);
            by_ = closest_deck;
        }
        bx_ = std::max(1.0f, std::min(14.0f, bx_));

        if (std::hypot(px_ - bx_, py_ - by_) < 1.1f) {
            if (spinach_timer_ > 0.0f) {
                bluto_stun_ = 4.0f;
                bx_ = 14.0f;
                by_ = 12.0f;
                score_ += 1000;
            } else {
                lives_--;
                state_ = STATE_POPEYE_DEFEATED;
                state_timer_ = 1.2f;
                return;
            }
        }
    }
}

void Game181Popeye::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Decks
    for (int y : {5, 9, 13}) {
        for (int x = 1; x <= 14; ++x) set_pixel(x, y, 120, 80, 40);
    }

    // Ladders
    for (int x : {2, 13}) {
        for (int y = 4; y <= 13; ++y) {
            if (y % 2 == 0) set_pixel(x, y, 180, 180, 190);
        }
    }

    // Spinach
    if (spinach_available_) {
        set_pixel(static_cast<int>(spinach_x_), static_cast<int>(spinach_y_), 40, 220, 40);
    }

    // Olive
    int ox = static_cast<int>(std::round(olive_x_));
    set_pixel(ox, 1, 240, 60, 120);
    set_pixel(ox, 0, 240, 200, 180);

    // Hearts
    for (int i = 0; i < MAX_HEARTS; ++i) {
        if (!hearts_[i].active) continue;
        int hx = static_cast<int>(std::round(hearts_[i].x));
        int hy = static_cast<int>(std::round(hearts_[i].y));
        if (hearts_[i].on_floor && hearts_[i].floor_timer < 2.0f) {
            set_pixel(hx, hy, 140, 40, 40);
        } else {
            set_pixel(hx, hy, 255, 60, 160);
        }
    }

    // Bluto
    int bx = static_cast<int>(std::round(bx_));
    int by = static_cast<int>(std::round(by_));
    if (bluto_stun_ > 0.0f) {
        set_pixel(bx, by, 100, 100, 100);
    } else {
        set_pixel(bx, by, 30, 30, 80);
        set_pixel(bx, by - 1, 40, 40, 40);
        set_pixel(bx - 1, by - 1, 220, 140, 100);
        set_pixel(bx + 1, by - 1, 220, 140, 100);
    }

    // Popeye
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        if (spinach_timer_ > 0.0f) {
            set_pixel(px, py, 255, 220, 0);
            set_pixel(px, py - 1, 255, 255, 100);
        } else {
            set_pixel(px, py, 40, 60, 200);
            set_pixel(px, py - 1, 255, 255, 255);
            set_pixel(px + 1, py, 255, 180, 140);
        }
    } else if (state_ == STATE_POPEYE_DEFEATED) {
        set_pixel(px, py, 255, 80, 0);
    }
}

} // namespace arcade

