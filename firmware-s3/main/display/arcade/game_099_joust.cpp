#include "game_099_joust.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game099Joust::Game099Joust() {
    Init();
}

void Game099Joust::Init() {
    ResetArena(true);
}

void Game099Joust::Reset() {
    ResetArena(true);
}

void Game099Joust::ResetArena(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        wave_ = 1;
    }
    state_ = STATE_JOUSTING;
    state_timer_ = 0.0f;
    knights_defeated_ = 0;

    px_ = 3.0f;
    py_ = 12.0f;
    vx_ = 0.0f;
    vy_ = 0.0f;
    facing_ = 1;
    on_platform_ = true;
    grabbed_by_lava_ = false;
    lava_escape_flaps_ = 0;

    for (int i = 0; i < MAX_EGGS; ++i) {
        eggs_[i].active = false;
    }

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = true;
        enemies_[i].rank = (i == 2) ? 1 : 0;
        enemies_[i].x = 7.0f + (float)i * 3.0f;
        enemies_[i].y = (i == 0) ? 7.0f : ((i == 1) ? 3.0f : 11.0f);
        enemies_[i].vx = (i % 2 == 0) ? 2.2f : -2.2f;
        enemies_[i].vy = 0.0f;
        enemies_[i].flap_timer = 0.5f + (float)i * 0.3f;
        enemies_[i].respawn_timer = 0.0f;
    }
}

void Game099Joust::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_KNIGHT_DOWN) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetArena(false);
            }
        }
        return;
    }

    if (state_ == STATE_WAVE_CLEAR) {
        if (state_timer_ > 2.0f) {
            wave_++;
            ResetArena(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetArena(true);
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateEnemies(dt);
    UpdateEggs(dt);
    CheckJoustCollisions();

    if (knights_defeated_ >= 4) {
        state_ = STATE_WAVE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1000;
    }
}

void Game099Joust::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Horizontal Glide Steering
    float accel = 8.0f;
    if (buttons & BTN_LEFT) {
        vx_ = std::max(-5.5f, vx_ - accel * dt);
        facing_ = -1;
    } else if (buttons & BTN_RIGHT) {
        vx_ = std::min(5.5f, vx_ + accel * dt);
        facing_ = 1;
    } else {
        vx_ *= std::max(0.0f, 1.0f - 3.5f * dt);
    }

    // Button A: Wing Flap!
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        if (grabbed_by_lava_) {
            lava_escape_flaps_++;
            if (lava_escape_flaps_ >= 3) {
                grabbed_by_lava_ = false;
                vy_ = -6.5f;
                py_ = 13.8f;
            }
        } else {
            vy_ = -5.8f;
            on_platform_ = false;
            score_ += 5;
        }
    }

    // Gravity
    if (!on_platform_ && !grabbed_by_lava_) {
        vy_ += 11.5f * dt;
        py_ += vy_ * dt;
    }

    if (!grabbed_by_lava_) {
        px_ += vx_ * dt;
    }

    // Screen Wraparound
    if (px_ < 0.0f) px_ += 16.0f;
    if (px_ >= 16.0f) px_ -= 16.0f;

    // Platform Collisions (when descending vy_ >= 0)
    if (vy_ >= 0.0f && !grabbed_by_lava_) {
        // Center platform at y=8.0f (x=4.0 to 11.5)
        if (py_ >= 7.6f && py_ <= 8.2f && px_ >= 3.8f && px_ <= 11.8f) {
            py_ = 8.0f;
            vy_ = 0.0f;
            on_platform_ = true;
        }
        // Bottom left platform at y=12.0f (x=0.0 to 5.5)
        else if (py_ >= 11.6f && py_ <= 12.2f && (px_ <= 5.5f || px_ >= 15.0f)) {
            py_ = 12.0f;
            vy_ = 0.0f;
            on_platform_ = true;
        }
        // Bottom right platform at y=12.0f (x=10.0 to 15.5)
        else if (py_ >= 11.6f && py_ <= 12.2f && px_ >= 10.0f) {
            py_ = 12.0f;
            vy_ = 0.0f;
            on_platform_ = true;
        }
        // Top ledge at y=4.0f (x=6.0 to 9.5)
        else if (py_ >= 3.6f && py_ <= 4.2f && px_ >= 5.8f && px_ <= 9.8f) {
            py_ = 4.0f;
            vy_ = 0.0f;
            on_platform_ = true;
        }
    }

    // Lava Pit Danger (bottom y >= 14.5, x between 5.5 and 10.0)
    if (py_ >= 14.5f && px_ >= 5.5f && px_ <= 10.0f) {
        if (!grabbed_by_lava_) {
            grabbed_by_lava_ = true;
            lava_escape_flaps_ = 0;
            vy_ = 0.0f;
        } else {
            // Pulled under
            py_ += 2.0f * dt;
            if (py_ >= 15.5f) {
                state_ = STATE_KNIGHT_DOWN;
                state_timer_ = 0.0f;
            }
        }
    }

    if (py_ < 1.0f) {
        py_ = 1.0f;
        vy_ = 0.5f; // Bonk ceiling
    }
}

