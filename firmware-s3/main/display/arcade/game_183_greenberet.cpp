#include "game_183_greenberet.h"
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

Game183GreenBeret::Game183GreenBeret() {
    Reset();
}

void Game183GreenBeret::Init() {
    Reset();
}

void Game183GreenBeret::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game183GreenBeret::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 3.0f;
    py_ = 13.0f;
    facing_ = 1;
    speed_ = 6.0f;
    is_prone_ = false;
    knife_timer_ = 0.0f;
    rpg_ammo_ = 1;
    distance_ = 0.0f;
    target_distance_ = 160.0f + stage_ * 40.0f;
    silo_hp_ = 3 + stage_;

    for (int i = 0; i < MAX_ROCKETS; ++i) rockets_[i].active = false;
    SpawnEnemyWave();
}

void Game183GreenBeret::SpawnEnemyWave() {
    enemies_[0] = {14.0f, 13.0f, -3.5f, false, true};
    enemies_[1] = {19.0f, 13.0f, -4.0f, true, true};
    enemies_[2] = {24.0f, 13.0f, -3.2f, false, true};
    enemies_[3] = {0.0f, 0.0f, 0.0f, false, false};

    paratroopers_[0] = {9.0f, 1.0f, 2.0f, true};
    paratroopers_[1] = {0.0f, 0.0f, 0.0f, false};
}

void Game183GreenBeret::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_SOLDIER_KILLED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 3.0f;
                is_prone_ = false;
                knife_timer_ = 0.0f;
                for (int i = 0; i < MAX_ROCKETS; ++i) rockets_[i].active = false;
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

    is_prone_ = (buttons & BTN_DOWN) != 0;

    float dx = 0.0f;
    if (!is_prone_) {
        if (buttons & BTN_LEFT)  { dx -= 1.0f; facing_ = -1; }
        if (buttons & BTN_RIGHT) { dx += 1.0f; facing_ = 1; }
    }

    px_ += dx * speed_ * dt;
    if (distance_ < target_distance_ && px_ > 8.0f) {
        float scroll = px_ - 8.0f;
        px_ = 8.0f;
        distance_ += scroll;
        for (int i = 0; i < MAX_ENEMIES; ++i) enemies_[i].x -= scroll;
        for (int i = 0; i < MAX_PARATROOPERS; ++i) paratroopers_[i].x -= scroll;
    }
    px_ = std::max(1.0f, std::min(14.0f, px_));

    if (knife_timer_ > 0.0f) knife_timer_ -= dt;

    // Knife thrust (Button A)
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        knife_timer_ = 0.2f;
        float kx = px_ + facing_ * 1.2f;
        float ky = is_prone_ ? (py_ + 0.5f) : py_;

        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (enemies_[i].alive && std::hypot(enemies_[i].x - kx, enemies_[i].y - ky) < 1.3f) {
                enemies_[i].alive = false;
                score_ += 100;
                if (enemies_[i].is_officer) {
                    rpg_ammo_ = std::min(3, rpg_ammo_ + 3);
                    score_ += 400;
                }
            }
        }

        for (int i = 0; i < MAX_PARATROOPERS; ++i) {
            if (paratroopers_[i].alive && std::hypot(paratroopers_[i].x - kx, paratroopers_[i].y - ky) < 1.3f) {
                paratroopers_[i].alive = false;
                score_ += 200;
            }
        }

        if (distance_ >= target_distance_ && std::hypot(14.0f - kx, 13.0f - ky) < 1.5f) {
            silo_hp_--;
            score_ += 200;
            if (silo_hp_ <= 0) {
                state_ = STATE_STAGE_CLEAR;
                state_timer_ = 2.0f;
                score_ += 3000;
                return;
            }
        }
    }

    // Fire RPG (Button B)
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B) && rpg_ammo_ > 0) {
        rpg_ammo_--;
        for (int i = 0; i < MAX_ROCKETS; ++i) {
            if (!rockets_[i].active) {
                rockets_[i] = {px_ + facing_ * 1.0f, py_ - 0.2f, facing_ * 14.0f, true};
                break;
            }
        }
    }

    // Rockets
    for (int i = 0; i < MAX_ROCKETS; ++i) {
        if (!rockets_[i].active) continue;
        rockets_[i].x += rockets_[i].vx * dt;
        if (rockets_[i].x < 0.0f || rockets_[i].x > 16.0f) {
            rockets_[i].active = false;
            continue;
        }

        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (enemies_[e].alive && std::hypot(enemies_[e].x - rockets_[i].x, enemies_[e].y - rockets_[i].y) < 1.4f) {
                enemies_[e].alive = false;
                score_ += 150;
            }
        }

        if (distance_ >= target_distance_ && std::hypot(14.0f - rockets_[i].x, 13.0f - rockets_[i].y) < 1.5f) {
            rockets_[i].active = false;
            silo_hp_ -= 2;
            score_ += 400;
            if (silo_hp_ <= 0) {
                state_ = STATE_STAGE_CLEAR;
                state_timer_ = 2.0f;
                score_ += 3000;
                return;
            }
        }
    }

    // Enemies AI
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].alive) continue;
        enemies_[i].x += enemies_[i].vx * dt;
        if (std::hypot(enemies_[i].x - px_, enemies_[i].y - py_) < 0.8f) {
            lives_--;
            state_ = STATE_SOLDIER_KILLED;
            state_timer_ = 1.0f;
            return;
        }
    }

    // Paratroopers AI
    for (int i = 0; i < MAX_PARATROOPERS; ++i) {
        if (!paratroopers_[i].alive) continue;
        paratroopers_[i].y += paratroopers_[i].vy * dt;
        if (paratroopers_[i].y >= 13.0f) {
            paratroopers_[i].alive = false;
            for (int e = 0; e < MAX_ENEMIES; ++e) {
                if (!enemies_[e].alive) {
                    enemies_[e] = {paratroopers_[i].x, 13.0f, -3.5f, false, true};
                    break;
                }
            }
        }

        if (std::hypot(paratroopers_[i].x - px_, paratroopers_[i].y - py_) < 0.8f) {
            lives_--;
            state_ = STATE_SOLDIER_KILLED;
            state_timer_ = 1.0f;
            return;
        }
    }

    bool any_enemy_alive = false;
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].alive) { any_enemy_alive = true; break; }
    }
    if (!any_enemy_alive && distance_ < target_distance_) {
        SpawnEnemyWave();
    }
}

