#include "game_185_congobongo.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

// Bitmask input definitions
static constexpr uint16_t BTN_UP    = 1 << 0;
static constexpr uint16_t BTN_DOWN  = 1 << 1;
static constexpr uint16_t BTN_LEFT  = 1 << 2;
static constexpr uint16_t BTN_RIGHT = 1 << 3;
static constexpr uint16_t BTN_A     = 1 << 4; // Jump
static constexpr uint16_t BTN_B     = 1 << 5; // Light match / torch

Game185CongoBongo::Game185CongoBongo() {
    Init();
}

void Game185CongoBongo::Init() {
    Reset();
}

void Game185CongoBongo::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game185CongoBongo::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 2.0f;
    py_ = 14.0f;
    speed_ = 4.5f;
    is_jumping_ = false;
    jump_timer_ = 0.0f;

    bongo_x_ = 12.0f;
    bongo_y_ = 2.0f;
    bongo_asleep_ = true;
    tail_ignited_ = false;

    for (int i = 0; i < MAX_BOULDERS; ++i) {
        boulders_[i].active = false;
    }
    boulder_spawn_timer_ = 1.0f;

    // Logs
    logs_[0] = {1.0f, 8.0f, 3.0f, 3.0f};
    logs_[1] = {9.0f, 8.0f, 3.0f, 3.0f};
    logs_[2] = {14.0f, 9.0f, -2.5f, 3.5f};
    logs_[3] = {6.0f, 9.0f, -2.5f, 3.5f};

    // Rhino
    rhinos_[0] = {1.0f, 5.0f, 4.0f, true};
    rhinos_[1] = {0.0f, 0.0f, 0.0f, false};
}

void Game185CongoBongo::SpawnBoulder() {
    for (int i = 0; i < MAX_BOULDERS; ++i) {
        if (!boulders_[i].active) {
            boulders_[i] = {10.0f, 3.0f, -3.5f, 2.2f, true};
            break;
        }
    }
}

void Game185CongoBongo::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_HUNTER_KILLED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 2.0f;
                py_ = 14.0f;
                is_jumping_ = false;
                for (int i = 0; i < MAX_BOULDERS; ++i) boulders_[i].active = false;
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

    uint16_t pressed = buttons & ~prev_buttons;

    // 1. Jump Handling (Button A)
    if ((pressed & BTN_A) && !is_jumping_) {
        is_jumping_ = true;
        jump_timer_ = 0.45f;
    }

    if (is_jumping_) {
        jump_timer_ -= dt;
        if (jump_timer_ <= 0.0f) {
            is_jumping_ = false;
        }
    }

    // 2. Hunter Movement
    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT)  dx -= 1.0f;
    if (buttons & BTN_RIGHT) dx += 1.0f;
    if (buttons & BTN_UP)    dy -= 1.0f;
    if (buttons & BTN_DOWN)  dy += 1.0f;

    if (dx != 0.0f || dy != 0.0f) {
        float inv = 1.0f / std::hypot(dx, dy);
        px_ += dx * inv * speed_ * dt;
        py_ += dy * inv * speed_ * dt;
    }

    px_ = std::max(0.5f, std::min(14.5f, px_));
    py_ = std::max(1.0f, std::min(14.5f, py_));

    // 3. Match / Torch Strike on Bongo's tail (Button B)
    if (pressed & BTN_B) {
        if (py_ <= 3.5f && std::hypot(bongo_x_ - px_, bongo_y_ - py_) < 2.5f) {
            tail_ignited_ = true;
            bongo_asleep_ = false;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 2.0f;
            score_ += 2500 + stage_ * 500;
            return;
        }
    }

    // 4. Update Logs & River Water Hazard
    bool on_log = false;
    for (int i = 0; i < MAX_LOGS; ++i) {
        logs_[i].x += logs_[i].speed * dt;
        if (logs_[i].speed > 0.0f && logs_[i].x > 16.0f) {
            logs_[i].x = -logs_[i].width;
        } else if (logs_[i].speed < 0.0f && logs_[i].x < -logs_[i].width) {
            logs_[i].x = 16.0f;
        }

        if (std::abs(py_ - logs_[i].y) < 0.6f) {
            if (px_ >= logs_[i].x && px_ <= logs_[i].x + logs_[i].width) {
                on_log = true;
                if (!is_jumping_) {
                    px_ += logs_[i].speed * dt;
                }
            }
        }
    }

    if (py_ >= 7.5f && py_ <= 9.5f) {
        if (!on_log && !is_jumping_) {
            lives_--;
            state_ = STATE_HUNTER_KILLED;
            state_timer_ = 1.0f;
            return;
        }
    }

    // 5. Update Boulders
    boulder_spawn_timer_ -= dt;
    if (boulder_spawn_timer_ <= 0.0f) {
        boulder_spawn_timer_ = std::max(1.0f, 2.5f - stage_ * 0.2f);
        SpawnBoulder();
    }

    for (int i = 0; i < MAX_BOULDERS; ++i) {
        if (!boulders_[i].active) continue;
        boulders_[i].x += boulders_[i].vx * dt;
        boulders_[i].y += boulders_[i].vy * dt;

        if (boulders_[i].x < 1.0f) {
            boulders_[i].x = 1.0f;
            boulders_[i].vx = -boulders_[i].vx;
        } else if (boulders_[i].x > 14.5f) {
            boulders_[i].x = 14.5f;
            boulders_[i].vx = -boulders_[i].vx;
        }

        if (boulders_[i].y > 15.5f) {
            boulders_[i].active = false;
            score_ += 50;
            continue;
        }

        if (!is_jumping_ && std::hypot(boulders_[i].x - px_, boulders_[i].y - py_) < 0.8f) {
            lives_--;
            state_ = STATE_HUNTER_KILLED;
            state_timer_ = 1.0f;
            return;
        }
    }

    // 6. Update Rhinos
    for (int i = 0; i < MAX_RHINOS; ++i) {
        if (!rhinos_[i].active) continue;
        rhinos_[i].x += rhinos_[i].vx * dt;
        if (rhinos_[i].x < 1.0f) {
            rhinos_[i].x = 1.0f;
            rhinos_[i].vx = -rhinos_[i].vx;
        } else if (rhinos_[i].x > 14.5f) {
            rhinos_[i].x = 14.5f;
            rhinos_[i].vx = -rhinos_[i].vx;
        }

        if (std::hypot(rhinos_[i].x - px_, rhinos_[i].y - py_) < 0.9f) {
            lives_--;
            state_ = STATE_HUNTER_KILLED;
            state_timer_ = 1.0f;
            return;
        }
    }
}

