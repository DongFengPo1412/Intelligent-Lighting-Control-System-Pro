#include "game_190_demolitionderby.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_LEFT  = 1 << 2;
static constexpr uint16_t BTN_RIGHT = 1 << 3;
static constexpr uint16_t BTN_A     = 1 << 4; // Throttle Forward
static constexpr uint16_t BTN_B     = 1 << 5; // Reverse Ram

Game190DemolitionDerby::Game190DemolitionDerby() {
    Init();
}

void Game190DemolitionDerby::Init() {
    Reset();
}

void Game190DemolitionDerby::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game190DemolitionDerby::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 8.0f;
    py_ = 12.0f;
    angle_ = -3.14159265f / 2.0f;
    vx_ = 0.0f;
    vy_ = 0.0f;
    speed_ = 0.0f;
    hp_ = 100.0f;

    float r_hp = 70.0f + stage_ * 15.0f;
    rivals_[0] = {4.0f, 4.0f, 3.14159265f / 4.0f, 0.0f, 0.0f, 0.0f, r_hp, true, 230, 40, 40};
    rivals_[1] = {12.0f, 4.0f, 3.0f * 3.14159265f / 4.0f, 0.0f, 0.0f, 0.0f, r_hp, true, 40, 100, 230};
    rivals_[2] = {8.0f, 2.5f, 3.14159265f / 2.0f, 0.0f, 0.0f, 0.0f, r_hp, true, 240, 210, 30};
}

void Game190DemolitionDerby::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_CAR_WRECKED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 8.0f;
                py_ = 12.0f;
                angle_ = -3.14159265f / 2.0f;
                vx_ = 0.0f;
                vy_ = 0.0f;
                speed_ = 0.0f;
                hp_ = 100.0f;
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

    // Steering
    if (buttons & BTN_LEFT)  angle_ -= 3.5f * dt;
    if (buttons & BTN_RIGHT) angle_ += 3.5f * dt;

    // Throttle / Reverse
    if (buttons & BTN_A) {
        speed_ = std::min(7.5f, speed_ + 12.0f * dt);
    } else if (buttons & BTN_B) {
        speed_ = std::max(-4.5f, speed_ - 12.0f * dt);
    } else {
        if (speed_ > 0.0f) speed_ = std::max(0.0f, speed_ - 4.0f * dt);
        else if (speed_ < 0.0f) speed_ = std::min(0.0f, speed_ + 4.0f * dt);
    }

    vx_ = std::cos(angle_) * speed_;
    vy_ = std::sin(angle_) * speed_;
    px_ += vx_ * dt;
    py_ += vy_ * dt;

    // Walls
    if (px_ < 1.5f) { px_ = 1.5f; vx_ = -vx_ * 0.5f; speed_ *= -0.4f; }
    else if (px_ > 14.5f) { px_ = 14.5f; vx_ = -vx_ * 0.5f; speed_ *= -0.4f; }
    if (py_ < 1.5f) { py_ = 1.5f; vy_ = -vy_ * 0.5f; speed_ *= -0.4f; }
    else if (py_ > 14.5f) { py_ = 14.5f; vy_ = -vy_ * 0.5f; speed_ *= -0.4f; }

    // Rivals AI
    for (int i = 0; i < MAX_RIVALS; ++i) {
        if (!rivals_[i].alive) continue;
        float t_dx = px_ - rivals_[i].x;
        float t_dy = py_ - rivals_[i].y;
        float desired = std::atan2(t_dy, t_dx);

        float diff = std::fmod(desired - rivals_[i].angle + 3.14159265f, 2.0f * 3.14159265f) - 3.14159265f;
        rivals_[i].angle += std::max(-3.0f * dt, std::min(3.0f * dt, diff));

        float max_s = 4.8f + stage_ * 0.3f;
        rivals_[i].speed = std::min(max_s, rivals_[i].speed + 8.0f * dt);
        rivals_[i].vx = std::cos(rivals_[i].angle) * rivals_[i].speed;
        rivals_[i].vy = std::sin(rivals_[i].angle) * rivals_[i].speed;

        rivals_[i].x += rivals_[i].vx * dt;
        rivals_[i].y += rivals_[i].vy * dt;
        rivals_[i].x = std::max(1.5f, std::min(14.5f, rivals_[i].x));
        rivals_[i].y = std::max(1.5f, std::min(14.5f, rivals_[i].y));
    }

    // Collisions
    for (int i = 0; i < MAX_RIVALS; ++i) {
        float dist = std::hypot(px_ - rivals_[i].x, py_ - rivals_[i].y);
        if (dist < 1.5f) {
            float rel_v = std::hypot(vx_ - rivals_[i].vx, vy_ - rivals_[i].vy);
            float force = std::max(10.0f, rel_v * 8.0f);

            float p_fwd_x = std::cos(angle_);
            float p_fwd_y = std::sin(angle_);
            float dir_x = (rivals_[i].x - px_) / std::max(0.01f, dist);
            float dir_y = (rivals_[i].y - py_) / std::max(0.01f, dist);

            float dot = p_fwd_x * dir_x + p_fwd_y * dir_y;

            if (rivals_[i].alive) {
                if (dot > 0.4f) {
                    hp_ -= force * 0.4f;
                    rivals_[i].hp -= force * 0.8f;
                    score_ += static_cast<uint32_t>(force * 5.0f);
                } else if (dot < -0.4f) {
                    hp_ -= force * 0.15f;
                    rivals_[i].hp -= force * 0.9f;
                    score_ += static_cast<uint32_t>(force * 8.0f);
                } else {
                    hp_ -= force * 0.5f;
                    rivals_[i].hp -= force * 0.6f;
                    score_ += static_cast<uint32_t>(force * 4.0f);
                }

                if (rivals_[i].hp <= 0.0f) {
                    rivals_[i].hp = 0.0f;
                    rivals_[i].alive = false;
                    rivals_[i].speed = 0.0f;
                    score_ += 2000;
                }
            } else {
                hp_ -= force * 0.2f;
            }

            speed_ = -speed_ * 0.6f;
            rivals_[i].speed = -rivals_[i].speed * 0.6f;
            px_ -= dir_x * 0.5f;
            py_ -= dir_y * 0.5f;
            rivals_[i].x += dir_x * 0.5f;
            rivals_[i].y += dir_y * 0.5f;
        }
    }

    if (hp_ <= 0.0f) {
        hp_ = 0.0f;
        lives_--;
        state_ = STATE_CAR_WRECKED;
        state_timer_ = 1.5f;
        return;
    }

    bool any_alive = false;
    for (int i = 0; i < MAX_RIVALS; ++i) {
        if (rivals_[i].alive) any_alive = true;
    }

    if (!any_alive) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 2.0f;
        score_ += 5000;
    }
}

