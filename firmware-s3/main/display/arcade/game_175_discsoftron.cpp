#include "game_175_discsoftron.h"
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

Game175DiscsOfTron::Game175DiscsOfTron() {
    Reset();
}

void Game175DiscsOfTron::Init() {
    Reset();
}

void Game175DiscsOfTron::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game175DiscsOfTron::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 13.0f;
    speed_ = 6.5f;
    shield_active_ = false;
    shield_energy_ = 100.0f;

    sx_ = 7.5f;
    sy_ = 2.5f;
    sark_hp_ = 3;
    sark_dir_ = 1.0f;
    sark_speed_ = 3.0f + stage_ * 0.4f;
    sark_throw_timer_ = 1.2f;

    for (int i = 0; i < MAX_DISCS; ++i) discs_[i].active = false;
}

void Game175DiscsOfTron::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_SARK_FALLING) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_PLAYER_DIED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                py_ = 13.0f;
                shield_active_ = false;
                for (int i = 0; i < MAX_DISCS; ++i) discs_[i].active = false;
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

    // Flynn movement
    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT)  dx -= 1.0f;
    if (buttons & BTN_RIGHT) dx += 1.0f;
    if (buttons & BTN_UP)    dy -= 1.0f;
    if (buttons & BTN_DOWN)  dy += 1.0f;

    if (dx != 0.0f || dy != 0.0f) {
        px_ += dx * speed_ * dt;
        py_ += dy * speed_ * dt;
    }
    px_ = std::max(2.5f, std::min(12.5f, px_));
    py_ = std::max(10.5f, std::min(14.0f, py_));

    // Deflection shield (Button B)
    if ((buttons & BTN_B) && shield_energy_ > 0.0f) {
        shield_active_ = true;
        shield_energy_ = std::max(0.0f, shield_energy_ - 35.0f * dt);
    } else {
        shield_active_ = false;
        shield_energy_ = std::min(100.0f, shield_energy_ + 20.0f * dt);
    }

    // Throw Energy Disc (Button A)
    int player_discs_count = 0;
    for (int i = 0; i < MAX_DISCS; ++i) {
        if (discs_[i].active && discs_[i].is_player) player_discs_count++;
    }

    if ((buttons & BTN_A) && !(prev_buttons & BTN_A) && player_discs_count < 2) {
        for (int i = 0; i < MAX_DISCS; ++i) {
            if (!discs_[i].active) {
                float vx = (px_ < 7.5f) ? 4.0f : -4.0f;
                if (dx != 0.0f) vx = dx * 6.0f;
                discs_[i] = {px_, py_ - 1.0f, vx, -12.0f, true, true};
                break;
            }
        }
    }

    // Sark AI
    sx_ += sark_dir_ * sark_speed_ * dt;
    if (sx_ > 12.0f) { sx_ = 12.0f; sark_dir_ = -1.0f; }
    else if (sx_ < 3.0f) { sx_ = 3.0f; sark_dir_ = 1.0f; }

    sark_throw_timer_ -= dt;
    if (sark_throw_timer_ <= 0.0f) {
        sark_throw_timer_ = std::max(0.8f, 1.8f - stage_ * 0.15f);
        for (int i = 0; i < MAX_DISCS; ++i) {
            if (!discs_[i].active) {
                float sark_vx = (px_ - sx_) * 0.8f;
                discs_[i] = {sx_, sy_ + 1.0f, sark_vx, 8.0f + stage_ * 0.5f, false, true};
                break;
            }
        }
    }

    // Update Discs
    for (int i = 0; i < MAX_DISCS; ++i) {
        if (!discs_[i].active) continue;

        discs_[i].x += discs_[i].vx * dt;
        discs_[i].y += discs_[i].vy * dt;

        // Side wall bounce
        if (discs_[i].x <= 1.5f) {
            discs_[i].x = 1.5f;
            discs_[i].vx = std::abs(discs_[i].vx);
        } else if (discs_[i].x >= 13.5f) {
            discs_[i].x = 13.5f;
            discs_[i].vx = -std::abs(discs_[i].vx);
        }

        // Out of arena
        if (discs_[i].y < 0.5f || discs_[i].y > 15.5f) {
            discs_[i].active = false;
            continue;
        }

        // Player disc hits Sark
        if (discs_[i].is_player) {
            if (std::hypot(discs_[i].x - sx_, discs_[i].y - sy_) < 1.1f) {
                discs_[i].active = false;
                sark_hp_--;
                score_ += 500;
                if (sark_hp_ <= 0) {
                    state_ = STATE_SARK_FALLING;
                    state_timer_ = 2.0f;
                    score_ += 3000;
                    return;
                }
            }
        } else {
            // Sark disc hits Flynn
            if (std::hypot(discs_[i].x - px_, discs_[i].y - py_) < 1.2f) {
                if (shield_active_) {
                    discs_[i].is_player = true;
                    discs_[i].vy = -std::abs(discs_[i].vy) * 1.2f;
                    discs_[i].vx = -discs_[i].vx;
                    score_ += 250;
                } else {
                    lives_--;
                    state_ = STATE_PLAYER_DIED;
                    state_timer_ = 1.0f;
                    return;
                }
            }
        }
    }

    // Mid-air clashes
    for (int i = 0; i < MAX_DISCS; ++i) {
        if (!discs_[i].active) continue;
        for (int j = i + 1; j < MAX_DISCS; ++j) {
            if (!discs_[j].active) continue;
            if (std::hypot(discs_[i].x - discs_[j].x, discs_[i].y - discs_[j].y) < 0.8f) {
                discs_[i].vx = -discs_[i].vx;
                discs_[j].vx = -discs_[j].vx;
                discs_[i].vy = -discs_[i].vy;
                discs_[j].vy = -discs_[j].vy;
                score_ += 50;
            }
        }
    }
}

