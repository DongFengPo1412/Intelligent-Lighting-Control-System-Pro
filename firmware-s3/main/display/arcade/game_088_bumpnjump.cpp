#include "game_088_bumpnjump.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game088BumpNJump::Game088BumpNJump() {
    Init();
}

void Game088BumpNJump::Init() {
    ResetStage(true);
}

void Game088BumpNJump::Reset() {
    ResetStage(true);
}

void Game088BumpNJump::ResetStage(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        level_ = 1;
        crushed_count_ = 0;
    }
    state_ = STATE_DRIVING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 13.0f;
    speed_ = 110.0f;
    jump_z_ = 0.0f;
    jump_vz_ = 0.0f;
    is_jumping_ = false;
    bump_vx_ = 0.0f;
    bump_boost_cooldown_ = 0.0f;
    distance_ = 0.0f;
    stage_length_ = 500.0f + level_ * 100.0f;
    road_scroll_ = 0.0f;
    water_gap_dist_ = 160.0f;
    water_gap_length_ = 6.0f;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = false;
        enemies_[i].respawn_timer = 1.0f + i * 1.5f;
        enemies_[i].x = 4.0f + (i % 3) * 3.5f;
        enemies_[i].y = -2.0f - i * 4.0f;
        enemies_[i].speed = 70.0f + (i % 2) * 20.0f;
        enemies_[i].type = (i == 1) ? ENEMY_TRUCK : ENEMY_CAR;
    }
}

void Game088BumpNJump::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_CRASHED) {
        if (state_timer_ > 2.0f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetStage(false);
            }
        }
        return;
    }

    if (state_ == STATE_LEVEL_CLEAR) {
        if (state_timer_ > 2.5f) {
            level_++;
            ResetStage(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetStage(true);
        }
        return;
    }

    // STATE_DRIVING
    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateEnemies(dt);
    UpdateRoadHazards(dt);
    CheckCollisions();

    // Stage progression
    distance_ += (speed_ * 0.08f) * dt;
    if (distance_ >= stage_length_) {
        state_ = STATE_LEVEL_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1000;
    }
}

void Game088BumpNJump::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Acceleration and braking
    if (buttons & BTN_UP) {
        speed_ += 40.0f * dt;
        if (speed_ > 180.0f) speed_ = 180.0f;
    } else if (buttons & BTN_DOWN) {
        speed_ -= 50.0f * dt;
        if (speed_ < 40.0f) speed_ = 40.0f;
    } else {
        // Natural gradual speed drift towards 100 km/h
        if (speed_ < 100.0f) speed_ += 10.0f * dt;
        else if (speed_ > 100.0f) speed_ -= 10.0f * dt;
    }

    // Lateral steering
    float steer_speed = 7.0f;
    if (buttons & BTN_LEFT) {
        px_ -= steer_speed * dt;
    }
    if (buttons & BTN_RIGHT) {
        px_ += steer_speed * dt;
    }

    // Apply bump impulse decay
    if (std::fabs(bump_vx_) > 0.01f) {
        px_ += bump_vx_ * dt;
        bump_vx_ *= std::max(0.0f, 1.0f - 8.0f * dt);
    }

    // Clamp player to road boundaries (guard rails at x=2.0 and x=13.0)
    if (px_ < 2.2f) {
        px_ = 2.2f;
        bump_vx_ = 2.0f; // bounce off rail
        speed_ = std::max(40.0f, speed_ - 15.0f * dt);
    } else if (px_ > 12.8f) {
        px_ = 12.8f;
        bump_vx_ = -2.0f;
        speed_ = std::max(40.0f, speed_ - 15.0f * dt);
    }

    // Jump logic (Button A: Jump into the air, requires speed >= 100 km/h)
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        if (!is_jumping_ && speed_ >= 100.0f) {
            is_jumping_ = true;
            jump_z_ = 0.05f;
            jump_vz_ = 4.8f; // initial vertical speed
        }
    }

    // Lateral Bump Boost (Button B: Sideways tackle boost)
    if (bump_boost_cooldown_ > 0.0f) {
        bump_boost_cooldown_ -= dt;
    }
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B) && bump_boost_cooldown_ <= 0.0f) {
        bump_boost_cooldown_ = 0.8f;
        float dir = (buttons & BTN_LEFT) ? -1.0f : ((buttons & BTN_RIGHT) ? 1.0f : (px_ < 7.5f ? 1.0f : -1.0f));
        bump_vx_ = dir * 9.0f;
        score_ += 10;
    }

    // Airborne physics
    if (is_jumping_) {
        jump_z_ += jump_vz_ * dt;
        jump_vz_ -= 8.5f * dt; // gravity

        if (jump_z_ <= 0.0f) {
            jump_z_ = 0.0f;
            jump_vz_ = 0.0f;
            is_jumping_ = false;
        }
    }

    road_scroll_ += (speed_ * 0.15f) * dt;
    if (road_scroll_ >= 4.0f) road_scroll_ -= 4.0f;
}

