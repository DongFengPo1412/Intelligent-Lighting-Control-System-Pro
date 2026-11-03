#include "game_131_solarfox.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace arcade {

static constexpr float ARENA_MIN = 1.5f;
static constexpr float ARENA_MAX = 13.5f;

Game131SolarFox::Game131SolarFox() {
    Init();
}

void Game131SolarFox::Init() {
    score_ = 0;
    lives_ = 3;
    quadrant_ = 1;
    InitQuadrant();
}

void Game131SolarFox::Reset() {
    Init();
}

void Game131SolarFox::InitQuadrant() {
    state_ = STATE_FLYING;
    state_timer_ = 0.0f;

    px_ = 7.5f;
    py_ = 12.0f;
    dir_x_ = 0;
    dir_y_ = -1; // Heading UP
    next_dir_x_ = 0;
    next_dir_y_ = -1;
    is_hyperspeed_ = false;
    shield_timer_ = 0.0f;
    shield_cooldown_ = 0.0f;

    // Initialize 8x8 solar energy cells inside [4, 11]
    remaining_cells_ = 0;
    for (int y = 0; y < MATRIX_H; ++y) {
        for (int x = 0; x < MATRIX_W; ++x) {
            if (x >= 1 && x <= 8 && y >= 1 && y <= 8) {
                // Checkerboard pattern or hollow square depending on quadrant
                bool active = (quadrant_ % 2 == 1) ? ((x + y) % 2 == 0) : true;
                cells_[y][x] = active;
                if (active) remaining_cells_++;
            } else {
                cells_[y][x] = false;
            }
        }
    }

    // 4 Sentinels
    float base_speed = 3.5f + quadrant_ * 0.4f;
    sentinels_[0] = {4.0f, base_speed, 1.0f};          // Top
    sentinels_[1] = {11.0f, -base_speed, 1.8f};        // Bottom
    sentinels_[2] = {5.0f, base_speed * 0.9f, 2.5f};   // Left
    sentinels_[3] = {10.0f, -base_speed * 0.9f, 3.2f}; // Right

    for (int i = 0; i < MAX_FIREBALLS; ++i) {
        fireballs_[i].active = false;
    }
}