void Game190DemolitionDerby::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Track
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                set_pixel(x, y, 90, 80, 80);
            } else {
                set_pixel(x, y, 110, 75, 45);
            }
        }
    }

    // Rivals
    for (int i = 0; i < MAX_RIVALS; ++i) {
        int rx = static_cast<int>(std::round(rivals_[i].x));
        int ry = static_cast<int>(std::round(rivals_[i].y));
        if (rivals_[i].alive) {
            set_pixel(rx, ry, rivals_[i].r, rivals_[i].g, rivals_[i].b);
            int fx = static_cast<int>(std::round(rivals_[i].x + std::cos(rivals_[i].angle)));
            int fy = static_cast<int>(std::round(rivals_[i].y + std::sin(rivals_[i].angle)));
            set_pixel(fx, fy, 255, 255, 255);
        } else {
            set_pixel(rx, ry, 50, 50, 50);
            set_pixel(rx, ry - 1, 255, 80, 0);
        }
    }

    // Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 40, 220, 40);
        int fx = static_cast<int>(std::round(px_ + std::cos(angle_)));
        int fy = static_cast<int>(std::round(py_ + std::sin(angle_)));
        set_pixel(fx, fy, 255, 255, 100);
        int bx = static_cast<int>(std::round(px_ - std::cos(angle_)));
        int by = static_cast<int>(std::round(py_ - std::sin(angle_)));
        set_pixel(bx, by, 180, 40, 40);
    } else if (state_ == STATE_CAR_WRECKED) {
        set_pixel(px, py, 255, 60, 0);
    }
}

} // namespace arcade
