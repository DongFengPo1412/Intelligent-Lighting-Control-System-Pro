#include "game_179_gauntlet.h"
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

Game179Gauntlet::Game179Gauntlet() {
    Reset();
}

void Game179Gauntlet::Init() {
    Reset();
}

void Game179Gauntlet::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    health_ = 500.0f;
    InitStage();
}

void Game179Gauntlet::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 2.0f;
    py_ = 2.0f;
    facing_x_ = 1.0f;
    facing_y_ = 0.0f;
    speed_ = 5.5f;
    keys_count_ = 1;
    potions_count_ = 1;
    health_ = std::max(400.0f, health_);

    std::memset(grid_, 0, sizeof(grid_));
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                grid_[y][x] = 1;
            }
        }
    }

    for (int y = 1; y <= 9; ++y) grid_[y][5] = 1;
    for (int x = 5; x <= 11; ++x) grid_[9][x] = 1;
    for (int y = 6; y <= 14; ++y) grid_[y][11] = 1;

    grid_[5][5] = 2; // Locked door
    grid_[13][13] = 3; // Exit stairs

    for (int i = 0; i < MAX_AXES; ++i) axes_[i].active = false;

    pickups_[0] = {2, 8, 0, true}; // food
    pickups_[1] = {8, 2, 0, true}; // food
    pickups_[2] = {8, 7, 1, true}; // key
    pickups_[3] = {13, 3, 2, true}; // potion
    pickups_[4] = {7, 13, 0, true}; // food
    for (int i = 5; i < MAX_PICKUPS; ++i) pickups_[i].active = false;

    generators_[0] = {8, 4, 3, 1.5f};
    generators_[1] = {13, 7, 3, 2.0f};
    generators_[2] = {4, 12, 3, 1.8f};
    generators_[3] = {0, 0, 0, 0.0f};

    monsters_[0] = {7.0f, 4.0f, 2.0f + stage_ * 0.2f, true};
    monsters_[1] = {13.0f, 5.0f, 2.0f + stage_ * 0.2f, true};
    for (int i = 2; i < MAX_MONSTERS; ++i) monsters_[i].alive = false;
}

void Game179Gauntlet::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_WARRIOR_DIED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 2.0f;
                py_ = 2.0f;
                health_ = 500.0f;
                for (int i = 0; i < MAX_AXES; ++i) axes_[i].active = false;
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

    // Health decay
    health_ -= 12.0f * dt;
    if (health_ <= 0.0f) {
        health_ = 0.0f;
        lives_--;
        state_ = STATE_WARRIOR_DIED;
        state_timer_ = 1.2f;
        return;
    }

    // Movement
    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT)  { dx -= 1.0f; facing_x_ = -1.0f; facing_y_ = 0.0f; }
    if (buttons & BTN_RIGHT) { dx += 1.0f; facing_x_ = 1.0f;  facing_y_ = 0.0f; }
    if (buttons & BTN_UP)    { dy -= 1.0f; facing_x_ = 0.0f;  facing_y_ = -1.0f; }
    if (buttons & BTN_DOWN)  { dy += 1.0f; facing_x_ = 0.0f;  facing_y_ = 1.0f; }

    if (dx != 0.0f || dy != 0.0f) {
        float new_px = px_ + dx * speed_ * dt;
        float new_py = py_ + dy * speed_ * dt;

        int cx = static_cast<int>(std::round(new_px));
        int cy = static_cast<int>(std::round(new_py));
        if (cx >= 0 && cx < 16 && cy >= 0 && cy < 16) {
            uint8_t cell = grid_[cy][cx];
            if (cell == 1) {
                // Wall
            } else if (cell == 2) {
                if (keys_count_ > 0) {
                    keys_count_--;
                    grid_[cy][cx] = 0;
                    score_ += 100;
                    px_ = new_px; py_ = new_py;
                }
            } else if (cell == 3) {
                state_ = STATE_STAGE_CLEAR;
                state_timer_ = 2.0f;
                score_ += 2500;
                return;
            } else {
                px_ = new_px; py_ = new_py;
            }
        }
    }

    // Pickups
    for (int i = 0; i < MAX_PICKUPS; ++i) {
        if (!pickups_[i].active) continue;
        if (std::hypot(pickups_[i].x - px_, pickups_[i].y - py_) < 0.8f) {
            pickups_[i].active = false;
            if (pickups_[i].type == 0) {
                health_ = std::min(1000.0f, health_ + 150.0f);
                score_ += 100;
            } else if (pickups_[i].type == 1) {
                keys_count_++;
                score_ += 100;
            } else if (pickups_[i].type == 2) {
                potions_count_++;
                score_ += 200;
            }
        }
    }

    // Throw axe (Btn A)
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        for (int i = 0; i < MAX_AXES; ++i) {
            if (!axes_[i].active) {
                axes_[i] = {px_, py_, facing_x_ * 12.0f, facing_y_ * 12.0f, true};
                break;
            }
        }
    }

    // Cast potion (Btn B)
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B) && potions_count_ > 0) {
        potions_count_--;
        for (int i = 0; i < MAX_MONSTERS; ++i) {
            if (monsters_[i].alive) {
                monsters_[i].alive = false;
                score_ += 150;
            }
        }
    }

    // Axes
    for (int i = 0; i < MAX_AXES; ++i) {
        if (!axes_[i].active) continue;
        axes_[i].x += axes_[i].vx * dt;
        axes_[i].y += axes_[i].vy * dt;

        int ax = static_cast<int>(std::round(axes_[i].x));
        int ay = static_cast<int>(std::round(axes_[i].y));
        if (ax < 1 || ax >= 15 || ay < 1 || ay >= 15 || grid_[ay][ax] == 1 || grid_[ay][ax] == 2) {
            axes_[i].active = false;
            continue;
        }

        for (int m = 0; m < MAX_MONSTERS; ++m) {
            if (monsters_[m].alive && std::hypot(monsters_[m].x - axes_[i].x, monsters_[m].y - axes_[i].y) < 0.9f) {
                monsters_[m].alive = false;
                axes_[i].active = false;
                score_ += 100;
                break;
            }
        }

        if (axes_[i].active) {
            for (int g = 0; g < MAX_GENERATORS; ++g) {
                if (generators_[g].hp > 0 && std::hypot(generators_[g].x - axes_[i].x, generators_[g].y - axes_[i].y) < 0.9f) {
                    generators_[g].hp--;
                    axes_[i].active = false;
                    score_ += 150;
                    if (generators_[g].hp <= 0) score_ += 500;
                    break;
                }
            }
        }
    }

    // Generators
    for (int g = 0; g < MAX_GENERATORS; ++g) {
        if (generators_[g].hp <= 0) continue;
        generators_[g].timer -= dt;
        if (generators_[g].timer <= 0.0f) {
            generators_[g].timer = 3.0f;
            for (int m = 0; m < MAX_MONSTERS; ++m) {
                if (!monsters_[m].alive) {
                    monsters_[m] = {static_cast<float>(generators_[g].x),
                                    static_cast<float>(generators_[g].y + 0.5f),
                                    2.0f + stage_ * 0.2f, true};
                    break;
                }
            }
        }
    }

    // Monsters AI
    for (int m = 0; m < MAX_MONSTERS; ++m) {
        if (!monsters_[m].alive) continue;
        float mdx = px_ - monsters_[m].x;
        float mdy = py_ - monsters_[m].y;
        float dist = std::hypot(mdx, mdy);
        if (dist > 0.1f) {
            monsters_[m].x += (mdx / dist) * monsters_[m].speed * dt;
            monsters_[m].y += (mdy / dist) * monsters_[m].speed * dt;
        }

        if (std::hypot(monsters_[m].x - px_, monsters_[m].y - py_) < 0.8f) {
            health_ -= 50.0f * dt;
            if (health_ <= 0.0f) {
                health_ = 0.0f;
                lives_--;
                state_ = STATE_WARRIOR_DIED;
                state_timer_ = 1.2f;
                return;
            }
        }
    }
}

