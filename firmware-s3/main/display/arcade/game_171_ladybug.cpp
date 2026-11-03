#include "game_171_ladybug.h"
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

Game171LadyBug::Game171LadyBug() {
    Reset();
}

void Game171LadyBug::Init() {
    Reset();
}

void Game171LadyBug::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    multiplier_ = 1;
    InitStage();
}

bool Game171LadyBug::IsSkull(int x, int y) const {
    return (x == 4 && y == 8) || (x == 11 && y == 8);
}

bool Game171LadyBug::IsHeart(int x, int y) const {
    return (x == 7 && y == 2) || (x == 8 && y == 13);
}

bool Game171LadyBug::IsTurnstile(int x, int y) const {
    return (x == 4 && y == 5) || (x == 11 && y == 5) ||
           (x == 7 && y == 8) || (x == 8 && y == 8) ||
           (x == 4 && y == 11) || (x == 11 && y == 11);
}

bool Game171LadyBug::IsDot(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return false;
    int idx = y * 16 + x;
    return (dots_mask_[idx / 8] & (1 << (idx % 8))) != 0;
}

void Game171LadyBug::RemoveDot(int x, int y) {
    if (IsDot(x, y)) {
        int idx = y * 16 + x;
        dots_mask_[idx / 8] &= ~(1 << (idx % 8));
        if (dots_left_ > 0) dots_left_--;
    }
}

void Game171LadyBug::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 13.0f;
    speed_ = 5.0f;

    std::memset(dots_mask_, 0, sizeof(dots_mask_));
    dots_left_ = 0;

    static const int valid_y[] = {2, 5, 8, 11, 13};
    for (int y : valid_y) {
        for (int x = 1; x <= 14; ++x) {
            if (!IsSkull(x, y) && !IsHeart(x, y) && !IsTurnstile(x, y) && !(x == 7 && y == 5) && !(x == 8 && y == 5)) {
                int idx = y * 16 + x;
                dots_mask_[idx / 8] |= (1 << (idx % 8));
                dots_left_++;
            }
        }
    }

    turnstiles_[0] = {4, 5, 0};  // 0: 'H'
    turnstiles_[1] = {11, 5, 0};
    turnstiles_[2] = {7, 8, 1};  // 1: 'V'
    turnstiles_[3] = {8, 8, 1};
    turnstiles_[4] = {4, 11, 0};
    turnstiles_[5] = {11, 11, 0};

    beetles_[0] = {0, 7.5f, 5.0f, 2.2f + stage_ * 0.2f, true};
    beetles_[1] = {1, 8.0f, 2.0f, 2.5f + stage_ * 0.2f, true};
}