void Game088BumpNJump::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        Enemy& e = enemies_[i];
        if (!e.active) {
            if (e.respawn_timer > 0.0f) {
                e.respawn_timer -= dt;
            } else {
                e.active = true;
                e.x = 3.5f + (float)(rand() % 8);
                e.y = -2.0f;
                e.speed = 60.0f + (float)(rand() % 40);
                e.type = (rand() % 4 == 0) ? ENEMY_TRUCK : ENEMY_CAR;
            }
            continue;
        }

        // Relative speed moves enemy vertically on screen
        float rel_speed = (speed_ - e.speed) * 0.1f;
        e.y += rel_speed * dt;

        // Simple wandering AI
        if (e.type == ENEMY_CAR) {
            e.x += ((i % 2 == 0) ? 0.8f : -0.8f) * dt;
            if (e.x < 3.0f) e.x = 3.0f;
            if (e.x > 12.0f) e.x = 12.0f;
        }

        // Off-screen despawn
        if (e.y > 18.0f || e.y < -8.0f) {
            e.active = false;
            e.respawn_timer = 2.0f + (rand() % 2);
        }
    }
}

void Game088BumpNJump::UpdateRoadHazards(float dt) {
    water_gap_dist_ -= (speed_ * 0.12f) * dt;

    // Check if player reaches water gap while grounded
    // Water gap hazards are active when distance spans the player's position (py_ = 13)
    // Here water_gap_dist_ measures distance from top (y=0)
    // When water_gap_dist_ is around 13.0f, it aligns with py_
    if (water_gap_dist_ >= 10.0f && water_gap_dist_ <= 14.5f) {
        if (!is_jumping_ || jump_z_ < 0.25f) {
            // Fell into water / broken bridge!
            state_ = STATE_CRASHED;
            state_timer_ = 0.0f;
            return;
        }
    }

    if (water_gap_dist_ < -8.0f) {
        // Scheduled next water hazard
        water_gap_dist_ = 200.0f + (rand() % 100);
    }
}

void Game088BumpNJump::CheckCollisions() {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        Enemy& e = enemies_[i];
        if (!e.active) continue;

        float dx = std::fabs(px_ - e.x);
        float dy = std::fabs(py_ - e.y);

        if (dx < 1.3f && dy < 1.4f) {
            if (is_jumping_) {
                // If descending or near landing height, player crushes enemy!
                if (jump_vz_ < 0.5f && jump_z_ <= 1.2f) {
                    e.active = false;
                    e.respawn_timer = 2.5f;
                    score_ += 200;
                    crushed_count_++;
                    // Bounce up slightly after crushing
                    jump_vz_ = 2.5f;
                }
            } else {
                // Ground bump collision!
                float shove_dir = (px_ < e.x) ? -1.0f : 1.0f;
                px_ += shove_dir * 0.6f;
                e.x -= shove_dir * 1.5f;

                if (e.type == ENEMY_TRUCK) {
                    // Trucks are heavy, knock player harder
                    bump_vx_ = shove_dir * 3.5f;
                    speed_ = std::max(40.0f, speed_ - 20.0f);
                } else {
                    bump_vx_ = shove_dir * 1.5f;
                }

                // If enemy got shoved into guard rails (x < 2.2 or x > 12.8)
                if (e.x < 2.2f || e.x > 12.8f) {
                    e.active = false;
                    e.respawn_timer = 2.0f;
                    score_ += 100; // Bump smash bonus!
                }
            }
        }
    }
}