void Game099Joust::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        BuzzardKnight& e = enemies_[i];
        if (!e.active) {
            if (e.respawn_timer > 0.0f) {
                e.respawn_timer -= dt;
            } else {
                e.active = true;
                e.x = 2.0f + (float)(rand() % 12);
                e.y = 4.0f;
                e.vx = (rand() % 2 == 0) ? 2.5f : -2.5f;
                e.vy = 0.0f;
                e.flap_timer = 0.5f;
            }
            continue;
        }

        // Flapping AI
        e.flap_timer -= dt;
        if (e.flap_timer <= 0.0f) {
            e.flap_timer = 0.6f + (float)(rand() % 5) * 0.1f;
            e.vy = -5.0f;
        }

        e.vy += 11.0f * dt;
        e.y += e.vy * dt;
        e.x += e.vx * dt;

        // Wraparound
        if (e.x < 0.0f) e.x += 16.0f;
        if (e.x >= 16.0f) e.x -= 16.0f;

        // Bounds
        if (e.y < 2.0f) { e.y = 2.0f; e.vy = 1.0f; }
        if (e.y > 13.5f) { e.y = 13.5f; e.vy = -4.5f; }
    }
}

void Game099Joust::UpdateEggs(float dt) {
    for (int i = 0; i < MAX_EGGS; ++i) {
        Egg& egg = eggs_[i];
        if (!egg.active) continue;

        egg.hatch_timer -= dt;
        if (egg.hatch_timer <= 0.0f) {
            // Hatched into shadow buzzard knight!
            egg.active = false;
            for (int k = 0; k < MAX_ENEMIES; ++k) {
                if (!enemies_[k].active) {
                    enemies_[k].active = true;
                    enemies_[k].x = egg.x;
                    enemies_[k].y = egg.y - 1.0f;
                    enemies_[k].vx = 3.0f;
                    enemies_[k].vy = -5.0f;
                    enemies_[k].rank = 1; // High rank!
                    break;
                }
            }
        }
    }
}

void Game099Joust::CheckJoustCollisions() {
    // 1. Egg Harvesting
    for (int i = 0; i < MAX_EGGS; ++i) {
        Egg& egg = eggs_[i];
        if (!egg.active) continue;

        float dx = std::fabs(px_ - egg.x);
        float dy = std::fabs(py_ - egg.y);
        if (dx < 1.2f && dy < 1.2f) {
            egg.active = false;
            score_ += 250; // Collected egg!
        }
    }

    // 2. Knight vs Enemy Jousting!
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        BuzzardKnight& e = enemies_[i];
        if (!e.active) continue;

        float dx = std::fabs(px_ - e.x);
        float dy = py_ - e.y; // Positive if hero is lower, negative if hero is higher!

        if (dx < 1.2f && std::fabs(dy) < 1.2f) {
            if (dy < -0.2f) {
                // HERO IS HIGHER! Hero wins joust!
                e.active = false;
                e.respawn_timer = 3.0f;
                score_ += 500;
                knights_defeated_++;

                // Spawn Egg
                for (int k = 0; k < MAX_EGGS; ++k) {
                    if (!eggs_[k].active) {
                        eggs_[k].active = true;
                        eggs_[k].x = e.x;
                        eggs_[k].y = std::min(12.0f, e.y + 1.0f);
                        eggs_[k].hatch_timer = 5.0f;
                        break;
                    }
                }

                // Bounce upward after victory
                vy_ = -4.0f;
            } else if (dy > 0.2f) {
                // ENEMY IS HIGHER! Hero defeated!
                state_ = STATE_KNIGHT_DOWN;
                state_timer_ = 0.0f;
                break;
            } else {
                // Equal height: CLANG! Both bounce off horizontally
                vx_ = -vx_;
                e.vx = -e.vx;
                score_ += 20;
            }
        }
    }
}