void Game185CongoBongo::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Background terrain
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (y >= 13) {
                set_pixel(x, y, 40, 120, 40);
            } else if (y >= 10 && y <= 12) {
                set_pixel(x, y, 140, 90, 50);
            } else if (y >= 8 && y <= 9) {
                set_pixel(x, y, 30, 80, 200);
            } else if (y >= 4 && y <= 7) {
                set_pixel(x, y, 160, 110, 60);
            } else {
                set_pixel(x, y, 180, 130, 70);
            }
        }
    }

    // River logs
    for (int i = 0; i < MAX_LOGS; ++i) {
        int x0 = static_cast<int>(std::floor(logs_[i].x));
        int x1 = static_cast<int>(std::ceil(logs_[i].x + logs_[i].width));
        int ly = static_cast<int>(std::round(logs_[i].y));
        for (int lx = x0; lx < x1; ++lx) {
            set_pixel(lx, ly, 110, 70, 30);
        }
    }

    // Rhinos
    for (int i = 0; i < MAX_RHINOS; ++i) {
        if (!rhinos_[i].active) continue;
        int rx = static_cast<int>(std::round(rhinos_[i].x));
        int ry = static_cast<int>(std::round(rhinos_[i].y));
        set_pixel(rx, ry, 180, 180, 190);
        int horn_x = rx + (rhinos_[i].vx > 0 ? 1 : -1);
        set_pixel(horn_x, ry, 255, 255, 255);
    }

    // Boulders
    for (int i = 0; i < MAX_BOULDERS; ++i) {
        if (!boulders_[i].active) continue;
        int bx = static_cast<int>(std::round(boulders_[i].x));
        int by = static_cast<int>(std::round(boulders_[i].y));
        set_pixel(bx, by, 220, 130, 30);
    }

    // Gorilla Bongo
    int bgx = static_cast<int>(std::round(bongo_x_));
    int bgy = static_cast<int>(std::round(bongo_y_));
    if (bongo_asleep_) {
        set_pixel(bgx, bgy, 130, 60, 20);
        set_pixel(bgx - 1, bgy, 100, 40, 10);
        set_pixel(bgx + 1, bgy, 200, 160, 120);
        set_pixel(bgx - 2, bgy + 1, 150, 80, 30);
    } else {
        set_pixel(bgx, bgy, 255, 50, 0);
        set_pixel(bgx - 1, bgy, 255, 200, 0);
        set_pixel(bgx + 1, bgy, 255, 100, 0);
    }

    // Hunter
    int hx = static_cast<int>(std::round(px_));
    int hy = static_cast<int>(std::round(py_));
    if (is_jumping_) {
        hy -= 1;
    }

    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(hx, hy, 230, 210, 50);
        set_pixel(hx, hy - 1, 220, 40, 30);
        if (tail_ignited_) {
            set_pixel(hx + 1, hy, 255, 255, 80);
        }
    } else if (state_ == STATE_HUNTER_KILLED) {
        set_pixel(hx, hy, 255, 60, 0);
    }
}

} // namespace arcade

