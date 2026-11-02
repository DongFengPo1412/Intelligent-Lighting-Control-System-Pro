#include "game_098_mappy.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game098Mappy::Game098Mappy() {
    Init();
}

void Game098Mappy::Init() {
    ResetMansion(true);
}

void Game098Mappy::Reset() {
    ResetMansion(true);
}

void Game098Mappy::ResetMansion(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        round_ = 1;
    }
    state_ = STATE_IN_MANSION;
    state_timer_ = 0.0f;
    loot_collected_ = 0;

    px_ = 5.0f;
    py_ = 13.0f;
    vy_ = 0.0f;
    facing_ = 1;
    is_on_trampoline_ = false;
    active_tramp_idx_ = -1;
    continuous_bounces_ = 0;

    tramp_wear_left_ = 0;
    tramp_wear_right_ = 0;

    door_floor_ = 6;
    door_x_ = 7;
    door_opened_ = false;

    wave_.active = false;

    // 6 Stolen Treasures Setup
    loot_[0] = {4, 3, 0, false};   // Radio
    loot_[1] = {10, 3, 0, false};  // Radio
    loot_[2] = {5, 6, 1, false};   // TV
    loot_[3] = {11, 6, 1, false};  // TV
    loot_[4] = {4, 9, 2, false};   // Safe
    loot_[5] = {10, 9, 2, false};  // Safe

    for (int i = 0; i < MAX_CATS; ++i) {
        cats_[i].active = true;
        cats_[i].is_blasted = false;
        cats_[i].floor_y = (i == 0) ? 3 : ((i == 1) ? 6 : 9);
        cats_[i].x = (i % 2 == 0) ? 4.0f : 10.0f;
        cats_[i].vx = (i % 2 == 0) ? 1.2f : -1.2f;
        cats_[i].respawn_timer = 0.0f;
    }
}

void Game098Mappy::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_MAPPY_HIT) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetMansion(false);
            }
        }
        return;
    }

    if (state_ == STATE_ROUND_CLEAR) {
        if (state_timer_ > 2.0f) {
            round_++;
            ResetMansion(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetMansion(true);
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateMicrowaveWave(dt);
    UpdateCats(dt);
    CheckLootAndCombat();

    if (loot_collected_ >= MAX_LOOT) {
        state_ = STATE_ROUND_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1000;
    }
}

void Game098Mappy::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (is_on_trampoline_) {
        // Vertical trampoline bounce physics
        vy_ += 13.5f * dt; // Gravity in shaft
        py_ += vy_ * dt;

        // Bounce at trampoline base (y=14)
        if (py_ >= 14.0f) {
            py_ = 14.0f;
            int& wear = (active_tramp_idx_ == 0) ? tramp_wear_left_ : tramp_wear_right_;
            wear++;

            if (wear >= 4) {
                // Trampoline broke! Mappy falls through!
                state_ = STATE_MAPPY_HIT;
                state_timer_ = 0.0f;
                return;
            }

            vy_ = -8.8f; // Launch upward!
            continuous_bounces_++;
            score_ += 10;
        }

        // Stepping off trampoline onto a floor
        for (int fy : {3, 6, 9, 13}) {
            if (std::fabs(py_ - (float)fy) < 0.65f) {
                if (active_tramp_idx_ == 0 && (buttons & BTN_RIGHT)) {
                    // Step off left trampoline into hallway
                    is_on_trampoline_ = false;
                    px_ = 3.2f;
                    py_ = (float)fy;
                    vy_ = 0.0f;
                    tramp_wear_left_ = 0; // Repaired by landing
                    break;
                } else if (active_tramp_idx_ == 1 && (buttons & BTN_LEFT)) {
                    // Step off right trampoline into hallway
                    is_on_trampoline_ = false;
                    px_ = 11.8f;
                    py_ = (float)fy;
                    vy_ = 0.0f;
                    tramp_wear_right_ = 0; // Repaired by landing
                    break;
                }
            }
        }
    } else {
        // Hallway Movement on current floor
        float move_speed = 5.5f;
        if (buttons & BTN_LEFT) {
            px_ -= move_speed * dt;
            facing_ = -1;
        } else if (buttons & BTN_RIGHT) {
            px_ += move_speed * dt;
            facing_ = 1;
        }

        // Entering Trampolines
        if (px_ <= 2.2f) {
            px_ = 2.0f;
            is_on_trampoline_ = true;
            active_tramp_idx_ = 0;
            vy_ = 0.0f;
        } else if (px_ >= 12.8f) {
            px_ = 13.0f;
            is_on_trampoline_ = true;
            active_tramp_idx_ = 1;
            vy_ = 0.0f;
        }

        // Button A: Open Microwave Door
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            if ((int)std::round(py_) == door_floor_) {
                float dx = std::fabs(px_ - (float)door_x_);
                if (dx < 1.2f && !door_opened_) {
                    door_opened_ = true;
                    wave_.active = true;
                    wave_.floor_y = door_floor_;
                    wave_.x = (float)door_x_;
                    wave_.vx = (float)facing_ * 11.0f;
                    score_ += 50;
                }
            }
        }
    }
}

