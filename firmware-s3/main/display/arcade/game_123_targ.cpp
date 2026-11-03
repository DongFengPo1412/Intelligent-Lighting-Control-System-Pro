#include "game_123_targ.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace arcade {

static constexpr float STREETS[5] = {1.5f, 4.5f, 7.5f, 10.5f, 13.5f};
static constexpr float GRID_MIN = 1.5f;
static constexpr float GRID_MAX = 13.5f;

Game123Targ::Game123Targ() {
    Init();
}

void Game123Targ::Init() {
    score_ = 0;
    lives_ = 3;
    sector_ = 1;
    InitSector();
}

void Game123Targ::Reset() {
    Init();
}

void Game123Targ::InitSector() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    enemies_remaining_ = 10;
    spawn_timer_ = 0.5f;

    px_ = 7.5f;
    py_ = 13.5f;
    p_dir_x_ = 0;
    p_dir_y_ = -1;
    next_dir_x_ = 0;
    next_dir_y_ = -1;
    turbo_timer_ = 0.0f;
    turbo_cooldown_ = 0.0f;

    laser_.active = false;
    laser_.x = 0.0f;
    laser_.y = 0.0f;
    laser_.dir_x = 0;
    laser_.dir_y = 0;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = false;
        enemies_[i].is_spectar = false;
        enemies_[i].x = 0.0f;
        enemies_[i].y = 0.0f;
        enemies_[i].dir_x = 0;
        enemies_[i].dir_y = 0;
    }
}

bool Game123Targ::IsIntersection(float x, float y, float tol) {
    bool near_x = false;
    bool near_y = false;
    for (float s : STREETS) {
        if (std::abs(x - s) <= tol) near_x = true;
        if (std::abs(y - s) <= tol) near_y = true;
    }
    return near_x && near_y;
}

void Game123Targ::SpawnEnemy() {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) {
            // Spawn at one of the top intersections
            int corner = rand() % 5;
            enemies_[i].x = STREETS[corner];
            enemies_[i].y = GRID_MIN;
            enemies_[i].dir_x = (rand() % 2 == 0) ? 1 : -1;
            enemies_[i].dir_y = 1;
            // 20% chance of spawning as a fast Spectar, or guaranteed if fewer than 3 enemies remain
            enemies_[i].is_spectar = (enemies_remaining_ <= 3) || (rand() % 5 == 0);
            enemies_[i].active = true;
            break;
        }
    }
}

void Game123Targ::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & 0x0030) && !(prev_buttons & 0x0030)) { // KEY_A or KEY_B
            Reset();
        }
        return;
    }

    if (state_ == STATE_DYING) {
        if (state_timer_ > 1.2f) {
            lives_--;
            if (lives_ == 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                py_ = 13.5f;
                p_dir_x_ = 0;
                p_dir_y_ = -1;
                next_dir_x_ = 0;
                next_dir_y_ = -1;
                laser_.active = false;
            }
        }
        return;
    }

    if (state_ == STATE_SECTOR_CLEAR) {
        if (state_timer_ > 1.5f) {
            sector_++;
            score_ += 1500;
            InitSector();
        }
        return;
    }

    // Controls
    // KEY_A: Fire laser
    if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) {
        if (!laser_.active) {
            laser_.active = true;
            laser_.x = px_ + p_dir_x_ * 0.8f;
            laser_.y = py_ + p_dir_y_ * 0.8f;
            laser_.dir_x = p_dir_x_;
            laser_.dir_y = p_dir_y_;
        }
    }

    // KEY_B: Turbo boost
    if (turbo_cooldown_ > 0.0f) turbo_cooldown_ -= dt;
    if ((buttons & 0x0020) && !(prev_buttons & 0x0020)) {
        if (turbo_cooldown_ <= 0.0f) {
            turbo_timer_ = 0.8f;
            turbo_cooldown_ = 2.5f;
        }
    }
    if (turbo_timer_ > 0.0f) turbo_timer_ -= dt;

    UpdatePlayer(dt, buttons);
    UpdateLaser(dt);
    UpdateEnemies(dt);
    CheckCollisions();

    // Check sector complete
    if (enemies_remaining_ == 0) {
        bool any_enemy_alive = false;
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (enemies_[i].active) {
                any_enemy_alive = true;
                break;
            }
        }
        if (!any_enemy_alive) {
            state_ = STATE_SECTOR_CLEAR;
            state_timer_ = 0.0f;
        }
    }
}