void Game183GreenBeret::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Ground
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 14, 50, 50, 60);
        set_pixel(x, 15, 30, 30, 40);
    }

    // Silo
    if (distance_ >= target_distance_) {
        for (int y = 8; y <= 13; ++y) {
            set_pixel(14, y, 220, 220, 230);
            set_pixel(13, y, 160, 40, 40);
            set_pixel(15, y, 160, 40, 40);
        }
    }

    // Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].alive) {
            int ex = static_cast<int>(std::round(enemies_[i].x));
            int ey = static_cast<int>(std::round(enemies_[i].y));
            if (enemies_[i].is_officer) {
                set_pixel(ex, ey, 255, 30, 30);
                set_pixel(ex, ey - 1, 255, 200, 140);
            } else {
                set_pixel(ex, ey, 140, 140, 150);
                set_pixel(ex, ey - 1, 200, 160, 120);
            }
        }
    }

    // Paratroopers
    for (int i = 0; i < MAX_PARATROOPERS; ++i) {
        if (paratroopers_[i].alive) {
            int px = static_cast<int>(std::round(paratroopers_[i].x));
            int py = static_cast<int>(std::round(paratroopers_[i].y));
            set_pixel(px, py, 140, 140, 150);
            set_pixel(px - 1, py - 1, 240, 240, 240);
            set_pixel(px, py - 1, 240, 240, 240);
            set_pixel(px + 1, py - 1, 240, 240, 240);
        }
    }

    // Rockets
    for (int i = 0; i < MAX_ROCKETS; ++i) {
        if (rockets_[i].active) {
            int rx = static_cast<int>(std::round(rockets_[i].x));
            int ry = static_cast<int>(std::round(rockets_[i].y));
            set_pixel(rx, ry, 255, 220, 40);
            set_pixel(rx - facing_, ry, 255, 80, 0);
        }
    }

    // Commando
    int cx = static_cast<int>(std::round(px_));
    int cy = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        if (is_prone_) {
            set_pixel(cx, cy, 40, 140, 40);
            set_pixel(cx + facing_, cy, 255, 200, 140);
            if (knife_timer_ > 0.0f) set_pixel(cx + facing_ * 2, cy, 240, 240, 255);
        } else {
            set_pixel(cx, cy, 30, 120, 40);
            set_pixel(cx, cy - 1, 50, 160, 50);
            set_pixel(cx, cy - 2, 20, 180, 20);
            if (knife_timer_ > 0.0f) set_pixel(cx + facing_, cy - 1, 240, 240, 255);
        }
    } else if (state_ == STATE_SOLDIER_KILLED) {
        set_pixel(cx, cy, 255, 60, 0);
    }
}

} // namespace arcade