void Game088BumpNJump::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Render road and scenery
    int scroll_offset = (int)road_scroll_ % 2;

    for (int y = 0; y < 16; ++y) {
        // Scenery grass borders
        set_pixel(0, y, 10, 45, 10);
        set_pixel(1, y, 15, 60, 15);
        set_pixel(14, y, 15, 60, 15);
        set_pixel(15, y, 10, 45, 10);

        // Guard rails
        bool stripe = ((y + scroll_offset) % 2 == 0);
        if (stripe) {
            set_pixel(2, y, 220, 220, 220);
            set_pixel(13, y, 220, 220, 220);
        } else {
            set_pixel(2, y, 180, 30, 30);
            set_pixel(13, y, 180, 30, 30);
        }

        // Road surface
        for (int x = 3; x <= 12; ++x) {
            set_pixel(x, y, 35, 38, 45);
        }

        // Center dashed lines
        if ((y + scroll_offset) % 4 < 2) {
            set_pixel(7, y, 120, 120, 100);
            set_pixel(8, y, 120, 120, 100);
        }
    }

    // Render Water Hazard / Broken Bridge if in visible range
    int water_y = (int)water_gap_dist_;
    for (int dy = 0; dy < 3; ++dy) {
        int wy = water_y + dy;
        if (wy >= 0 && wy < 16) {
            for (int x = 2; x <= 13; ++x) {
                set_pixel(x, wy, 0, 70, 180); // Blue water gap
            }
            // Broken wood plank indicators on edges
            set_pixel(2, wy, 139, 69, 19);
            set_pixel(13, wy, 139, 69, 19);
        }
    }

    // Render Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        const Enemy& e = enemies_[i];
        if (!e.active) continue;

        int ex = (int)std::round(e.x);
        int ey = (int)std::round(e.y);

        if (e.type == ENEMY_TRUCK) {
            // Heavy purple truck (2x2)
            set_pixel(ex, ey, 180, 40, 180);
            set_pixel(ex + 1, ey, 180, 40, 180);
            set_pixel(ex, ey + 1, 100, 20, 100);
            set_pixel(ex + 1, ey + 1, 100, 20, 100);
        } else {
            // Normal orange/red car
            set_pixel(ex, ey, 240, 120, 20);
            set_pixel(ex, ey + 1, 180, 60, 10);
            set_pixel(ex - 1, ey + 1, 40, 40, 40); // tire
            set_pixel(ex + 1, ey + 1, 40, 40, 40); // tire
        }
    }

    // Render Player Buggy
    int px = (int)std::round(px_);
    int py = (int)std::round(py_);

    if (state_ == STATE_CRASHED) {
        // Crash explosion (orange/yellow sparks)
        set_pixel(px, py, 255, 200, 0);
        set_pixel(px - 1, py - 1, 255, 50, 0);
        set_pixel(px + 1, py - 1, 255, 100, 0);
        set_pixel(px - 1, py + 1, 200, 20, 0);
        set_pixel(px + 1, py + 1, 255, 150, 0);
    } else {
        if (is_jumping_) {
            // Drop shadow on the road
            set_pixel(px, py, 15, 15, 18);
            set_pixel(px, py + 1, 15, 15, 18);

            // Car rendered elevated / glowing bright cyan
            int elevated_y = py - (int)std::round(jump_z_ * 1.5f);
            set_pixel(px, elevated_y, 80, 240, 255);
            set_pixel(px, elevated_y + 1, 30, 180, 240);
            set_pixel(px - 1, elevated_y, 255, 255, 255); // Jump wing / air shine
            set_pixel(px + 1, elevated_y, 255, 255, 255);
        } else {
            // Ground buggy (Yellow/Cyan sports buggy)
            set_pixel(px, py, 40, 180, 240);
            set_pixel(px, py + 1, 20, 120, 200);
            // Wheels
            set_pixel(px - 1, py, 30, 30, 30);
            set_pixel(px + 1, py, 30, 30, 30);
            set_pixel(px - 1, py + 1, 30, 30, 30);
            set_pixel(px + 1, py + 1, 30, 30, 30);
        }
    }

    // Top HUD: Lives indicator on top left, Speed bar on top right
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 0, 255, 100);
    }

    int speed_bars = (int)((speed_ / 180.0f) * 4.0f);
    for (int s = 0; s < speed_bars; ++s) {
        set_pixel(15 - s, 0, (speed_ >= 100.0f) ? 0 : 255, (speed_ >= 100.0f) ? 255 : 200, 0);
    }
}

} // namespace arcade
