#include "game_168_bagman.h"
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

Game168Bagman::Game168Bagman() {
    Reset();
}

void Game168Bagman::Init() {
    Reset();
}

void Game168Bagman::Reset() {
    score_ = 0;
    lives_ = 3;
    mine_ = 1;
    InitMine();
}

bool Game168Bagman::IsPlatform(int x, int y) const {
    if (x < 0 || x >= 16) return false;
    return (y == 2 || y == 6 || y == 10 || y == 14);
}

bool Game168Bagman::IsLadder(int x, int y) const {
    if (x == 2 && y >= 2 && y <= 6) return true;
    if (x == 13 && y >= 6 && y <= 10) return true;
    if (x == 7 && y >= 10 && y <= 14) return true;
    return false;
}

void Game168Bagman::InitMine() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 2.0f;
    py_ = 2.0f;
    speed_ = 4.5f;
    carrying_bag_idx_ = -1;
    has_pickaxe_ = false;
    pickaxe_timer_ = 0.0f;

    wheelbarrow_x_ = 13.0f;
    wheelbarrow_y_ = 2.0f;
    bags_delivered_ = 0;

    bags_[0] = {4.0f, 14.0f, false};
    bags_[1] = {11.0f, 14.0f, false};

    guards_[0] = {0, 8.0f, 6.0f, 1.6f, 0.0f};
    guards_[1] = {1, 4.0f, 10.0f, -1.8f, 0.0f};

    cart_x_ = 3.0f;
    cart_vx_ = 2.5f;

    pickaxe_x_ = 8.0f;
    pickaxe_y_ = 10.0f;
    pickaxe_active_ = true;
}

void Game168Bagman::GrabOrDropBag() {
    if (carrying_bag_idx_ != -1) {
        int idx = carrying_bag_idx_;
        bags_[idx].x = px_;
        bags_[idx].y = py_;
        carrying_bag_idx_ = -1;

        for (int g = 0; g < NUM_GUARDS; ++g) {
            if (std::abs(guards_[g].x - px_) < 1.0f && std::abs(guards_[g].y - py_) < 2.0f) {
                guards_[g].stunned_timer = 3.5f;
                score_ += 300;
            }
        }
    } else {
        for (int i = 0; i < NUM_BAGS; ++i) {
            if (!bags_[i].delivered && std::hypot(bags_[i].x - px_, bags_[i].y - py_) < 1.0f) {
                carrying_bag_idx_ = i;
                break;
            }
        }
    }
}

