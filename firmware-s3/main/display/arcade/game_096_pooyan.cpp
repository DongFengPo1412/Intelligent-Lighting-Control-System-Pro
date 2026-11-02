#include "game_096_pooyan.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game096Pooyan::Game096Pooyan() {
    Init();
}

void Game096Pooyan::Init() {
    ResetCanyon(true);
}

void Game096Pooyan::Reset() {
    ResetCanyon(true);
}

void Game096Pooyan::ResetCanyon(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        round_ = 1;
    }
    state_ = STATE_DEFENDING;
    state_timer_ = 0.0f;
    wolves_defeated_ = 0;

    basket_y_ = 8.0f;
    shoot_cooldown_ = 0.0f;
    meat_available_ = true;
    meat_active_ = false;
    meat_reload_timer_ = 0.0f;

    for (int i = 0; i < MAX_ARROWS; ++i) {
        arrows_[i].active = false;
    }

    for (int i = 0; i < MAX_WOLVES; ++i) {
        wolves_[i].active = true;
        wolves_[i].is_falling = false;
        wolves_[i].balloon_hp = (i == 1) ? 2 : 1; // pink balloon has 2 hp
        wolves_[i].x = 3.0f + (i * 3.5f);
        wolves_[i].y = 1.0f + (i * 1.5f);
        wolves_[i].vy = 1.2f + (i * 0.4f);
        wolves_[i].respawn_timer = 0.0f;
    }
}

void Game096Pooyan::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_MAMA_HIT) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetCanyon(false);
            }
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.0f) {
            round_++;
            ResetCanyon(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetCanyon(true);
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateArrows(dt);
    UpdateMeat(dt);
    UpdateWolves(dt);
    CheckCombat();

    if (wolves_defeated_ >= 6) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1000;
    }
}

void Game096Pooyan::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (shoot_cooldown_ > 0.0f) shoot_cooldown_ -= dt;

    if (!meat_available_ && !meat_active_) {
        meat_reload_timer_ -= dt;
        if (meat_reload_timer_ <= 0.0f) {
            meat_available_ = true;
        }
    }

    // Elevator Basket Vertical Movement
    float elevator_speed = 7.5f;
    if (buttons & BTN_UP) {
        basket_y_ -= elevator_speed * dt;
    } else if (buttons & BTN_DOWN) {
        basket_y_ += elevator_speed * dt;
    }
    basket_y_ = std::clamp(basket_y_, 2.0f, 13.5f);

    // Button A: Shoot Arrow
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A) && shoot_cooldown_ <= 0.0f) {
        shoot_cooldown_ = 0.22f;
        for (int i = 0; i < MAX_ARROWS; ++i) {
            if (!arrows_[i].active) {
                arrows_[i].active = true;
                arrows_[i].x = 13.0f;
                arrows_[i].y = basket_y_;
                arrows_[i].vx = -14.0f;
                score_ += 10;
                break;
            }
        }
    }

    // Button B: Throw Meat Chunk (Parabolic Arc)
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        if (meat_available_ && !meat_active_) {
            meat_available_ = false;
            meat_active_ = true;
            meat_reload_timer_ = 5.0f;
            meat_x_ = 13.0f;
            meat_y_ = basket_y_;
            meat_vx_ = -8.5f;
            meat_vy_ = -3.5f;
            score_ += 20;
        }
    }
}

void Game096Pooyan::UpdateArrows(float dt) {
    for (int i = 0; i < MAX_ARROWS; ++i) {
        Arrow& a = arrows_[i];
        if (!a.active) continue;

        a.x += a.vx * dt;
        if (a.x < 0.0f) {
            a.active = false;
        }
    }
}

void Game096Pooyan::UpdateMeat(float dt) {
    if (!meat_active_) return;

    meat_x_ += meat_vx_ * dt;
    meat_y_ += meat_vy_ * dt;
    meat_vy_ += 9.5f * dt; // Gravity arc

    if (meat_x_ < 0.0f || meat_y_ > 16.0f) {
        meat_active_ = false;
    }
}

void Game096Pooyan::UpdateWolves(float dt) {
    for (int i = 0; i < MAX_WOLVES; ++i) {
        Wolf& w = wolves_[i];
        if (!w.active) {
            if (w.respawn_timer > 0.0f) {
                w.respawn_timer -= dt;
            } else {
                w.active = true;
                w.is_falling = false;
                w.balloon_hp = (i == 1) ? 2 : 1;
                w.x = 2.5f + (float)(rand() % 8);
                w.y = 0.5f;
                w.vy = 1.2f + (float)(rand() % 4) * 0.3f;
            }
            continue;
        }

        if (w.is_falling) {
            // Screaming fall into bottom of canyon
            w.y += 12.0f * dt;
            if (w.y > 17.0f) {
                w.active = false;
                w.is_falling = false;
                w.respawn_timer = 2.0f;
            }
            continue;
        }

        // Descending on balloon
        w.y += w.vy * dt;

        // When reaching bottom, wolf walks towards elevator
        if (w.y >= 13.5f) {
            w.y = 13.5f;
            w.x += 2.0f * dt;
        }
    }
}

