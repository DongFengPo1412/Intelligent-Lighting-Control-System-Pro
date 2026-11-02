#include "game_081_rampage.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace arcade {

Game081Rampage::Game081Rampage() {
    Reset();
}

void Game081Rampage::Init() {
    Reset();
}

void Game081Rampage::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    monster_hp_ = 100;
    days_survived_ = 1;
    ResetCity();
}

void Game081Rampage::ResetCity() {
    mx_ = 1.0f;
    my_ = 14.0f;
    mvy_ = 0.0f;
    on_ground_ = true;
    on_wall_ = false;
    current_building_ = -1;
    facing_ = 1;
    punch_timer_ = 0.0f;

    // 3 Skyscrapers
    buildings_[0].x_left = 1.0f;
    buildings_[0].x_right = 4.0f;
    buildings_[0].height = 10; // y=4 to 14
    buildings_[0].hp = 6;
    buildings_[0].collapsed = false;

    buildings_[1].x_left = 6.0f;
    buildings_[1].x_right = 9.0f;
    buildings_[1].height = 12; // y=2 to 14
    buildings_[1].hp = 8;
    buildings_[1].collapsed = false;

    buildings_[2].x_left = 11.0f;
    buildings_[2].x_right = 14.0f;
    buildings_[2].height = 9;  // y=5 to 14
    buildings_[2].hp = 6;
    buildings_[2].collapsed = false;

    heli_.x = 15.0f;
    heli_.y = 3.0f;
    heli_.vx = -2.5f;
    heli_.active = true;
}

