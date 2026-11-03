#include "game_167_crystalcastles.h"
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

Game167CrystalCastles::Game167CrystalCastles() {
    Reset();
}

void Game167CrystalCastles::Init() {
    Reset();
}

void Game167CrystalCastles::Reset() {
    score_ = 0;
    lives_ = 3;
    castle_ = 1;
    InitCastle();
}

bool Game167CrystalCastles::IsPlatform(int x, int y) const {
    if (y == 14) return (x >= 0 && x <= 15);
    if (y == 10) return (x >= 3 && x <= 12);
    if (y == 6)  return (x >= 5 && x <= 14);
    if (y == 2)  return (x >= 2 && x <= 8);
    return false;
}

bool Game167CrystalCastles::IsStairs(int x, int y) const {
    if (x == 3 && y >= 11 && y <= 13) return true;
    if (x == 11 && y >= 7 && y <= 9) return true;
    if (x == 5 && y >= 3 && y <= 5) return true;
    return false;
}

uint8_t Game167CrystalCastles::GetGemsLeft() const {
    uint8_t count = 0;
    for (int i = 0; i < NUM_GEMS; ++i) {
        if (!gems_[i].collected) count++;
    }
    return count;
}

void Game167CrystalCastles::InitCastle() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 2.0f;
    py_ = 13.0f;
    vx_ = 0.0f;
    vy_ = 0.0f;
    speed_ = 4.8f;
    is_jumping_ = false;
    invulnerable_timer_ = 0.0f;

    static const float gem_coords[NUM_GEMS][2] = {
        {2.0f, 13.0f}, {6.0f, 13.0f}, {10.0f, 13.0f}, {14.0f, 13.0f},
        {4.0f, 9.0f}, {7.0f, 9.0f}, {10.0f, 9.0f},
        {6.0f, 5.0f}, {9.0f, 5.0f}, {13.0f, 5.0f},
        {3.0f, 1.0f}, {7.0f, 1.0f}
    };

    for (int i = 0; i < NUM_GEMS; ++i) {
        gems_[i] = {gem_coords[i][0], gem_coords[i][1], false};
    }

    honey_pot_x_ = 8.0f;
    honey_pot_y_ = 1.0f;
    honey_pot_active_ = true;

    gem_eater_ = {5.0f, 9.0f, 1.8f, true};
    witch_ = {12.0f, 5.0f, -2.2f, true};
}