void Game096Pooyan::CheckCombat() {
    // 1. Arrows vs Wolf Balloons
    for (int a_idx = 0; a_idx < MAX_ARROWS; ++a_idx) {
        Arrow& a = arrows_[a_idx];
        if (!a.active) continue;

        for (int w_idx = 0; w_idx < MAX_WOLVES; ++w_idx) {
            Wolf& w = wolves_[w_idx];
            if (!w.active || w.is_falling) continue;

            float dx = std::fabs(a.x - w.x);
            // Balloon is above the wolf body (y - 1.0f)
            float dy = std::fabs(a.y - (w.y - 1.0f));

            if (dx < 1.1f && dy < 1.1f) {
                a.active = false;
                w.balloon_hp--;
                score_ += 50;

                if (w.balloon_hp <= 0) {
                    w.is_falling = true;
                    score_ += 200; // Balloon popped!
                    wolves_defeated_++;
                }
                break;
            }
        }
    }

    // 2. Meat Slab vs Wolves
    if (meat_active_) {
        for (int w_idx = 0; w_idx < MAX_WOLVES; ++w_idx) {
            Wolf& w = wolves_[w_idx];
            if (!w.active || w.is_falling) continue;

            float dx = std::fabs(meat_x_ - w.x);
            float dy = std::fabs(meat_y_ - w.y);

            if (dx < 1.4f && dy < 1.4f) {
                // Wolf tumbles down trying to catch meat!
                w.is_falling = true;
                score_ += 400; // Meat cleave bonus!
                wolves_defeated_++;
            }
        }
    }

    // 3. Wolves vs Mama Pig Basket
    for (int i = 0; i < MAX_WOLVES; ++i) {
        Wolf& w = wolves_[i];
        if (!w.active || w.is_falling) continue;

        float dx = std::fabs(14.0f - w.x);
        float dy = std::fabs(basket_y_ - w.y);

        if (dx < 1.1f && dy < 1.1f) {
            state_ = STATE_MAMA_HIT;
            state_timer_ = 0.0f;
            break;
        }
    }
}

void Game096Pooyan::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Sky Background
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 70, 150, 240);
        }
    }

    // Left Forest Tree Branches (x=0 and 1)
    for (int y = 0; y < 16; ++y) {
        set_pixel(0, y, 120, 70, 30); // Wood trunk
        if ((y % 3) == 0) {
            set_pixel(1, y, 30, 160, 40); // Leaves
            set_pixel(2, y, 30, 160, 40);
        }
    }

    // Right Cliff & Elevator Cable (x=14)
    for (int y = 0; y < 16; ++y) {
        set_pixel(15, y, 140, 80, 40); // Cliff rock
        set_pixel(14, y, 220, 220, 220); // Cable rope
    }

    // Top Pulley Crane at (14, 0)
    set_pixel(14, 0, 100, 100, 100);
    set_pixel(13, 0, 100, 100, 100);

    // Wolves & Balloons
    for (int i = 0; i < MAX_WOLVES; ++i) {
        const Wolf& w = wolves_[i];
        if (!w.active) continue;

        int wx = (int)std::round(w.x);
        int wy = (int)std::round(w.y);

        if (!w.is_falling) {
            // Balloon above wolf
            uint8_t br = 255, bg = 50, bb = 50; // Red balloon (1 HP)
            if (w.balloon_hp >= 2) {
                br = 255; bg = 120; bb = 220; // Pink balloon (2 HP)
            }
            set_pixel(wx, wy - 1, br, bg, bb);
            set_pixel(wx, wy - 2, br, bg, bb);
            set_pixel(wx - 1, wy - 2, br, bg, bb);
            set_pixel(wx + 1, wy - 2, br, bg, bb);
        }

        // Wolf Body
        set_pixel(wx, wy, 120, 120, 130);       // Gray wolf fur
        set_pixel(wx, wy + 1, 120, 120, 130);
        set_pixel(wx - 1, wy, 255, 200, 140);   // Snout
    }

    // Flying Arrows
    for (int i = 0; i < MAX_ARROWS; ++i) {
        const Arrow& a = arrows_[i];
        if (!a.active) continue;

        int ax = (int)std::round(a.x);
        int ay = (int)std::round(a.y);
        set_pixel(ax, ay, 255, 255, 255);       // Arrow tip
        set_pixel(ax + 1, ay, 240, 40, 40);     // Red fletching
    }

    // Flying Meat Slab
    if (meat_active_) {
        int mx = (int)std::round(meat_x_);
        int my = (int)std::round(meat_y_);
        set_pixel(mx, my, 220, 40, 40);         // Juicy meat
        set_pixel(mx + 1, my, 255, 255, 255);   // Bone
        set_pixel(mx, my - 1, 200, 30, 30);
    }

    // Mama Pig in Elevator Basket (x=14)
    int by = (int)std::round(basket_y_);

    if (state_ == STATE_MAMA_HIT) {
        set_pixel(14, by, 255, 50, 50);
        set_pixel(13, by, 255, 200, 0);
    } else {
        // Wooden Gondola Basket
        set_pixel(14, by + 1, 150, 90, 40);
        set_pixel(13, by + 1, 150, 90, 40);

        // Mama Pig
        set_pixel(14, by, 255, 170, 190);       // Pink body
        set_pixel(13, by, 255, 170, 190);       // Snout
        set_pixel(14, by - 1, 255, 240, 50);    // Yellow dress/hat
        set_pixel(12, by, 220, 180, 80);        // Drawn bow
    }

    // Top HUD
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 255, 100, 150);
    }
    if (meat_available_) {
        set_pixel(12, 0, 240, 50, 50); // Meat icon ready
    }
}

} // namespace arcade