void Game081Rampage::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_MONSTER_DEAD) {
        if (state_timer_ > 2.5f && (buttons & (BUTTON_A | BUTTON_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.0f) {
            days_survived_++;
            score_ += 5000;
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            ResetCity();
        }
        return;
    }

    UpdateMonster(dt, buttons, prev_buttons);
    UpdateHelicopter(dt);

    // Check city demolition victory
    bool all_collapsed = true;
    for (int i = 0; i < NUM_BUILDINGS; ++i) {
        if (!buildings_[i].collapsed) {
            all_collapsed = false;
            break;
        }
    }
    if (all_collapsed) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game081Rampage::UpdateMonster(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float walk_speed = 4.0f;
    float climb_speed = 3.5f;

    if (punch_timer_ > 0.0f) {
        punch_timer_ -= dt;
    }

    // Check Wall Climbing Attachment
    if (!on_wall_) {
        // Find if near any intact building side
        for (int i = 0; i < NUM_BUILDINGS; ++i) {
            if (buildings_[i].collapsed) continue;
            float top_y = 14.0f - buildings_[i].height;
            if (my_ >= top_y && my_ <= 14.0f) {
                if (std::abs(mx_ - buildings_[i].x_left) < 0.6f && (buttons & BUTTON_UP)) {
                    on_wall_ = true;
                    on_ground_ = false;
                    current_building_ = i;
                    mx_ = buildings_[i].x_left;
                    mvy_ = 0.0f;
                    break;
                } else if (std::abs(mx_ - buildings_[i].x_right) < 0.6f && (buttons & BUTTON_UP)) {
                    on_wall_ = true;
                    on_ground_ = false;
                    current_building_ = i;
                    mx_ = buildings_[i].x_right;
                    mvy_ = 0.0f;
                    break;
                }
            }
        }
    }

    if (on_wall_) {
        // Vertical climb
        if (buttons & BUTTON_UP)   my_ -= climb_speed * dt;
        if (buttons & BUTTON_DOWN) my_ += climb_speed * dt;

        float top_y = 14.0f - buildings_[current_building_].height;
        my_ = std::max(top_y, std::min(14.0f, my_));

        // Reach ground
        if (my_ >= 14.0f) {
            on_wall_ = false;
            on_ground_ = true;
            mvy_ = 0.0f;
        }

        // Jump off wall
        if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
            on_wall_ = false;
            mvy_ = -6.0f;
            float leap_dir = (mx_ <= buildings_[current_building_].x_left) ? -1.0f : 1.0f;
            mx_ += leap_dir * 1.5f;
        }
    } else {
        // Horizontal walk
        if (buttons & BUTTON_LEFT)  { mx_ -= walk_speed * dt; facing_ = -1; }
        if (buttons & BUTTON_RIGHT) { mx_ += walk_speed * dt; facing_ = 1; }

        mx_ = std::max(0.5f, std::min(15.0f, mx_));

        // Jump from ground
        if (on_ground_ && (buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
            on_ground_ = false;
            mvy_ = -8.0f;
        }

        // Gravity
        if (!on_ground_) {
            mvy_ += 20.0f * dt;
            my_ += mvy_ * dt;

            // Roof or ground landing
            if (my_ >= 14.0f) {
                my_ = 14.0f;
                mvy_ = 0.0f;
                on_ground_ = true;
            }
        }
    }

    // Punch Attack
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        punch_timer_ = 0.22f;
        CheckPunch();
    }
}

void Game081Rampage::CheckPunch() {
    // 1. Punch Helicopter
    if (heli_.active) {
        float dx = std::abs(heli_.x - mx_);
        float dy = std::abs(heli_.y - my_);
        if (dx < 2.0f && dy < 2.0f) {
            heli_.active = false;
            heli_.respawn_timer = 3.0f;
            score_ += 1000;
            return;
        }
    }

    // 2. Punch Building Wall
    for (int i = 0; i < NUM_BUILDINGS; ++i) {
        if (buildings_[i].collapsed) continue;

        bool in_range_x = (mx_ >= buildings_[i].x_left - 1.2f && mx_ <= buildings_[i].x_right + 1.2f);
        float top_y = 14.0f - buildings_[i].height;
        bool in_range_y = (my_ >= top_y && my_ <= 14.0f);

        if (in_range_x && in_range_y) {
            buildings_[i].hp--;
            score_ += 200;

            if (buildings_[i].hp <= 0) {
                buildings_[i].collapsed = true;
                score_ += 2000;
                if (on_wall_ && current_building_ == i) {
                    on_wall_ = false;
                    mvy_ = 4.0f; // Falls with rubble!
                }
            }
            break;
        }
    }
}

void Game081Rampage::UpdateHelicopter(float dt) {
    if (!heli_.active) {
        if (heli_.respawn_timer > 0.0f) {
            heli_.respawn_timer -= dt;
            if (heli_.respawn_timer <= 0.0f) {
                heli_.x = 15.5f;
                heli_.y = 3.0f + (std::rand() % 4);
                heli_.vx = -2.5f;
                heli_.active = true;
            }
        }
        return;
    }

    heli_.x += heli_.vx * dt;
    if (heli_.x < -1.0f) {
        heli_.x = 16.0f;
        heli_.y = 2.0f + (std::rand() % 5);
    }

    // Heli shoots/collides with monster
    if (std::abs(heli_.x - mx_) < 1.4f && std::abs(heli_.y - my_) < 1.4f) {
        monster_hp_ -= 8;
        if (monster_hp_ <= 0) {
            lives_--;
            if (lives_ > 0) {
                monster_hp_ = 100;
                mx_ = 1.0f;
                my_ = 14.0f;
                on_wall_ = false;
                on_ground_ = true;
            } else {
                state_ = STATE_MONSTER_DEAD;
                state_timer_ = 0.0f;
            }
        }
    }
}

void Game081Rampage::Render(uint8_t* fb) {
    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Night Sky
    for (int y = 0; y < 14; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 10, 15, 30);
        }
    }

    // 2. City Pavement / Ground (y: 14..15)
    for (int y = 14; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 60, 60, 60);
        }
    }

    // 3. Buildings
    for (int b = 0; b < NUM_BUILDINGS; ++b) {
        int xl = static_cast<int>(std::round(buildings_[b].x_left));
        int xr = static_cast<int>(std::round(buildings_[b].x_right));

        if (buildings_[b].collapsed) {
            // Rubble pile
            for (int x = xl; x <= xr; ++x) {
                set_pixel(x, 14, 100, 80, 60);
                set_pixel(x, 13, 80, 60, 40);
            }
        } else {
            int top_y = 14 - buildings_[b].height;
            for (int y = top_y; y < 14; ++y) {
                for (int x = xl; x <= xr; ++x) {
                    // Windows grid
                    if ((x + y) % 2 == 0) {
                        set_pixel(x, y, 255, 230, 100); // Lit window
                    } else {
                        set_pixel(x, y, 120, 100, 90);  // Concrete facade
                    }
                }
            }
        }
    }

    // 4. Helicopter
    if (heli_.active) {
        int hx = static_cast<int>(std::round(heli_.x));
        int hy = static_cast<int>(std::round(heli_.y));
        set_pixel(hx, hy, 40, 120, 220);     // Fuselage
        set_pixel(hx - 1, hy, 255, 255, 255); // Rotor blade
        set_pixel(hx + 1, hy, 255, 255, 255);
        set_pixel(hx, hy - 1, 200, 200, 200);
    }

    // 5. Giant Monster (George the Gorilla: Brown fur, Yellow face)
    int mx = static_cast<int>(std::round(mx_));
    int my = static_cast<int>(std::round(my_));
    set_pixel(mx, my, 140, 80, 30);      // Body
    set_pixel(mx, my - 1, 255, 200, 50); // Face / Jaw
    if (punch_timer_ > 0.0f) {
        set_pixel(mx + facing_, my, 255, 100, 20); // Fists slamming!
    }

    // 6. Monster Health Bar (y = 0)
    int hp_bars = std::max(0, std::min(8, monster_hp_ / 12));
    for (int b = 0; b < hp_bars; ++b) {
        set_pixel(b, 0, 50, 240, 50);
    }
    // Lives
    for (int l = 0; l < lives_; ++l) {
        set_pixel(15 - l * 2, 0, 255, 180, 0);
    }
}

} // namespace arcade
