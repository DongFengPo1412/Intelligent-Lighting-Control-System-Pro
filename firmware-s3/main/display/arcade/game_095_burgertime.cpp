#include "game_095_burgertime.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game095BurgerTime::Game095BurgerTime() {
    Init();
}

void Game095BurgerTime::Init() {
    ResetKitchen(true);
}

void Game095BurgerTime::Reset() {
    ResetKitchen(true);
}

void Game095BurgerTime::ResetKitchen(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        stage_ = 1;
        peppers_left_ = 5;
    }
    state_ = STATE_COOKING;
    state_timer_ = 0.0f;
    burgers_completed_ = 0;

    px_ = 4.0f;
    py_ = 13.0f;
    facing_ = 1;
    pepper_spray_timer_ = 0.0f;
    move_cooldown_ = 0.0f;

    // Burger Layers Setup (2 Burgers, 3 layers each)
    // Left Burger (col 0): x = 2 to 5
    layers_[0] = {0, ING_BUN_TOP, 3.0f, 3.0f, false, false, 0};
    layers_[1] = {0, ING_PATTY, 6.0f, 6.0f, false, false, 0};
    layers_[2] = {0, ING_BUN_BOTTOM, 9.0f, 9.0f, false, false, 0};

    // Right Burger (col 1): x = 10 to 13
    layers_[3] = {1, ING_BUN_TOP, 3.0f, 3.0f, false, false, 0};
    layers_[4] = {1, ING_PATTY, 6.0f, 6.0f, false, false, 0};
    layers_[5] = {1, ING_BUN_BOTTOM, 9.0f, 9.0f, false, false, 0};

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = true;
        enemies_[i].stun_timer = 0.0f;
        enemies_[i].respawn_timer = 0.0f;
        enemies_[i].x = (i == 0) ? 1.0f : ((i == 1) ? 14.0f : 8.0f);
        enemies_[i].y = (i == 2) ? 6.0f : 3.0f;
        enemies_[i].vx = (i % 2 == 0) ? 1.4f : -1.4f;
        enemies_[i].vy = 0.0f;
    }
}

void Game095BurgerTime::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_CHEF_HIT) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetKitchen(false);
            }
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.0f) {
            stage_++;
            peppers_left_ = std::min(5, peppers_left_ + 2);
            ResetKitchen(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetKitchen(true);
        }
        return;
    }

    // STATE_COOKING
    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateBurgerLayers(dt);
    UpdateEnemies(dt);
    CheckCollisions();

    // Check all layers on plates
    bool all_finished = true;
    for (int i = 0; i < MAX_LAYERS; ++i) {
        if (!layers_[i].on_plate) {
            all_finished = false;
            break;
        }
    }

    if (all_finished) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1000;
        burgers_completed_ = 2;
    }
}

