#include "game_124_carnival.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace arcade {

Game124Carnival::Game124Carnival() {
    Init();
}

void Game124Carnival::Init() {
    score_ = 0;
    round_ = 1;
    ammo_ = 40;
    InitRound();
}

void Game124Carnival::Reset() {
    Init();
}

void Game124Carnival::InitRound() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    ammo_ = 40 + (round_ - 1) * 5;
    gun_x_ = 7.5f;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
        bullets_[i].x = 0.0f;
        bullets_[i].y = 0.0f;
    }

    // Carousels
    // Row 0: Owls (top, slow left)
    // Row 1: Rabbits (mid, medium right)
    // Row 2: Ducks (bottom, slow left, potential divers)
    row_speeds_[0] = -(1.8f + round_ * 0.2f);
    row_speeds_[1] =  (2.4f + round_ * 0.2f);
    row_speeds_[2] = -(2.0f + round_ * 0.2f);

    for (int r = 0; r < NUM_ROWS; ++r) {
        row_offsets_[r] = (float)(r * 3.0f);
        for (int i = 0; i < TARGETS_PER_ROW; ++i) {
            rows_[r][i].x = (float)i * (16.0f / (float)TARGETS_PER_ROW);
            rows_[r][i].alive = true;
            if (r == 0) rows_[r][i].type = (i == 2) ? 3 : 2; // Owl, or extra ammo
            else if (r == 1) rows_[r][i].type = 0;           // Rabbit
            else rows_[r][i].type = 1;                       // Duck
        }
    }

    diving_duck_.active = false;
    diving_duck_.x = 0.0f;
    diving_duck_.y = 0.0f;
    diving_duck_.vx = 0.0f;
    diving_duck_.vy = 0.0f;
    duck_dive_timer_ = 4.0f;

    bonus_wheel_x_ = 0.0f;
    bonus_wheel_alive_ = true;
}

int Game124Carnival::GetRemainingTargets() const {
    int count = 0;
    for (int r = 0; r < NUM_ROWS; ++r) {
        for (int i = 0; i < TARGETS_PER_ROW; ++i) {
            if (rows_[r][i].alive && rows_[r][i].type != 3) {
                count++;
            }
        }
    }
    return count;
}

void Game124Carnival::TriggerDivingDuck() {
    if (diving_duck_.active) return;
    // Find an alive duck in row 2
    for (int i = 0; i < TARGETS_PER_ROW; ++i) {
        if (rows_[2][i].alive && rows_[2][i].type == 1) {
            float duck_world_x = rows_[2][i].x + row_offsets_[2];
            while (duck_world_x < 0.0f) duck_world_x += 16.0f;
            while (duck_world_x >= 16.0f) duck_world_x -= 16.0f;

            rows_[2][i].alive = false;
            diving_duck_.active = true;
            diving_duck_.x = duck_world_x;
            diving_duck_.y = 7.0f;
            diving_duck_.vy = 4.5f;
            diving_duck_.vx = (gun_x_ > duck_world_x) ? 1.5f : -1.5f;
            break;
        }
    }
}

void Game124Carnival::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & 0x0030) && !(prev_buttons & 0x0030)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_ROUND_CLEAR) {
        if (state_timer_ > 1.8f) {
            round_++;
            score_ += (uint32_t)ammo_ * 50; // Bonus for remaining ammo
            InitRound();
        }
        return;
    }

    // Fire bullet
    if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) {
        if (ammo_ > 0) {
            for (int i = 0; i < MAX_BULLETS; ++i) {
                if (!bullets_[i].active) {
                    bullets_[i].active = true;
                    bullets_[i].x = gun_x_;
                    bullets_[i].y = 13.0f;
                    ammo_--;
                    break;
                }
            }
        }
    }

    UpdateGun(dt, buttons);
    UpdateBullets(dt);
    UpdateCarousels(dt);
    UpdateDivingDucks(dt);
    CheckCollisions();

    // Check round victory
    if (GetRemainingTargets() == 0 && !diving_duck_.active) {
        state_ = STATE_ROUND_CLEAR;
        state_timer_ = 0.0f;
    }

    // Check ammunition depletion game over
    if (ammo_ <= 0) {
        bool any_bullet = false;
        for (int i = 0; i < MAX_BULLETS; ++i) {
            if (bullets_[i].active) {
                any_bullet = true;
                break;
            }
        }
        if (!any_bullet && GetRemainingTargets() > 0) {
            state_ = STATE_GAME_OVER;
        }
    }
}

