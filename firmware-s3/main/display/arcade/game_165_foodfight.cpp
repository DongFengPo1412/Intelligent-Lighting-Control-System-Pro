#include "game_165_foodfight.h"
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

Game165FoodFight::Game165FoodFight() {
    Reset();
}

void Game165FoodFight::Init() {
    Reset();
}

void Game165FoodFight::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game165FoodFight::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 2.0f;
    py_ = 8.0f;
    facing_dx_ = 1.0f;
    facing_dy_ = 0.0f;
    speed_ = 5.2f;
    food_ammo_ = 0;
    fire_cooldown_ = 0.0f;

    cone_x_ = 14.0f;
    cone_y_ = 8.0f;
    melt_timer_ = std::max(8.0f, 16.0f - static_cast<float>(level_));

    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        projectiles_[i].active = false;
    }

    food_piles_[0] = {6.0f, 4.0f, 8};
    food_piles_[1] = {6.0f, 12.0f, 8};
    food_piles_[2] = {10.0f, 4.0f, 8};
    food_piles_[3] = {10.0f, 12.0f, 8};

    chefs_[0] = {0, 4.0f, 4.0f, 1.8f + level_ * 0.2f, 0.0f, 2.0f};
    chefs_[1] = {1, 11.0f, 4.0f, 2.0f + level_ * 0.2f, 0.0f, 3.0f};
    chefs_[2] = {2, 11.0f, 11.0f, 2.2f + level_ * 0.2f, 0.0f, 2.5f};
}

void Game165FoodFight::ThrowFood() {
    if (food_ammo_ == 0 || fire_cooldown_ > 0.0f || state_ != STATE_PLAYING) return;

    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projectiles_[i].active) {
            food_ammo_--;
            projectiles_[i].x = px_ + facing_dx_ * 0.8f;
            projectiles_[i].y = py_ + facing_dy_ * 0.8f;
            projectiles_[i].vx = facing_dx_ * 14.0f;
            projectiles_[i].vy = facing_dy_ * 14.0f;
            projectiles_[i].is_player = true;
            projectiles_[i].active = true;
            fire_cooldown_ = 0.2f;
            break;
        }
    }
}

void Game165FoodFight::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            level_++;
            InitLevel();
        }
        return;
    }

    if (state_ == STATE_CHARLEY_SPLAT) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 2.0f;
                py_ = 8.0f;
                food_ammo_ = 0;
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

    if (fire_cooldown_ > 0.0f) fire_cooldown_ -= dt;

    melt_timer_ -= dt;
    if (melt_timer_ <= 0.0f) {
        lives_--;
        state_ = STATE_CHARLEY_SPLAT;
        state_timer_ = 1.2f;
        return;
    }

    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT) {
        dx -= 1.0f; facing_dx_ = -1.0f; facing_dy_ = 0.0f;
    } else if (buttons & BTN_RIGHT) {
        dx += 1.0f; facing_dx_ = 1.0f; facing_dy_ = 0.0f;
    } else if (buttons & BTN_UP) {
        dy -= 1.0f; facing_dx_ = 0.0f; facing_dy_ = -1.0f;
    } else if (buttons & BTN_DOWN) {
        dy += 1.0f; facing_dx_ = 0.0f; facing_dy_ = 1.0f;
    }

    if (dx != 0.0f || dy != 0.0f) {
        px_ += dx * speed_ * dt;
        py_ += dy * speed_ * dt;
    }

    px_ = std::max(1.0f, std::min(14.5f, px_));
    py_ = std::max(1.0f, std::min(14.5f, py_));

    // Eat ice cream cone!
    if (std::hypot(cone_x_ - px_, cone_y_ - py_) < 1.0f) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 2.0f;
        score_ += static_cast<uint32_t>(melt_timer_ * 100.0f) + 1000;
        return;
    }

    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        ThrowFood();
    }

    // Food piles reload
    for (int i = 0; i < NUM_FOOD_PILES; ++i) {
        if (food_piles_[i].remaining > 0 && std::hypot(food_piles_[i].x - px_, food_piles_[i].y - py_) < 1.0f) {
            if (food_ammo_ < 4) {
                uint8_t take = std::min(static_cast<uint8_t>(4 - food_ammo_), food_piles_[i].remaining);
                food_ammo_ += take;
                food_piles_[i].remaining -= take;
                score_ += 25 * take;
            }
        }
    }

    // Projectiles
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projectiles_[i].active) continue;

        projectiles_[i].x += projectiles_[i].vx * dt;
        projectiles_[i].y += projectiles_[i].vy * dt;

        if (projectiles_[i].x < 0.0f || projectiles_[i].x > 15.0f ||
            projectiles_[i].y < 0.0f || projectiles_[i].y > 15.0f) {
            projectiles_[i].active = false;
            continue;
        }

        if (projectiles_[i].is_player) {
            for (int c = 0; c < NUM_CHEFS; ++c) {
                if (chefs_[c].stunned_timer <= 0.0f &&
                    std::hypot(chefs_[c].x - projectiles_[i].x, chefs_[c].y - projectiles_[i].y) < 1.0f) {
                    chefs_[c].stunned_timer = 3.0f;
                    score_ += 200;
                    projectiles_[i].active = false;
                    break;
                }
            }
        } else {
            if (std::hypot(px_ - projectiles_[i].x, py_ - projectiles_[i].y) < 0.8f) {
                projectiles_[i].active = false;
                lives_--;
                state_ = STATE_CHARLEY_SPLAT;
                state_timer_ = 1.0f;
                return;
            }
        }
    }

    // Chefs
    for (int c = 0; c < NUM_CHEFS; ++c) {
        if (chefs_[c].stunned_timer > 0.0f) {
            chefs_[c].stunned_timer -= dt;
            continue;
        }

        float cdx = px_ - chefs_[c].x;
        float cdy = py_ - chefs_[c].y;
        float dist = std::hypot(cdx, cdy);
        if (dist > 0.2f) {
            chefs_[c].x += (cdx / dist) * chefs_[c].speed * dt;
            chefs_[c].y += (cdy / dist) * chefs_[c].speed * dt;
        }

        chefs_[c].throw_timer -= dt;
        if (chefs_[c].throw_timer <= 0.0f && dist < 8.0f) {
            for (int p = 0; p < MAX_PROJECTILES; ++p) {
                if (!projectiles_[p].active) {
                    projectiles_[p] = {chefs_[c].x, chefs_[c].y, (cdx / dist) * 8.0f, (cdy / dist) * 8.0f, false, true};
                    chefs_[c].throw_timer = 3.0f;
                    break;
                }
            }
        }

        if (std::hypot(chefs_[c].x - px_, chefs_[c].y - py_) < 0.8f) {
            lives_--;
            state_ = STATE_CHARLEY_SPLAT;
            state_timer_ = 1.0f;
            return;
        }
    }
}