void Game095BurgerTime::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (pepper_spray_timer_ > 0.0f) {
        pepper_spray_timer_ -= dt;
    }

    // Button A: Pepper Shaker
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        if (peppers_left_ > 0 && pepper_spray_timer_ <= 0.0f) {
            peppers_left_--;
            pepper_spray_timer_ = 0.45f;
            score_ += 10;

            // Stun any enemies in front
            float spray_x = px_ + facing_ * 1.5f;
            for (int i = 0; i < MAX_ENEMIES; ++i) {
                FoodEnemy& e = enemies_[i];
                if (e.active) {
                    float dx = std::fabs(e.x - spray_x);
                    float dy = std::fabs(e.y - py_);
                    if (dx < 1.6f && dy < 1.2f) {
                        e.stun_timer = 4.0f; // Sneeze-stun!
                    }
                }
            }
        }
    }

    // Directional Walkway & Ladder Movement
    float move_speed = 5.0f;
    int cur_floor_y = -1;
    for (int fy : {3, 6, 9, 13}) {
        if (std::fabs(py_ - (float)fy) < 0.35f) {
            cur_floor_y = fy;
            break;
        }
    }

    bool on_ladder = false;
    for (int lx : {1, 4, 8, 11, 14}) {
        if (std::fabs(px_ - (float)lx) < 0.45f) {
            on_ladder = true;
            break;
        }
    }

    if (buttons & BTN_LEFT) {
        if (cur_floor_y != -1) {
            px_ -= move_speed * dt;
            facing_ = -1;
            py_ = (float)cur_floor_y;
        }
    } else if (buttons & BTN_RIGHT) {
        if (cur_floor_y != -1) {
            px_ += move_speed * dt;
            facing_ = 1;
            py_ = (float)cur_floor_y;
        }
    }

    if (buttons & BTN_UP) {
        if (on_ladder) {
            py_ -= move_speed * dt;
        }
    } else if (buttons & BTN_DOWN) {
        if (on_ladder) {
            py_ += move_speed * dt;
        }
    }

    px_ = std::clamp(px_, 1.0f, 14.0f);
    py_ = std::clamp(py_, 3.0f, 13.0f);

    // Trample Burger Ingredients
    for (int i = 0; i < MAX_LAYERS; ++i) {
        BurgerLayer& layer = layers_[i];
        if (layer.is_falling || layer.on_plate) continue;

        if (std::fabs(py_ - layer.y) < 0.4f) {
            int start_x = (layer.col == 0) ? 2 : 10;
            if (px_ >= (float)start_x && px_ <= (float)(start_x + 3)) {
                int seg = (int)(px_ - (float)start_x);
                if (seg >= 0 && seg < 4) {
                    layer.stepped_mask |= (1 << seg);
                }

                if (layer.stepped_mask == 0x0F) {
                    // Full layer trampled! Drop down to next floor!
                    layer.is_falling = true;
                    layer.target_y = layer.y + 3.0f;
                    if (layer.target_y > 13.0f) layer.target_y = 13.0f;
                    layer.stepped_mask = 0;
                    score_ += 50;
                }
            }
        }
    }
}

void Game095BurgerTime::UpdateBurgerLayers(float dt) {
    for (int i = 0; i < MAX_LAYERS; ++i) {
        BurgerLayer& layer = layers_[i];
        if (!layer.is_falling) continue;

        layer.y += 8.0f * dt;

        // Check squishing enemies below
        int start_x = (layer.col == 0) ? 2 : 10;
        for (int e_idx = 0; e_idx < MAX_ENEMIES; ++e_idx) {
            FoodEnemy& e = enemies_[e_idx];
            if (e.active) {
                if (e.x >= (float)start_x && e.x <= (float)(start_x + 3)) {
                    if (std::fabs(e.y - layer.y) < 0.8f) {
                        e.active = false;
                        e.respawn_timer = 2.5f;
                        score_ += 500; // Squashed with burger!
                    }
                }
            }
        }

        if (layer.y >= layer.target_y) {
            layer.y = layer.target_y;
            layer.is_falling = false;

            if (layer.y >= 13.0f) {
                layer.on_plate = true;
            }

            // Check domino cascade: did it hit another layer below?
            for (int k = 0; k < MAX_LAYERS; ++k) {
                if (k != i && layers_[k].col == layer.col && !layers_[k].is_falling) {
                    if (std::fabs(layers_[k].y - layer.y) < 0.5f) {
                        // Cascading drop!
                        layers_[k].is_falling = true;
                        layers_[k].target_y = layers_[k].y + 3.0f;
                        if (layers_[k].target_y > 13.0f) layers_[k].target_y = 13.0f;
                        score_ += 50;
                    }
                }
            }
        }
    }
}

void Game095BurgerTime::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        FoodEnemy& e = enemies_[i];
        if (!e.active) {
            if (e.respawn_timer > 0.0f) {
                e.respawn_timer -= dt;
            } else {
                e.active = true;
                e.stun_timer = 0.0f;
                e.x = (i == 0) ? 1.0f : 14.0f;
                e.y = 3.0f;
                e.vx = (i == 0) ? 1.4f : -1.4f;
            }
            continue;
        }

        if (e.stun_timer > 0.0f) {
            e.stun_timer -= dt;
            continue; // Stunned by pepper!
        }

        // Move horizontally on walkways
        e.x += e.vx * dt;
        if (e.x <= 1.0f) {
            e.x = 1.0f;
            e.vx = std::fabs(e.vx);
        } else if (e.x >= 14.0f) {
            e.x = 14.0f;
            e.vx = -std::fabs(e.vx);
        }
    }
}