void Game124Carnival::UpdateGun(float dt, uint16_t buttons) {
    float move_speed = 9.0f;
    if (buttons & 0x0004) { // LEFT
        gun_x_ -= move_speed * dt;
    }
    if (buttons & 0x0008) { // RIGHT
        gun_x_ += move_speed * dt;
    }
    if (gun_x_ < 0.5f) gun_x_ = 0.5f;
    if (gun_x_ > 15.5f) gun_x_ = 15.5f;
}

void Game124Carnival::UpdateBullets(float dt) {
    float bullet_speed = 22.0f;
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        bullets_[i].y -= bullet_speed * dt;
        if (bullets_[i].y < 0.0f) {
            bullets_[i].active = false;
        }
    }
}

void Game124Carnival::UpdateCarousels(float dt) {
    for (int r = 0; r < NUM_ROWS; ++r) {
        row_offsets_[r] += row_speeds_[r] * dt;
        while (row_offsets_[r] < 0.0f) row_offsets_[r] += 16.0f;
        while (row_offsets_[r] >= 16.0f) row_offsets_[r] -= 16.0f;
    }

    // Top bonus pipe / wheel
    if (bonus_wheel_alive_) {
        bonus_wheel_x_ += 3.5f * dt;
        if (bonus_wheel_x_ >= 16.0f) bonus_wheel_x_ -= 16.0f;
    }

    // Duck dive timing
    duck_dive_timer_ -= dt;
    if (duck_dive_timer_ <= 0.0f) {
        duck_dive_timer_ = 3.5f + (rand() % 30) * 0.1f;
        TriggerDivingDuck();
    }
}

void Game124Carnival::UpdateDivingDucks(float dt) {
    if (!diving_duck_.active) return;

    diving_duck_.x += diving_duck_.vx * dt;
    diving_duck_.y += diving_duck_.vy * dt;

    if (diving_duck_.y >= 14.0f) {
        // Reached player level!
        if (std::abs(diving_duck_.x - gun_x_) < 1.6f) {
            // Quack attack! Steal 5 bullets!
            ammo_ -= 5;
            if (ammo_ < 0) ammo_ = 0;
        }
        diving_duck_.active = false;
    }
}

void Game124Carnival::CheckCollisions() {
    float row_y[NUM_ROWS] = {3.0f, 5.0f, 7.0f};

    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;

        // 1. Collision with Diving Duck
        if (diving_duck_.active) {
            float dx = std::abs(bullets_[b].x - diving_duck_.x);
            float dy = std::abs(bullets_[b].y - diving_duck_.y);
            if (dx < 0.9f && dy < 0.9f) {
                bullets_[b].active = false;
                diving_duck_.active = false;
                score_ += 50; // Bonus for shooting airborne duck
                continue;
            }
        }

        // 2. Collision with Top Bonus Wheel (y=1.0)
        if (bonus_wheel_alive_ && std::abs(bullets_[b].y - 1.0f) < 0.8f) {
            if (std::abs(bullets_[b].x - bonus_wheel_x_) < 1.0f) {
                bullets_[b].active = false;
                bonus_wheel_alive_ = false;
                ammo_ += 10;
                score_ += 150;
                continue;
            }
        }

        // 3. Collision with Carousel targets
        for (int r = 0; r < NUM_ROWS; ++r) {
            if (std::abs(bullets_[b].y - row_y[r]) < 0.8f) {
                for (int i = 0; i < TARGETS_PER_ROW; ++i) {
                    if (!rows_[r][i].alive) continue;

                    float target_x = rows_[r][i].x + row_offsets_[r];
                    while (target_x < 0.0f) target_x += 16.0f;
                    while (target_x >= 16.0f) target_x -= 16.0f;

                    if (std::abs(bullets_[b].x - target_x) < 0.85f) {
                        bullets_[b].active = false;
                        rows_[r][i].alive = false;

                        if (rows_[r][i].type == 3) {
                            ammo_ += 5; // Extra ammo box
                            score_ += 25;
                        } else if (rows_[r][i].type == 0) {
                            score_ += 10; // Rabbit
                        } else if (rows_[r][i].type == 1) {
                            score_ += 20; // Duck
                        } else if (rows_[r][i].type == 2) {
                            score_ += 30; // Owl
                        }
                        break;
                    }
                }
                if (!bullets_[b].active) break;
            }
        }
    }
}