void Game098Mappy::UpdateMicrowaveWave(float dt) {
    if (!wave_.active) return;

    wave_.x += wave_.vx * dt;
    if (wave_.x < 1.0f || wave_.x > 15.0f) {
        wave_.active = false;
    }
}

void Game098Mappy::UpdateCats(float dt) {
    for (int i = 0; i < MAX_CATS; ++i) {
        CatEnemy& c = cats_[i];
        if (!c.active) {
            if (c.respawn_timer > 0.0f) {
                c.respawn_timer -= dt;
            } else {
                c.active = true;
                c.is_blasted = false;
                c.floor_y = 3 + (i * 3) % 9;
                c.x = 7.0f;
                c.vx = (i % 2 == 0) ? 1.2f : -1.2f;
            }
            continue;
        }

        if (c.is_blasted) {
            c.x += c.vx * dt;
            if (c.x < -2.0f || c.x > 18.0f) {
                c.active = false;
                c.is_blasted = false;
                c.respawn_timer = 2.5f;
            }
            continue;
        }

        // Patrol hallway
        c.x += c.vx * dt;
        if (c.x <= 3.0f) {
            c.x = 3.0f;
            c.vx = std::fabs(c.vx);
        } else if (c.x >= 12.0f) {
            c.x = 12.0f;
            c.vx = -std::fabs(c.vx);
        }
    }
}

void Game098Mappy::CheckLootAndCombat() {
    // 1. Microwave Sonic Wave vs Cats
    if (wave_.active) {
        for (int i = 0; i < MAX_CATS; ++i) {
            CatEnemy& c = cats_[i];
            if (!c.active || c.is_blasted) continue;

            if (c.floor_y == wave_.floor_y) {
                float dx = std::fabs(c.x - wave_.x);
                if (dx < 1.4f) {
                    // Blasted off screen!
                    c.is_blasted = true;
                    c.vx = (wave_.vx > 0.0f) ? 14.0f : -14.0f;
                    score_ += 400;
                }
            }
        }
    }

    // 2. Mappy collects Stolen Treasures
    if (!is_on_trampoline_) {
        int cur_y = (int)std::round(py_);
        for (int i = 0; i < MAX_LOOT; ++i) {
            StolenLoot& item = loot_[i];
            if (!item.collected && item.floor_y == cur_y) {
                float dx = std::fabs(px_ - (float)item.x);
                if (dx < 0.9f) {
                    item.collected = true;
                    loot_collected_++;
                    int pts = (item.type == 0) ? 100 : ((item.type == 1) ? 200 : 500);
                    score_ += pts;
                }
            }
        }
    }

    // 3. Cats vs Mappy (Invulnerable while airborne on trampolines!)
    if (!is_on_trampoline_) {
        int cur_y = (int)std::round(py_);
        for (int i = 0; i < MAX_CATS; ++i) {
            CatEnemy& c = cats_[i];
            if (!c.active || c.is_blasted) continue;

            if (c.floor_y == cur_y) {
                float dx = std::fabs(px_ - c.x);
                if (dx < 0.9f) {
                    state_ = STATE_MAPPY_HIT;
                    state_timer_ = 0.0f;
                    break;
                }
            }
        }
    }
}