void Game123Targ::UpdatePlayer(float dt, uint16_t buttons) {
    if (buttons & 0x0001) { next_dir_x_ = 0; next_dir_y_ = -1; } // UP
    if (buttons & 0x0002) { next_dir_x_ = 0; next_dir_y_ = 1; }  // DOWN
    if (buttons & 0x0004) { next_dir_x_ = -1; next_dir_y_ = 0; } // LEFT
    if (buttons & 0x0008) { next_dir_x_ = 1; next_dir_y_ = 0; }  // RIGHT

    // Speed calculation
    float speed = (turbo_timer_ > 0.0f) ? 10.0f : 5.5f;

    // Check if player can turn at intersection
    if (next_dir_x_ != p_dir_x_ || next_dir_y_ != p_dir_y_) {
        // Can always reverse
        if (next_dir_x_ == -p_dir_x_ && next_dir_y_ == -p_dir_y_) {
            p_dir_x_ = next_dir_x_;
            p_dir_y_ = next_dir_y_;
        } else {
            // Turning 90 degrees requires being near a grid intersection
            for (float s : STREETS) {
                if (next_dir_x_ != 0 && std::abs(py_ - s) < 0.35f) {
                    py_ = s;
                    p_dir_x_ = next_dir_x_;
                    p_dir_y_ = next_dir_y_;
                    break;
                }
                if (next_dir_y_ != 0 && std::abs(px_ - s) < 0.35f) {
                    px_ = s;
                    p_dir_x_ = next_dir_x_;
                    p_dir_y_ = next_dir_y_;
                    break;
                }
            }
        }
    }

    px_ += p_dir_x_ * speed * dt;
    py_ += p_dir_y_ * speed * dt;

    // Boundary clamp
    if (px_ < GRID_MIN) { px_ = GRID_MIN; p_dir_x_ = 0; }
    if (px_ > GRID_MAX) { px_ = GRID_MAX; p_dir_x_ = 0; }
    if (py_ < GRID_MIN) { py_ = GRID_MIN; p_dir_y_ = 0; }
    if (py_ > GRID_MAX) { py_ = GRID_MAX; p_dir_y_ = 0; }
}

void Game123Targ::UpdateLaser(float dt) {
    if (!laser_.active) return;
    float laser_speed = 28.0f;
    laser_.x += laser_.dir_x * laser_speed * dt;
    laser_.y += laser_.dir_y * laser_speed * dt;

    if (laser_.x < GRID_MIN - 0.5f || laser_.x > GRID_MAX + 0.5f ||
        laser_.y < GRID_MIN - 0.5f || laser_.y > GRID_MAX + 0.5f) {
        laser_.active = false;
    }
}

void Game123Targ::UpdateEnemies(float dt) {
    spawn_timer_ -= dt;
    if (spawn_timer_ <= 0.0f && enemies_remaining_ > 0) {
        spawn_timer_ = 1.8f - sector_ * 0.1f;
        if (spawn_timer_ < 0.8f) spawn_timer_ = 0.8f;
        SpawnEnemy();
    }

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        float base_speed = enemies_[i].is_spectar ? (6.0f + sector_ * 0.4f) : (4.0f + sector_ * 0.25f);
        enemies_[i].x += enemies_[i].dir_x * base_speed * dt;
        enemies_[i].y += enemies_[i].dir_y * base_speed * dt;

        // Check if reached intersection
        for (float sx : STREETS) {
            for (float sy : STREETS) {
                if (std::abs(enemies_[i].x - sx) < 0.25f && std::abs(enemies_[i].y - sy) < 0.25f) {
                    enemies_[i].x = sx;
                    enemies_[i].y = sy;

                    // AI decision
                    if (enemies_[i].is_spectar) {
                        // Spectar tracks player
                        float dx = px_ - enemies_[i].x;
                        float dy = py_ - enemies_[i].y;
                        if (std::abs(dx) > std::abs(dy)) {
                            enemies_[i].dir_x = (dx > 0) ? 1 : -1;
                            enemies_[i].dir_y = 0;
                        } else {
                            enemies_[i].dir_x = 0;
                            enemies_[i].dir_y = (dy > 0) ? 1 : -1;
                        }
                    } else {
                        // Regular smuggler chooses random available direction
                        if (rand() % 2 == 0) {
                            int r = rand() % 4;
                            if (r == 0) { enemies_[i].dir_x = 0; enemies_[i].dir_y = -1; }
                            else if (r == 1) { enemies_[i].dir_x = 0; enemies_[i].dir_y = 1; }
                            else if (r == 2) { enemies_[i].dir_x = -1; enemies_[i].dir_y = 0; }
                            else { enemies_[i].dir_x = 1; enemies_[i].dir_y = 0; }
                        }
                    }
                }
            }
        }

        // Clamp & bounce on boundary
        if (enemies_[i].x <= GRID_MIN) { enemies_[i].x = GRID_MIN; enemies_[i].dir_x = 1; }
        if (enemies_[i].x >= GRID_MAX) { enemies_[i].x = GRID_MAX; enemies_[i].dir_x = -1; }
        if (enemies_[i].y <= GRID_MIN) { enemies_[i].y = GRID_MIN; enemies_[i].dir_y = 1; }
        if (enemies_[i].y >= GRID_MAX) { enemies_[i].y = GRID_MAX; enemies_[i].dir_y = -1; }
    }
}