void Game124Carnival::Render(uint8_t* fb) {
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

    // 1. Draw carousel tracks
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 2, 20, 20, 35);
        set_pixel(x, 4, 20, 20, 35);
        set_pixel(x, 6, 20, 20, 35);
    }

    // 2. Bonus top wheel (y=1)
    if (bonus_wheel_alive_) {
        int bx = (int)std::round(bonus_wheel_x_);
        set_pixel(bx, 1, 255, 215, 0); // Gold wheel
        set_pixel((bx + 1) % 16, 1, 255, 140, 0);
    }

    // 3. Carousel targets
    int row_y[NUM_ROWS] = {3, 5, 7};
    for (int r = 0; r < NUM_ROWS; ++r) {
        for (int i = 0; i < TARGETS_PER_ROW; ++i) {
            if (!rows_[r][i].alive) continue;
            float tx = rows_[r][i].x + row_offsets_[r];
            while (tx < 0.0f) tx += 16.0f;
            while (tx >= 16.0f) tx -= 16.0f;
            int itx = (int)std::round(tx);

            if (rows_[r][i].type == 0) {
                // Rabbit: cyan
                set_pixel(itx, row_y[r], 40, 200, 255);
            } else if (rows_[r][i].type == 1) {
                // Duck: bright yellow
                set_pixel(itx, row_y[r], 255, 220, 30);
            } else if (rows_[r][i].type == 2) {
                // Owl: purple
                set_pixel(itx, row_y[r], 200, 60, 255);
            } else if (rows_[r][i].type == 3) {
                // Ammo box: flashing green
                set_pixel(itx, row_y[r], 30, 255, 80);
            }
        }
    }

    // 4. Diving duck
    if (diving_duck_.active) {
        int dx = (int)std::round(diving_duck_.x);
        int dy = (int)std::round(diving_duck_.y);
        set_pixel(dx, dy, 255, 60, 30); // Danger red-orange diving duck
        set_pixel(dx, dy - 1, 255, 200, 0);
    }

    // 5. Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        int bx = (int)std::round(bullets_[i].x);
        int by = (int)std::round(bullets_[i].y);
        set_pixel(bx, by, 255, 255, 255);
    }

    // 6. Gun Carriage
    int gx = (int)std::round(gun_x_);
    set_pixel(gx, 13, 0, 255, 200);     // Barrel
    set_pixel(gx - 1, 14, 0, 180, 255); // Wheels / chassis
    set_pixel(gx, 14, 255, 255, 255);
    set_pixel(gx + 1, 14, 0, 180, 255);

    // 7. Ammunition meter on bottom row (y=15)
    int ammo_pips = ammo_ / 3;
    if (ammo_pips > 16) ammo_pips = 16;
    for (int a = 0; a < 16; ++a) {
        if (a < ammo_pips) {
            if (ammo_ <= 5) {
                set_pixel(a, 15, 255, 30, 20); // Danger low ammo red
            } else {
                set_pixel(a, 15, 255, 220, 50); // Yellow bullet pip
            }
        } else {
            set_pixel(a, 15, 20, 20, 20);
        }
    }
}

} // namespace arcade