void Game098Mappy::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Floors (y = 4, 7, 10, 14; walking level is 3, 6, 9, 13)
    for (int fy : {4, 7, 10, 14}) {
        for (int x = 3; x <= 12; ++x) {
            set_pixel(x, fy, 40, 150, 200); // Cyan wooden floor
        }
    }

    // Trampolines (x = 2 and x = 13 at y = 15)
    auto draw_trampoline = [&](int tx, int wear) {
        uint8_t r = 50, g = 230, b = 50; // Green
        if (wear == 1) { r = 40; g = 120; b = 255; } // Blue
        else if (wear == 2) { r = 240; g = 220; b = 30; } // Yellow
        else if (wear >= 3) { r = 255; g = 50; b = 50; } // Red

        set_pixel(tx, 15, r, g, b);
        set_pixel(tx - 1, 15, 120, 120, 120); // Springs
        set_pixel(tx + 1, 15, 120, 120, 120);
    };

    draw_trampoline(2, tramp_wear_left_);
    draw_trampoline(13, tramp_wear_right_);

    // Microwave Door at (7, 6)
    if (!door_opened_) {
        set_pixel(door_x_, door_floor_, 240, 50, 180);     // Flashing magenta door
        set_pixel(door_x_, door_floor_ - 1, 240, 50, 180);
    } else {
        set_pixel(door_x_ + 1, door_floor_, 180, 180, 180); // Open door swing
    }

    // Microwave Sonic Wave
    if (wave_.active) {
        int wx = (int)std::round(wave_.x);
        int wy = wave_.floor_y;
        set_pixel(wx, wy, 255, 255, 100);
        set_pixel(wx, wy - 1, 255, 200, 50);
        set_pixel(wx + (wave_.vx > 0 ? 1 : -1), wy, 255, 100, 255);
    }

    // Stolen Loot
    for (int i = 0; i < MAX_LOOT; ++i) {
        const StolenLoot& item = loot_[i];
        if (item.collected) continue;

        if (item.type == 0) {
            // Radio (Orange/yellow)
            set_pixel(item.x, item.floor_y, 255, 180, 30);
        } else if (item.type == 1) {
            // TV (Cyan screen)
            set_pixel(item.x, item.floor_y, 40, 220, 255);
            set_pixel(item.x, item.floor_y - 1, 100, 100, 100);
        } else {
            // Safe (Gold box)
            set_pixel(item.x, item.floor_y, 255, 215, 0);
            set_pixel(item.x + 1, item.floor_y, 200, 160, 0);
        }
    }

    // Cats (Nyamco / Mewkies)
    for (int i = 0; i < MAX_CATS; ++i) {
        const CatEnemy& c = cats_[i];
        if (!c.active) continue;

        int cx = (int)std::round(c.x);
        int cy = c.floor_y;

        if (c.is_blasted) {
            set_pixel(cx, cy, 255, 200, 0); // Blasted spin
            set_pixel(cx, cy - 1, 255, 50, 50);
        } else {
            if (i == 0) {
                // Boss Cat Nyamco: Big Red Cat
                set_pixel(cx, cy, 220, 30, 30);
                set_pixel(cx, cy - 1, 255, 60, 60);
                set_pixel(cx - 1, cy - 1, 240, 200, 120); // Ears
                set_pixel(cx + 1, cy - 1, 240, 200, 120);
            } else {
                // Mewky: Pink small cat
                set_pixel(cx, cy, 255, 120, 180);
                set_pixel(cx, cy - 1, 255, 150, 200);
            }
        }
    }

    // Police Mouse Mappy
    int px = (int)std::round(px_);
    int py = (int)std::round(py_);

    if (state_ == STATE_MAPPY_HIT) {
        set_pixel(px, py, 255, 50, 50);
        set_pixel(px, py - 1, 255, 220, 0);
    } else {
        set_pixel(px, py, 30, 90, 220);         // Blue police trousers
        set_pixel(px, py - 1, 240, 240, 240);   // White mouse body
        set_pixel(px, py - 2, 40, 120, 240);    // Blue police cap
        set_pixel(px - 1, py - 2, 255, 180, 180); // Round mouse ear
        set_pixel(px + 1, py - 2, 255, 180, 180); // Round mouse ear
    }

    // Top HUD: Lives on left
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 50, 120, 255);
    }
}

} // namespace arcade