void Game175DiscsOfTron::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Deflection conduits
    for (int y = 0; y < 16; ++y) {
        set_pixel(1, y, 40, 100, 180);
        set_pixel(14, y, 40, 100, 180);
    }

    // Sark ring
    for (int x = 3; x <= 12; ++x) set_pixel(x, 3, 160, 40, 40);

    // Flynn ring
    for (int x = 3; x <= 12; ++x) set_pixel(x, 14, 0, 140, 200);

    // Discs
    for (int i = 0; i < MAX_DISCS; ++i) {
        if (discs_[i].active) {
            int dx = static_cast<int>(std::round(discs_[i].x));
            int dy = static_cast<int>(std::round(discs_[i].y));
            if (discs_[i].is_player) set_pixel(dx, dy, 80, 240, 255);
            else set_pixel(dx, dy, 255, 60, 40);
        }
    }

    // Sark
    int sx = static_cast<int>(std::round(sx_));
    int sy = static_cast<int>(std::round(sy_));
    if (state_ == STATE_PLAYING || state_ == STATE_PLAYER_DIED) {
        set_pixel(sx, sy, 255, 30, 30);
        set_pixel(sx, sy - 1, 255, 200, 0);
        set_pixel(sx - 1, sy, 200, 20, 20);
        set_pixel(sx + 1, sy, 200, 20, 20);
    } else if (state_ == STATE_SARK_FALLING) {
        int fall_y = static_cast<int>(sy + (2.0f - state_timer_) * 6.0f);
        set_pixel(sx, fall_y, 255, 100, 0);
    }

    // Flynn
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_SARK_FALLING) {
        set_pixel(px, py, 40, 200, 255);
        set_pixel(px, py - 1, 100, 240, 255);
        set_pixel(px - 1, py, 20, 140, 220);
        set_pixel(px + 1, py, 20, 140, 220);

        if (shield_active_) {
            set_pixel(px - 1, py - 1, 255, 255, 80);
            set_pixel(px, py - 2, 255, 255, 140);
            set_pixel(px + 1, py - 1, 255, 255, 80);
        }
    } else if (state_ == STATE_PLAYER_DIED) {
        set_pixel(px, py, 255, 100, 0);
        set_pixel(px - 1, py, 255, 0, 0);
        set_pixel(px + 1, py, 255, 0, 0);
    }
}

} // namespace arcade