void Game123Targ::CheckCollisions() {
    // 1. Laser vs Enemies
    if (laser_.active) {
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (!enemies_[i].active) continue;

            float dx = std::abs(laser_.x - enemies_[i].x);
            float dy = std::abs(laser_.y - enemies_[i].y);
            if (dx < 0.9f && dy < 0.9f) {
                laser_.active = false;
                enemies_[i].active = false;
                if (enemies_remaining_ > 0) enemies_remaining_--;

                if (enemies_[i].is_spectar) {
                    score_ += 500; // Big bonus for Spectar boss
                } else {
                    score_ += 100;
                }
                break;
            }
        }
    }

    // 2. Enemies vs Player
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        float dx = std::abs(px_ - enemies_[i].x);
        float dy = std::abs(py_ - enemies_[i].y);
        if (dx < 0.75f && dy < 0.75f) {
            state_ = STATE_DYING;
            state_timer_ = 0.0f;
            break;
        }
    }
}

void Game123Targ::Render(uint8_t* fb) {
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

    // 1. Draw 4x4 city blocks (obstacles between streets)
    for (int by = 0; by < 4; ++by) {
        for (int bx = 0; bx < 4; ++bx) {
            int x1 = (int)STREETS[bx] + 1;
            int x2 = (int)STREETS[bx + 1] - 1;
            int y1 = (int)STREETS[by] + 1;
            int y2 = (int)STREETS[by + 1] - 1;
            for (int cy = y1; cy <= y2; ++cy) {
                for (int cx = x1; cx <= x2; ++cx) {
                    set_pixel(cx, cy, 15, 25, 45); // Dark blue-grey building block
                }
            }
        }
    }

    // 2. Draw streets
    for (float s : STREETS) {
        int is = (int)std::round(s);
        for (int p = 0; p < 16; ++p) {
            // Street intersection markers
            set_pixel(is, p, 30, 35, 55);
            set_pixel(p, is, 30, 35, 55);
        }
    }

    // 3. Draw enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = (int)std::round(enemies_[i].x);
        int ey = (int)std::round(enemies_[i].y);
        if (enemies_[i].is_spectar) {
            // Flashing bright yellow Spectar boss car
            bool flash = ((int)(state_timer_ * 10.0f) % 2) == 0;
            if (flash) {
                set_pixel(ex, ey, 255, 255, 0);
            } else {
                set_pixel(ex, ey, 255, 140, 0);
            }
        } else {
            // Magenta / red smuggler car
            set_pixel(ex, ey, 255, 40, 70);
        }
    }

    // 4. Draw laser beam
    if (laser_.active) {
        int lx = (int)std::round(laser_.x);
        int ly = (int)std::round(laser_.y);
        set_pixel(lx, ly, 80, 255, 100);
        set_pixel(lx - laser_.dir_x, ly - laser_.dir_y, 40, 200, 60);
    }

    // 5. Draw Player
    int px_screen = (int)std::round(px_);
    int py_screen = (int)std::round(py_);
    if (state_ == STATE_PLAYING || state_ == STATE_SECTOR_CLEAR) {
        if (turbo_timer_ > 0.0f) {
            // Turbo cyan-white glow
            set_pixel(px_screen, py_screen, 255, 255, 255);
            set_pixel(px_screen - p_dir_x_, py_screen - p_dir_y_, 0, 220, 255);
        } else {
            set_pixel(px_screen, py_screen, 0, 230, 255);
            set_pixel(px_screen - p_dir_x_, py_screen - p_dir_y_, 0, 120, 180);
        }
    } else if (state_ == STATE_DYING) {
        // Explosion flash
        set_pixel(px_screen, py_screen, 255, 220, 50);
        set_pixel(px_screen - 1, py_screen, 255, 60, 20);
        set_pixel(px_screen + 1, py_screen, 255, 60, 20);
        set_pixel(px_screen, py_screen - 1, 255, 60, 20);
        set_pixel(px_screen, py_screen + 1, 255, 60, 20);
    }

    // 6. HUD / Lives indicators at bottom corners
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l * 2, 0, 0, 230, 255);
    }
    // Remaining enemies pip bar
    for (int rem = 0; rem < enemies_remaining_ && rem < 5; ++rem) {
        set_pixel(15 - rem * 2, 0, 255, 40, 70);
    }
}

} // namespace arcade