void Game171LadyBug::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_LADYBUG_DIED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                py_ = 13.0f;
            } else {
                state_ = STATE_GAME_OVER;
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT)  dx -= 1.0f;
    if (buttons & BTN_RIGHT) dx += 1.0f;
    if (buttons & BTN_UP)    dy -= 1.0f;
    if (buttons & BTN_DOWN)  dy += 1.0f;

    if (dx != 0.0f || dy != 0.0f) {
        float new_px = px_ + dx * speed_ * dt;
        float new_py = py_ + dy * speed_ * dt;

        for (int i = 0; i < NUM_TURNSTILES; ++i) {
            if (std::hypot(turnstiles_[i].x - new_px, turnstiles_[i].y - new_py) < 0.8f) {
                turnstiles_[i].ori = (turnstiles_[i].ori == 0) ? 1 : 0;
                score_ += 50;
                break;
            }
        }

        px_ = std::max(1.0f, std::min(14.0f, new_px));
        py_ = std::max(1.0f, std::min(14.0f, new_py));
    }

    int cx = static_cast<int>(std::round(px_));
    int cy = static_cast<int>(std::round(py_));

    if (IsDot(cx, cy)) {
        RemoveDot(cx, cy);
        score_ += 10 * multiplier_;
        if (dots_left_ == 0) {
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 2.0f;
            score_ += 2000;
            return;
        }
    }

    if (IsHeart(cx, cy)) {
        multiplier_ = std::min(5, multiplier_ + 1);
        score_ += 300;
    }

    if (IsSkull(cx, cy)) {
        lives_--;
        state_ = STATE_LADYBUG_DIED;
        state_timer_ = 1.0f;
        return;
    }

    // Beetles
    for (int b = 0; b < NUM_BEETLES; ++b) {
        if (!beetles_[b].alive) continue;

        float bdx = px_ - beetles_[b].x;
        float bdy = py_ - beetles_[b].y;
        float dist = std::hypot(bdx, bdy);

        float step_x = (dist > 0.1f) ? ((bdx / dist) * beetles_[b].speed * dt) : 0.0f;
        float step_y = (dist > 0.1f) ? ((bdy / dist) * beetles_[b].speed * dt) : 0.0f;

        bool blocked = false;
        float nx = beetles_[b].x + step_x;
        float ny = beetles_[b].y + step_y;
        for (int t = 0; t < NUM_TURNSTILES; ++t) {
            if (turnstiles_[t].ori == 0) { // 'H'
                if (std::abs(ny - turnstiles_[t].y) < 0.6f && std::abs(nx - turnstiles_[t].x) <= 1.2f) {
                    blocked = true;
                    break;
                }
            } else { // 'V'
                if (std::abs(nx - turnstiles_[t].x) < 0.6f && std::abs(ny - turnstiles_[t].y) <= 1.2f) {
                    blocked = true;
                    break;
                }
            }
        }

        if (!blocked && dist > 0.1f) {
            beetles_[b].x += step_x;
            beetles_[b].y += step_y;
        }

        int bx = static_cast<int>(std::round(beetles_[b].x));
        int by = static_cast<int>(std::round(beetles_[b].y));

        if (IsSkull(bx, by)) {
            beetles_[b].alive = false;
            score_ += 1000;
        }

        if (std::hypot(beetles_[b].x - px_, beetles_[b].y - py_) < 0.8f) {
            lives_--;
            state_ = STATE_LADYBUG_DIED;
            state_timer_ = 1.0f;
            return;
        }
    }
}

void Game171LadyBug::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Border
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 0, 40, 100, 40);
        set_pixel(x, 15, 40, 100, 40);
    }
    for (int y = 0; y < 16; ++y) {
        set_pixel(0, y, 40, 100, 40);
        set_pixel(15, y, 40, 100, 40);
    }

    // Dots
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsDot(x, y)) {
                set_pixel(x, y, 240, 240, 120);
            }
        }
    }

    // Hearts & Skulls
    set_pixel(7, 2, 255, 60, 140);
    set_pixel(8, 13, 255, 60, 140);
    set_pixel(4, 8, 0, 220, 255);
    set_pixel(11, 8, 0, 220, 255);

    // Turnstiles
    for (int i = 0; i < NUM_TURNSTILES; ++i) {
        int tx = turnstiles_[i].x;
        int ty = turnstiles_[i].y;
        set_pixel(tx, ty, 255, 200, 0);
        if (turnstiles_[i].ori == 0) {
            set_pixel(tx - 1, ty, 220, 160, 0);
            set_pixel(tx + 1, ty, 220, 160, 0);
        } else {
            set_pixel(tx, ty - 1, 220, 160, 0);
            set_pixel(tx, ty + 1, 220, 160, 0);
        }
    }

    // Beetles
    for (int b = 0; b < NUM_BEETLES; ++b) {
        if (beetles_[b].alive) {
            int bx = static_cast<int>(std::round(beetles_[b].x));
            int by = static_cast<int>(std::round(beetles_[b].y));
            set_pixel(bx, by, 60, 180, 60);
        }
    }

    // Lady Bug
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 255, 30, 30);
        set_pixel(px, py - 1, 255, 200, 180);
    } else if (state_ == STATE_LADYBUG_DIED) {
        set_pixel(px, py, 255, 120, 0);
    }
}

} // namespace arcade