void Game099Joust::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Dark underground cavern background
    // Center platform at y=8 (x=4 to 11)
    for (int x = 4; x <= 11; ++x) {
        set_pixel(x, 8, 120, 120, 130);
    }
    // Bottom left platform at y=12 (x=0 to 5)
    for (int x = 0; x <= 5; ++x) {
        set_pixel(x, 12, 120, 120, 130);
    }
    // Bottom right platform at y=12 (x=10 to 15)
    for (int x = 10; x <= 15; ++x) {
        set_pixel(x, 12, 120, 120, 130);
    }
    // Top platform at y=4 (x=6 to 9)
    for (int x = 6; x <= 9; ++x) {
        set_pixel(x, 4, 120, 120, 130);
    }

    // Lava Pit at bottom y=15 (x=6 to 9)
    for (int x = 6; x <= 9; ++x) {
        set_pixel(x, 15, 255, 60, 20); // Hot red lava
    }

    // Fire Troll Hand if grabbed
    if (grabbed_by_lava_) {
        set_pixel((int)std::round(px_), 14, 255, 200, 0); // Fiery claw
    }

    // Eggs on platforms
    for (int i = 0; i < MAX_EGGS; ++i) {
        const Egg& egg = eggs_[i];
        if (!egg.active) continue;

        int ex = (int)std::round(egg.x);
        int ey = (int)std::round(egg.y);
        set_pixel(ex, ey, 255, 230, 80); // Glowing golden egg
        set_pixel(ex, ey - 1, 255, 255, 180);
    }

    // Buzzard Knights (Enemies)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        const BuzzardKnight& e = enemies_[i];
        if (!e.active) continue;

        int ex = (int)std::round(e.x);
        int ey = (int)std::round(e.y);

        if (e.rank == 0) {
            // Bounder Buzzard (Red/gray)
            set_pixel(ex, ey, 180, 50, 40);
            set_pixel(ex, ey - 1, 200, 80, 80); // Knight helmet
            set_pixel(ex + (e.vx > 0 ? 1 : -1), ey - 1, 255, 255, 255); // Lance
        } else {
            // Shadow Knight (Dark purple/blue)
            set_pixel(ex, ey, 100, 30, 160);
            set_pixel(ex, ey - 1, 140, 60, 220);
            set_pixel(ex + (e.vx > 0 ? 1 : -1), ey - 1, 255, 255, 255);
        }
    }

    // Ostrich Knight Hero
    int px = (int)std::round(px_);
    int py = (int)std::round(py_);

    if (state_ == STATE_KNIGHT_DOWN) {
        set_pixel(px, py, 255, 50, 50);
        set_pixel(px, py - 1, 255, 200, 0);
    } else {
        // Yellow ostrich body & blue knight
        set_pixel(px, py, 240, 200, 40);            // Ostrich body
        set_pixel(px, py - 1, 40, 120, 240);         // Blue knight armor
        set_pixel(px, py - 2, 220, 220, 220);       // Silver helmet
        set_pixel(px + facing_, py - 1, 255, 255, 255); // Forward silver lance
        set_pixel(px + facing_ * 2, py - 1, 255, 255, 255); // Extended lance tip
    }

    // Top HUD: Lives on left
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 255, 200, 50);
    }
}

} // namespace arcade