void Game165FoodFight::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Manholes
    static const int manholes[4][2] = {{4, 4}, {4, 11}, {11, 4}, {11, 11}};
    for (int i = 0; i < 4; ++i) {
        set_pixel(manholes[i][0], manholes[i][1], 60, 60, 60);
    }

    // Food piles
    for (int i = 0; i < NUM_FOOD_PILES; ++i) {
        if (food_piles_[i].remaining > 0) {
            int fx = static_cast<int>(std::round(food_piles_[i].x));
            int fy = static_cast<int>(std::round(food_piles_[i].y));
            set_pixel(fx, fy, 255, 230, 150);
        }
    }

    // Ice cream cone
    int cx = static_cast<int>(std::round(cone_x_));
    int cy = static_cast<int>(std::round(cone_y_));
    set_pixel(cx, cy, 255, 255, 255);
    set_pixel(cx + 1, cy, 180, 110, 40);

    // Chefs
    for (int c = 0; c < NUM_CHEFS; ++c) {
        int chx = static_cast<int>(std::round(chefs_[c].x));
        int chy = static_cast<int>(std::round(chefs_[c].y));
        if (chefs_[c].stunned_timer > 0.0f) {
            set_pixel(chx, chy, 255, 200, 50);
        } else {
            set_pixel(chx, chy, 220, 60, 40);
            set_pixel(chx, chy - 1, 240, 240, 240);
        }
    }

    // Projectiles
    for (int p = 0; p < MAX_PROJECTILES; ++p) {
        if (projectiles_[p].active) {
            int px = static_cast<int>(std::round(projectiles_[p].x));
            int py = static_cast<int>(std::round(projectiles_[p].y));
            if (projectiles_[p].is_player) {
                set_pixel(px, py, 255, 255, 200);
            } else {
                set_pixel(px, py, 255, 100, 50);
            }
        }
    }

    // Charley Chuck
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 40, 120, 255);
        set_pixel(px, py - 1, 255, 200, 160);
    } else if (state_ == STATE_CHARLEY_SPLAT) {
        set_pixel(px, py, 255, 120, 0);
    }

    // Ammo dots
    for (int i = 0; i < food_ammo_; ++i) {
        set_pixel(i, 0, 255, 230, 100);
    }
}

} // namespace arcade