void Game179Gauntlet::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Walls & Doors
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (grid_[y][x] == 1) set_pixel(x, y, 60, 60, 80);
            else if (grid_[y][x] == 2) set_pixel(x, y, 200, 160, 40);
            else if (grid_[y][x] == 3) set_pixel(x, y, 60, 240, 255);
        }
    }

    // Pickups
    for (int i = 0; i < MAX_PICKUPS; ++i) {
        if (!pickups_[i].active) continue;
        int px = pickups_[i].x;
        int py = pickups_[i].y;
        if (pickups_[i].type == 0) set_pixel(px, py, 240, 100, 40);
        else if (pickups_[i].type == 1) set_pixel(px, py, 255, 220, 0);
        else if (pickups_[i].type == 2) set_pixel(px, py, 180, 40, 240);
    }

    // Generators
    for (int g = 0; g < MAX_GENERATORS; ++g) {
        if (generators_[g].hp > 0) {
            set_pixel(generators_[g].x, generators_[g].y, 140, 20, 20);
            set_pixel(generators_[g].x, generators_[g].y - 1, 200, 40, 40);
        }
    }

    // Monsters
    for (int m = 0; m < MAX_MONSTERS; ++m) {
        if (monsters_[m].alive) {
            set_pixel(static_cast<int>(std::round(monsters_[m].x)),
                      static_cast<int>(std::round(monsters_[m].y)),
                      40, 220, 60);
        }
    }

    // Axes
    for (int i = 0; i < MAX_AXES; ++i) {
        if (axes_[i].active) {
            set_pixel(static_cast<int>(std::round(axes_[i].x)),
                      static_cast<int>(std::round(axes_[i].y)),
                      255, 255, 200);
        }
    }

    // Warrior
    int wx = static_cast<int>(std::round(px_));
    int wy = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(wx, wy, 240, 40, 40);
        set_pixel(wx, wy - 1, 255, 220, 140);
        set_pixel(wx + static_cast<int>(facing_x_), wy + static_cast<int>(facing_y_), 200, 200, 220);
    } else if (state_ == STATE_WARRIOR_DIED) {
        set_pixel(wx, wy, 255, 100, 0);
    }
}

} // namespace arcade