void Game095BurgerTime::CheckCollisions() {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        FoodEnemy& e = enemies_[i];
        if (!e.active || e.stun_timer > 0.0f) continue;

        float dx = std::fabs(px_ - e.x);
        float dy = std::fabs(py_ - e.y);

        if (dx < 0.9f && dy < 0.8f) {
            state_ = STATE_CHEF_HIT;
            state_timer_ = 0.0f;
            break;
        }
    }
}

void Game095BurgerTime::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Walkways (Floors at y = 3, 6, 9, 13)
    for (int fy : {3, 6, 9, 13}) {
        for (int x = 1; x <= 14; ++x) {
            set_pixel(x, fy, 40, 60, 140); // Blue girders
        }
    }

    // Ladders (x = 1, 4, 8, 11, 14 from y=3 to 13)
    for (int lx : {1, 4, 8, 11, 14}) {
        for (int y = 3; y <= 13; ++y) {
            if ((y % 2) == 0) {
                set_pixel(lx, y, 220, 220, 40); // Yellow ladder rungs
            }
        }
    }

    // Serving Plates at bottom y = 14
    for (int x = 2; x <= 5; ++x) set_pixel(x, 14, 230, 230, 230);
    for (int x = 10; x <= 13; ++x) set_pixel(x, 14, 230, 230, 230);

    // Burger Layers
    for (int i = 0; i < MAX_LAYERS; ++i) {
        const BurgerLayer& layer = layers_[i];
        int ly = (int)std::round(layer.y);
        int start_x = (layer.col == 0) ? 2 : 10;

        uint8_t r = 200, g = 120, b = 40; // Bun Top
        if (layer.type == ING_PATTY) {
            r = 130; g = 60; b = 30; // Patty
        } else if (layer.type == ING_BUN_BOTTOM) {
            r = 210; g = 135; b = 50; // Bun Bottom
        }

        for (int seg = 0; seg < 4; ++seg) {
            int bx = start_x + seg;
            bool stepped = (layer.stepped_mask & (1 << seg)) != 0;
            // Stepped segments sink slightly or flash
            int seg_y = stepped ? ly + 1 : ly;
            set_pixel(bx, seg_y, r, g, b);
        }
    }

    // Pepper Cloud
    if (pepper_spray_timer_ > 0.0f) {
        int sx = (int)std::round(px_ + facing_ * 1.5f);
        int sy = (int)std::round(py_);
        set_pixel(sx, sy, 255, 255, 255);
        set_pixel(sx, sy - 1, 255, 240, 180);
        set_pixel(sx + facing_, sy, 240, 240, 220);
    }

    // Enemies (Mr. Hot Dog, Mr. Pickle)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        const FoodEnemy& e = enemies_[i];
        if (!e.active) continue;

        int ex = (int)std::round(e.x);
        int ey = (int)std::round(e.y);

        if (e.stun_timer > 0.0f) {
            // Sneeze-stunned: flashing blue / stars
            set_pixel(ex, ey, 40, 160, 255);
            set_pixel(ex, ey - 1, 255, 255, 0);
        } else {
            if (i == 0) {
                // Hot Dog: Red sausage with mustard yellow band
                set_pixel(ex, ey, 220, 50, 40);
                set_pixel(ex, ey - 1, 240, 200, 20);
            } else {
                // Pickle: Green sliced pickle
                set_pixel(ex, ey, 40, 180, 50);
                set_pixel(ex, ey - 1, 80, 220, 70);
            }
        }
    }

    // Chef Peter Pepper
    int px = (int)std::round(px_);
    int py = (int)std::round(py_);

    if (state_ == STATE_CHEF_HIT) {
        set_pixel(px, py, 255, 50, 50);
        set_pixel(px, py - 1, 255, 220, 0);
    } else {
        set_pixel(px, py, 40, 60, 180);         // Blue pants
        set_pixel(px, py - 1, 255, 255, 255);   // White chef coat
        set_pixel(px, py - 2, 255, 255, 255);   // White tall chef hat
        set_pixel(px + facing_, py - 1, 255, 50, 50); // Red neckerchief
    }

    // Top HUD
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 255, 80, 80);
    }
    for (int p = 0; p < peppers_left_ && p < 5; ++p) {
        set_pixel(15 - p, 0, 255, 255, 255); // Pepper shakers
    }
}

} // namespace arcade