void Game167CrystalCastles::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            castle_++;
            InitCastle();
        }
        return;
    }

    if (state_ == STATE_BENTLEY_DIED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 2.0f;
                py_ = 13.0f;
                is_jumping_ = false;
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

    if (invulnerable_timer_ > 0.0f) invulnerable_timer_ -= dt;

    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT)  dx -= 1.0f;
    if (buttons & BTN_RIGHT) dx += 1.0f;
    if (buttons & BTN_UP)    dy -= 1.0f;
    if (buttons & BTN_DOWN)  dy += 1.0f;

    if (dx != 0.0f || dy != 0.0f) {
        float len = std::hypot(dx, dy);
        px_ += (dx / len) * speed_ * dt;
        py_ += (dy / len) * speed_ * dt;
    }

    px_ = std::max(1.0f, std::min(14.5f, px_));
    py_ = std::max(1.0f, std::min(14.0f, py_));

    if ((buttons & BTN_A) && !(prev_buttons & BTN_A) && !is_jumping_) {
        is_jumping_ = true;
        vy_ = -6.0f;
    }

    if (is_jumping_) {
        py_ += vy_ * dt;
        vy_ += 18.0f * dt;
        if (vy_ > 6.0f) {
            is_jumping_ = false;
            vy_ = 0.0f;
        }
    }

    // Portal Warp
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        if (std::abs(px_ - 1.5f) < 1.0f && std::abs(py_ - 13.0f) < 1.0f) {
            px_ = 3.0f; py_ = 1.5f;
        } else if (std::abs(px_ - 3.0f) < 1.0f && std::abs(py_ - 1.5f) < 1.0f) {
            px_ = 1.5f; py_ = 13.0f;
        }
    }

    // Gem Collection
    for (int i = 0; i < NUM_GEMS; ++i) {
        if (!gems_[i].collected && std::hypot(gems_[i].x - px_, gems_[i].y - py_) < 0.9f) {
            gems_[i].collected = true;
            uint8_t rem = GetGemsLeft();
            if (rem == 0) {
                score_ += 500; // Last gem bonus!
                state_ = STATE_STAGE_CLEAR;
                state_timer_ = 2.0f;
                score_ += 2000;
                return;
            } else {
                score_ += 100;
            }
        }
    }

    // Honey Pot
    if (honey_pot_active_ && std::hypot(honey_pot_x_ - px_, honey_pot_y_ - py_) < 1.0f) {
        honey_pot_active_ = false;
        invulnerable_timer_ = 4.0f;
        score_ += 500;
    }

    // Gem Eater
    if (gem_eater_.alive) {
        gem_eater_.x += gem_eater_.vx * dt;
        if (gem_eater_.x <= 3.0f || gem_eater_.x >= 12.0f) {
            gem_eater_.vx = -gem_eater_.vx;
        }

        for (int i = 0; i < NUM_GEMS; ++i) {
            if (!gems_[i].collected && std::hypot(gems_[i].x - gem_eater_.x, gems_[i].y - gem_eater_.y) < 0.8f) {
                gems_[i].collected = true;
            }
        }

        if (std::hypot(gem_eater_.x - px_, gem_eater_.y - py_) < 1.0f) {
            if (is_jumping_ || invulnerable_timer_ > 0.0f) {
                gem_eater_.alive = false;
                score_ += 500;
            } else {
                lives_--;
                state_ = STATE_BENTLEY_DIED;
                state_timer_ = 1.0f;
                return;
            }
        }
    }

    // Witch
    if (witch_.alive) {
        witch_.x += witch_.vx * dt;
        if (witch_.x <= 4.0f || witch_.x >= 14.0f) {
            witch_.vx = -witch_.vx;
        }

        if (std::hypot(witch_.x - px_, witch_.y - py_) < 1.0f) {
            if (invulnerable_timer_ > 0.0f) {
                witch_.alive = false;
                score_ += 3000;
            } else {
                lives_--;
                state_ = STATE_BENTLEY_DIED;
                state_timer_ = 1.0f;
                return;
            }
        }
    }
}

void Game167CrystalCastles::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Platforms
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsPlatform(x, y)) {
                set_pixel(x, y, 60, 90, 180);
            } else if (IsStairs(x, y)) {
                set_pixel(x, y, 100, 130, 220);
            }
        }
    }

    // Portals
    set_pixel(1, 13, 180, 0, 220);
    set_pixel(3, 1, 180, 0, 220);

    // Gems
    for (int i = 0; i < NUM_GEMS; ++i) {
        if (!gems_[i].collected) {
            int gx = static_cast<int>(std::round(gems_[i].x));
            int gy = static_cast<int>(std::round(gems_[i].y));
            set_pixel(gx, gy, 0, 255, 255);
        }
    }

    // Honey pot
    if (honey_pot_active_) {
        int hx = static_cast<int>(std::round(honey_pot_x_));
        int hy = static_cast<int>(std::round(honey_pot_y_));
        set_pixel(hx, hy, 255, 180, 0);
    }

    // Gem eater
    if (gem_eater_.alive) {
        int ex = static_cast<int>(std::round(gem_eater_.x));
        int ey = static_cast<int>(std::round(gem_eater_.y));
        set_pixel(ex, ey, 50, 220, 50);
        set_pixel(ex + 1, ey, 30, 160, 30);
    }

    // Witch
    if (witch_.alive) {
        int wx = static_cast<int>(std::round(witch_.x));
        int wy = static_cast<int>(std::round(witch_.y));
        set_pixel(wx, wy, 200, 30, 180);
        set_pixel(wx, wy - 1, 255, 40, 40);
    }

    // Bentley
    int bx = static_cast<int>(std::round(px_));
    int by = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        if (invulnerable_timer_ > 0.0f) {
            set_pixel(bx, by, 255, 255, 255);
            set_pixel(bx, by - 1, 255, 220, 0);
        } else {
            set_pixel(bx, by, 180, 100, 40);
            set_pixel(bx, by - 1, 240, 60, 60);
        }
    } else if (state_ == STATE_BENTLEY_DIED) {
        set_pixel(bx, by, 255, 80, 0);
    }
}

} // namespace arcade