void Game168Bagman::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            mine_++;
            InitMine();
        }
        return;
    }

    if (state_ == STATE_BAGMAN_CAUGHT) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 2.0f;
                py_ = 2.0f;
                carrying_bag_idx_ = -1;
                has_pickaxe_ = false;
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

    if (has_pickaxe_) {
        pickaxe_timer_ -= dt;
        if (pickaxe_timer_ <= 0.0f) has_pickaxe_ = false;
    }

    float cur_speed = (carrying_bag_idx_ != -1) ? (speed_ * 0.5f) : speed_;

    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        GrabOrDropBag();
    }

    int ix = static_cast<int>(std::round(px_));
    int iy = static_cast<int>(std::round(py_));
    bool on_ladder = IsLadder(ix, iy) || IsLadder(ix, iy + 1);

    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT)  dx -= 1.0f;
    if (buttons & BTN_RIGHT) dx += 1.0f;

    // Carrying heavy bag blocks ladder climbing
    if (on_ladder && carrying_bag_idx_ == -1) {
        if (buttons & BTN_UP)   dy -= 1.0f;
        if (buttons & BTN_DOWN) dy += 1.0f;
    }

    px_ += dx * cur_speed * dt;
    py_ += dy * cur_speed * dt;

    px_ = std::max(1.0f, std::min(14.5f, px_));
    py_ = std::max(2.0f, std::min(14.0f, py_));

    if (carrying_bag_idx_ != -1) {
        bags_[carrying_bag_idx_].x = px_;
        bags_[carrying_bag_idx_].y = py_;

        if (std::hypot(wheelbarrow_x_ - px_, wheelbarrow_y_ - py_) < 1.2f) {
            bags_[carrying_bag_idx_].delivered = true;
            carrying_bag_idx_ = -1;
            bags_delivered_++;
            score_ += 1000;

            if (bags_delivered_ >= NUM_BAGS) {
                state_ = STATE_STAGE_CLEAR;
                state_timer_ = 2.0f;
                score_ += 2000;
                return;
            }
        }
    }

    if (pickaxe_active_ && std::hypot(pickaxe_x_ - px_, pickaxe_y_ - py_) < 1.0f) {
        pickaxe_active_ = false;
        has_pickaxe_ = true;
        pickaxe_timer_ = 5.0f;
        score_ += 200;
    }

    // Ore Cart
    cart_x_ += cart_vx_ * dt;
    if (cart_x_ <= 2.0f || cart_x_ >= 13.0f) cart_vx_ = -cart_vx_;

    if (std::abs(py_ - 6.0f) < 0.6f && std::abs(cart_x_ - px_) < 1.0f) {
        lives_--;
        state_ = STATE_BAGMAN_CAUGHT;
        state_timer_ = 1.0f;
        return;
    }

    // Guards
    for (int g = 0; g < NUM_GUARDS; ++g) {
        if (guards_[g].stunned_timer > 0.0f) {
            guards_[g].stunned_timer -= dt;
            continue;
        }

        guards_[g].x += guards_[g].vx * dt;
        if (guards_[g].x <= 2.0f || guards_[g].x >= 13.0f) guards_[g].vx = -guards_[g].vx;

        if (std::hypot(guards_[g].x - px_, guards_[g].y - py_) < 0.9f) {
            if (has_pickaxe_) {
                guards_[g].stunned_timer = 4.0f;
                score_ += 400;
            } else {
                lives_--;
                state_ = STATE_BAGMAN_CAUGHT;
                state_timer_ = 1.0f;
                return;
            }
        }
    }
}

void Game168Bagman::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Shaft beams
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsPlatform(x, y)) {
                set_pixel(x, y, 110, 80, 50);
            } else if (IsLadder(x, y)) {
                set_pixel(x, y, 220, 220, 0);
            }
        }
    }

    // Surface Wheelbarrow
    set_pixel(13, 2, 255, 120, 0);
    set_pixel(14, 2, 200, 100, 0);

    // Ore Cart (y=6)
    int cx = static_cast<int>(std::round(cart_x_));
    set_pixel(cx, 6, 80, 80, 255);
    set_pixel(cx + 1, 6, 80, 80, 255);

    // Pickaxe
    if (pickaxe_active_) {
        int px = static_cast<int>(std::round(pickaxe_x_));
        int py = static_cast<int>(std::round(pickaxe_y_));
        set_pixel(px, py, 200, 220, 240);
    }

    // Gold Bags
    for (int i = 0; i < NUM_BAGS; ++i) {
        if (!bags_[i].delivered) {
            int bx = static_cast<int>(std::round(bags_[i].x));
            int by = static_cast<int>(std::round(bags_[i].y));
            set_pixel(bx, by, 255, 230, 20);
        }
    }

    // Guards
    for (int g = 0; g < NUM_GUARDS; ++g) {
        int gx = static_cast<int>(std::round(guards_[g].x));
        int gy = static_cast<int>(std::round(guards_[g].y));
        if (guards_[g].stunned_timer > 0.0f) {
            set_pixel(gx, gy, 255, 180, 50);
        } else {
            set_pixel(gx, gy, 40, 80, 255);
        }
    }

    // Bagman
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        if (has_pickaxe_) {
            set_pixel(px, py, 255, 255, 255);
        } else {
            set_pixel(px, py, 255, 220, 60);
        }
        if (carrying_bag_idx_ != -1) {
            set_pixel(px + 1, py, 255, 200, 0);
        }
    } else if (state_ == STATE_BAGMAN_CAUGHT) {
        set_pixel(px, py, 255, 60, 0);
    }
}

} // namespace arcade