void Game131SolarFox::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & 0x0030) && !(prev_buttons & 0x0030)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_SHIP_EXPLODING) {
        if (state_timer_ > 1.3f) {
            lives_--;
            if (lives_ == 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_FLYING;
                px_ = 7.5f;
                py_ = 12.0f;
                dir_x_ = 0;
                dir_y_ = -1;
                next_dir_x_ = 0;
                next_dir_y_ = -1;
                shield_timer_ = 0.0f;
            }
        }
        return;
    }

    if (state_ == STATE_QUADRANT_CLEAR) {
        if (state_timer_ > 1.6f) {
            quadrant_++;
            score_ += 1500;
            InitQuadrant();
        }
        return;
    }

    // Button A: Hyperspeed toggle/hold
    is_hyperspeed_ = (buttons & 0x0010) != 0;

    // Button B: Shield activation
    if (shield_cooldown_ > 0.0f) shield_cooldown_ -= dt;
    if ((buttons & 0x0020) && !(prev_buttons & 0x0020)) {
        if (shield_cooldown_ <= 0.0f) {
            shield_timer_ = 0.8f;
            shield_cooldown_ = 3.0f;
        }
    }
    if (shield_timer_ > 0.0f) shield_timer_ -= dt;

    UpdateShip(dt, buttons);
    UpdateSentinels(dt);
    UpdateFireballs(dt);
    CheckCollisions();

    // Check completion
    if (remaining_cells_ == 0) {
        state_ = STATE_QUADRANT_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game131SolarFox::UpdateShip(float dt, uint16_t buttons) {
    if (buttons & 0x0001) { next_dir_x_ = 0; next_dir_y_ = -1; } // UP
    if (buttons & 0x0002) { next_dir_x_ = 0; next_dir_y_ = 1; }  // DOWN
    if (buttons & 0x0004) { next_dir_x_ = -1; next_dir_y_ = 0; } // LEFT
    if (buttons & 0x0008) { next_dir_x_ = 1; next_dir_y_ = 0; }  // RIGHT

    // Can turn or reverse
    if (next_dir_x_ != 0 || next_dir_y_ != 0) {
        dir_x_ = next_dir_x_;
        dir_y_ = next_dir_y_;
    }

    float speed = is_hyperspeed_ ? 11.5f : 6.0f;
    px_ += (float)dir_x_ * speed * dt;
    py_ += (float)dir_y_ * speed * dt;

    // Boundary bounce / clamping
    if (px_ <= ARENA_MIN) { px_ = ARENA_MIN; dir_x_ = 1; }
    if (px_ >= ARENA_MAX) { px_ = ARENA_MAX; dir_x_ = -1; }
    if (py_ <= ARENA_MIN) { py_ = ARENA_MIN; dir_y_ = 1; }
    if (py_ >= ARENA_MAX) { py_ = ARENA_MAX; dir_y_ = -1; }
}

void Game131SolarFox::UpdateSentinels(float dt) {
    for (int i = 0; i < NUM_SENTINELS; ++i) {
        sentinels_[i].pos += sentinels_[i].speed * dt;
        if (sentinels_[i].pos < 2.0f) {
            sentinels_[i].pos = 2.0f;
            sentinels_[i].speed = -sentinels_[i].speed;
        } else if (sentinels_[i].pos > 13.0f) {
            sentinels_[i].pos = 13.0f;
            sentinels_[i].speed = -sentinels_[i].speed;
        }

        // Fire cooldown
        sentinels_[i].fire_cooldown -= dt;
        if (sentinels_[i].fire_cooldown <= 0.0f) {
            sentinels_[i].fire_cooldown = 2.8f - quadrant_ * 0.15f;
            if (sentinels_[i].fire_cooldown < 1.0f) sentinels_[i].fire_cooldown = 1.0f;

            // Spawn fireball towards player
            for (int f = 0; f < MAX_FIREBALLS; ++f) {
                if (!fireballs_[f].active) {
                    fireballs_[f].active = true;
                    float sx = 0.0f, sy = 0.0f;
                    if (i == 0) { sx = sentinels_[i].pos; sy = 1.0f; }       // Top
                    else if (i == 1) { sx = sentinels_[i].pos; sy = 14.0f; }  // Bottom
                    else if (i == 2) { sx = 1.0f; sy = sentinels_[i].pos; }   // Left
                    else { sx = 14.0f; sy = sentinels_[i].pos; }              // Right

                    fireballs_[f].x = sx;
                    fireballs_[f].y = sy;

                    float dx = px_ - sx;
                    float dy = py_ - sy;
                    float dist = std::sqrt(dx * dx + dy * dy);
                    float fb_speed = 6.5f + quadrant_ * 0.3f;
                    if (dist > 0.1f) {
                        fireballs_[f].vx = (dx / dist) * fb_speed;
                        fireballs_[f].vy = (dy / dist) * fb_speed;
                    }
                    break;
                }
            }
        }
    }
}

void Game131SolarFox::UpdateFireballs(float dt) {
    for (int i = 0; i < MAX_FIREBALLS; ++i) {
        if (!fireballs_[i].active) continue;
        fireballs_[i].x += fireballs_[i].vx * dt;
        fireballs_[i].y += fireballs_[i].vy * dt;

        if (fireballs_[i].x < 0.5f || fireballs_[i].x > 15.0f ||
            fireballs_[i].y < 0.5f || fireballs_[i].y > 15.0f) {
            fireballs_[i].active = false;
        }
    }
}

void Game131SolarFox::CheckCollisions() {
    // 1. Ship harvesting Energy Cells
    int cell_x = (int)std::round(px_) - 3;
    int cell_y = (int)std::round(py_) - 3;
    if (cell_x >= 0 && cell_x < MATRIX_W && cell_y >= 0 && cell_y < MATRIX_H) {
        if (cells_[cell_y][cell_x]) {
            cells_[cell_y][cell_x] = false;
            remaining_cells_--;
            score_ += is_hyperspeed_ ? 40 : 20; // Double points for hyperspeed harvesting!
        }
    }

    // 2. Fireballs vs Ship
    for (int i = 0; i < MAX_FIREBALLS; ++i) {
        if (!fireballs_[i].active) continue;
        float dx = std::abs(px_ - fireballs_[i].x);
        float dy = std::abs(py_ - fireballs_[i].y);
        if (dx < 0.8f && dy < 0.8f) {
            fireballs_[i].active = false;
            if (shield_timer_ > 0.0f) {
                // Deflected by shield!
                score_ += 50;
            } else {
                // Ship destroyed!
                state_ = STATE_SHIP_EXPLODING;
                state_timer_ = 0.0f;
                break;
            }
        }
    }
}

void Game131SolarFox::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Perimeter border
    for (int p = 1; p <= 14; ++p) {
        set_pixel(p, 1, 30, 40, 60);
        set_pixel(p, 14, 30, 40, 60);
        set_pixel(1, p, 30, 40, 60);
        set_pixel(14, p, 30, 40, 60);
    }

    // 2. Solar Energy Cells
    for (int y = 0; y < MATRIX_H; ++y) {
        for (int x = 0; x < MATRIX_W; ++x) {
            if (cells_[y][x]) {
                set_pixel(x + 3, y + 3, 255, 220, 40); // Radiant solar yellow
            }
        }
    }

    // 3. Sentinels along perimeter
    // Top
    set_pixel((int)std::round(sentinels_[0].pos), 1, 255, 60, 40);
    // Bottom
    set_pixel((int)std::round(sentinels_[1].pos), 14, 255, 60, 40);
    // Left
    set_pixel(1, (int)std::round(sentinels_[2].pos), 255, 60, 40);
    // Right
    set_pixel(14, (int)std::round(sentinels_[3].pos), 255, 60, 40);

    // 4. Fireballs
    for (int i = 0; i < MAX_FIREBALLS; ++i) {
        if (!fireballs_[i].active) continue;
        int fx = (int)std::round(fireballs_[i].x);
        int fy = (int)std::round(fireballs_[i].y);
        set_pixel(fx, fy, 255, 140, 0); // Orange fireball
    }

    // 5. Player Ship
    int px_s = (int)std::round(px_);
    int py_s = (int)std::round(py_);
    if (state_ == STATE_FLYING || state_ == STATE_QUADRANT_CLEAR) {
        if (shield_timer_ > 0.0f) {
            set_pixel(px_s, py_s, 255, 255, 255);
            set_pixel(px_s - dir_x_, py_s - dir_y_, 0, 255, 200); // Shield cyan glow
        } else if (is_hyperspeed_) {
            set_pixel(px_s, py_s, 255, 255, 255);
            set_pixel(px_s - dir_x_, py_s - dir_y_, 255, 120, 0); // Hyperspeed flame
        } else {
            set_pixel(px_s, py_s, 0, 220, 255); // Cyan body
            set_pixel(px_s - dir_x_, py_s - dir_y_, 0, 120, 180);
        }
    } else if (state_ == STATE_SHIP_EXPLODING) {
        set_pixel(px_s, py_s, 255, 220, 40);
        set_pixel(px_s - 1, py_s, 255, 50, 20);
        set_pixel(px_s + 1, py_s, 255, 50, 20);
        set_pixel(px_s, py_s - 1, 255, 50, 20);
        set_pixel(px_s, py_s + 1, 255, 50, 20);
    }

    // 6. Lives
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l * 2, 0, 0, 220, 255);
    }
}

} // namespace arcade
