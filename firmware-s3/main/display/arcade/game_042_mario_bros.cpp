#include "game_042_mario_bros.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

Game042MarioBros::Game042MarioBros()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      lives_(3),
      pow_hits_(3),
      enemies_defeated_(0),
      total_wave_enemies_(6),
      player_x_(4.0f),
      player_y_(13.0f),
      player_vx_(0.0f),
      player_vy_(0.0f),
      player_facing_(1),
      is_grounded_(true),
      pow_shake_timer_(0.0f) {
}

void Game042MarioBros::Init() {
    Reset();
}

void Game042MarioBros::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    pow_hits_ = 3;
    enemies_defeated_ = 0;
    total_wave_enemies_ = 6;
    player_x_ = 4.0f;
    player_y_ = 13.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;
    player_facing_ = 1;
    is_grounded_ = true;
    pow_shake_timer_ = 0.0f;

    InitArena();

    // Spawn initial enemies
    enemies_[0] = {2.0f, 4.0f, 2.5f, 0.0f, true, false, 0.0f, false};
    enemies_[1] = {13.0f, 4.0f, -2.5f, 0.0f, true, false, 0.0f, false};
    enemies_[2] = {6.0f, 7.0f, 2.5f, 0.0f, true, false, 0.0f, false};
    enemies_[3] = {10.0f, 10.0f, -2.5f, 0.0f, true, false, 0.0f, false};
}

void Game042MarioBros::InitArena() {
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            platform_grid_[y][x] = 0;
        }
    }

    // Ground floor (y = 14..15)
    for (int x = 0; x < 16; ++x) {
        platform_grid_[14][x] = 2;
        platform_grid_[15][x] = 2;
    }

    // Tier 1 (Low): y = 11
    for (int x = 1; x <= 6; ++x) platform_grid_[11][x] = 2;
    for (int x = 9; x <= 14; ++x) platform_grid_[11][x] = 2;

    // Tier 2 (Mid): y = 8 (center)
    for (int x = 4; x <= 11; ++x) platform_grid_[8][x] = 2;

    // Tier 3 (High): y = 5
    for (int x = 1; x <= 6; ++x) platform_grid_[5][x] = 2;
    for (int x = 9; x <= 14; ++x) platform_grid_[5][x] = 2;

    // Green spawn pipes (y = 3)
    platform_grid_[3][1] = 1;
    platform_grid_[3][14] = 1;

    // Central POW block at x = 7, y = 12
    platform_grid_[12][7] = 3;
    platform_grid_[12][8] = 3;
}

int Game042MarioBros::GetEnemiesRemaining() const {
    return total_wave_enemies_ - enemies_defeated_;
}

void Game042MarioBros::HitPowBlock() {
    if (pow_hits_ <= 0) return;

    pow_hits_--;
    pow_shake_timer_ = 0.35f;

    // Earthquake: flips all active grounded enemies on screen
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].active) {
            enemies_[i].is_flipped = true;
            enemies_[i].flip_timer = 5.0f;
        }
    }

    score_ += 100;
    if (score_ > high_score_) high_score_ = score_;

    if (pow_hits_ <= 0) {
        platform_grid_[12][7] = 0;
        platform_grid_[12][8] = 0;
    }
}

void Game042MarioBros::BumpCeiling(float bump_x, float bump_y) {
    int bx = static_cast<int>(std::round(bump_x));
    int by = static_cast<int>(std::round(bump_y));

    // Check if POW block was bumped from underneath
    if (by == 12 && (bx == 7 || bx == 8)) {
        HitPowBlock();
        return;
    }

    // Check if an enemy is standing on the platform directly above
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (fabsf(enemies_[i].x - bump_x) <= 1.25f &&
            fabsf(enemies_[i].y - static_cast<float>(by - 1)) <= 0.65f) {
            // Concussion shockwave flips enemy!
            if (!enemies_[i].is_flipped) {
                enemies_[i].is_flipped = true;
                enemies_[i].flip_timer = 5.0f;
            } else {
                enemies_[i].is_flipped = false; // Bumping flipped enemy un-flips it
            }
            score_ += 50;
            if (score_ > high_score_) high_score_ = score_;
        }
    }
}

void Game042MarioBros::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    const float gravity = 22.0f;
    const float run_speed = 5.5f;

    // Horizontal run
    player_vx_ = 0.0f;
    if (buttons & KEY_LEFT) {
        player_vx_ = -run_speed;
        player_facing_ = -1;
    }
    if (buttons & KEY_RIGHT) {
        player_vx_ = run_speed;
        player_facing_ = 1;
    }

    player_x_ += player_vx_ * dt;
    // Screen wrap
    if (player_x_ < 0.0f) player_x_ += 16.0f;
    if (player_x_ >= 16.0f) player_x_ -= 16.0f;

    // Jump (KEY_A)
    if ((buttons & KEY_A) && !(prev_buttons & KEY_A) && is_grounded_) {
        player_vy_ = -10.5f;
        is_grounded_ = false;
    }

    // Vertical physics
    if (!is_grounded_) {
        player_vy_ += gravity * dt;
        player_y_ += player_vy_ * dt;

        // Upward head bump on platforms
        if (player_vy_ < 0.0f) {
            int ceil_y = static_cast<int>(std::round(player_y_ - 0.45f));
            int head_x = static_cast<int>(std::round(player_x_));

            if (ceil_y >= 0 && ceil_y < 16 && head_x >= 0 && head_x < 16) {
                if (platform_grid_[ceil_y][head_x] != 0) {
                    player_vy_ = 0.0f; // Rebound
                    BumpCeiling(player_x_, static_cast<float>(ceil_y));
                }
            }
        }
        // Downward landing on platforms
        else if (player_vy_ >= 0.0f) {
            int floor_y = static_cast<int>(std::round(player_y_ + 1.0f));
            int foot_x = static_cast<int>(std::round(player_x_));

            if (floor_y >= 0 && floor_y < 16 && foot_x >= 0 && foot_x < 16) {
                if (platform_grid_[floor_y][foot_x] != 0 && player_y_ <= static_cast<float>(floor_y - 0.8f)) {
                    player_y_ = static_cast<float>(floor_y - 1.0f);
                    player_vy_ = 0.0f;
                    is_grounded_ = true;
                }
            }
        }
    } else {
        // Grounded: check if platform underneath exists
        int floor_y = static_cast<int>(std::round(player_y_ + 1.0f));
        int foot_x = static_cast<int>(std::round(player_x_));

        if (floor_y >= 0 && floor_y < 16 && foot_x >= 0 && foot_x < 16) {
            if (platform_grid_[floor_y][foot_x] == 0) {
                is_grounded_ = false; // Step off platform into gap
            }
        }
    }
}

void Game042MarioBros::UpdateEnemies(float dt) {
    const float gravity = 20.0f;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (enemies_[i].is_flipped) {
            enemies_[i].flip_timer -= dt;
            if (enemies_[i].flip_timer <= 0.0f) {
                // Recover and turn enraged!
                enemies_[i].is_flipped = false;
                enemies_[i].is_enraged = true;
                enemies_[i].vx = (enemies_[i].vx > 0 ? 5.2f : -5.2f); // Double speed
            }
            continue; // Cannot move while on back
        }

        // Horizontal advance
        enemies_[i].x += enemies_[i].vx * dt;
        // Screen wrap
        if (enemies_[i].x < 0.0f) enemies_[i].x += 16.0f;
        if (enemies_[i].x >= 16.0f) enemies_[i].x -= 16.0f;

        // Fall through gaps
        int floor_y = static_cast<int>(std::round(enemies_[i].y + 1.0f));
        int foot_x = static_cast<int>(std::round(enemies_[i].x));

        bool on_floor = false;
        if (floor_y >= 0 && floor_y < 16 && foot_x >= 0 && foot_x < 16) {
            if (platform_grid_[floor_y][foot_x] != 0) {
                on_floor = true;
            }
        }

        if (!on_floor) {
            enemies_[i].vy += gravity * dt;
            enemies_[i].y += enemies_[i].vy * dt;

            // Check landing on lower floor
            int new_floor = static_cast<int>(std::round(enemies_[i].y + 1.0f));
            if (new_floor >= 0 && new_floor < 16 && foot_x >= 0 && foot_x < 16) {
                if (platform_grid_[new_floor][foot_x] != 0 && enemies_[i].y <= static_cast<float>(new_floor - 0.8f)) {
                    enemies_[i].y = static_cast<float>(new_floor - 1.0f);
                    enemies_[i].vy = 0.0f;
                }
            }
        }
    }
}

void Game042MarioBros::CheckCollisions() {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        float dist = fabsf(player_x_ - enemies_[i].x) + fabsf(player_y_ - enemies_[i].y);
        if (dist <= 0.82f) {
            if (enemies_[i].is_flipped) {
                // Kick flipped turtle off screen!
                enemies_[i].active = false;
                enemies_defeated_++;

                int pts = enemies_[i].is_enraged ? 400 : 200;
                score_ += pts;
                if (score_ > high_score_) high_score_ = score_;

                if (enemies_defeated_ >= total_wave_enemies_) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 1000;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
            } else {
                // Touch unflipped turtle -> Death!
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game042MarioBros::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (pow_shake_timer_ > 0.0f) {
        pow_shake_timer_ -= dt;
    }

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DEAD) {
        if (state_timer_ >= 1.5f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                player_x_ = 4.0f;
                player_y_ = 13.0f;
                player_vx_ = 0.0f;
                player_vy_ = 0.0f;
                is_grounded_ = true;
            }
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ >= 2.5f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateEnemies(dt);
    CheckCollisions();
}

void Game042MarioBros::Render(uint8_t* fb) {
    // Sewer Black / Navy Background (#000000)
    for (int i = 0; i < 256; ++i) {
        fb[i * 3 + 0] = 5;
        fb[i * 3 + 1] = 5;
        fb[i * 3 + 2] = 10;
    }

    // 1. Draw Platforms & Pipes
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            uint8_t tile = platform_grid_[y][x];

            if (tile == 2) {
                // Solid Brick / Metal Platform (Cobalt Blue #2980B9)
                fb[idx + 0] = 41; fb[idx + 1] = 128; fb[idx + 2] = 185;
            } else if (tile == 1) {
                // Drain Pipes (Emerald Green #27AE60)
                fb[idx + 0] = 39; fb[idx + 1] = 174; fb[idx + 2] = 96;
            } else if (tile == 3) {
                // POW Block (Amber Gold / Red)
                fb[idx + 0] = 230; fb[idx + 1] = 126; fb[idx + 2] = 34;
            }
        }
    }

    // 2. Draw Enemies (Shellcreeper Turtles)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));

        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            if (enemies_[i].is_flipped) {
                // Flipped turtle (Yellow belly facing up)
                fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15;
            } else if (enemies_[i].is_enraged) {
                // Enraged fast turtle (Crimson Red)
                fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
            } else {
                // Normal walking turtle (Bright Green shell)
                fb[idx + 0] = 46; fb[idx + 1] = 204; fb[idx + 2] = 113;
            }
        }
    }

    // 3. Draw Player Mario (Classic Scarlet Overalls & Blue Cap)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));

    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Scarlet Mario
    }

    // 4. HUD: Lives on top row
    for (int l = 0; l < lives_ && l < 3; ++l) {
        int idx = (0 * 16 + l) * 3;
        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
    }
}

} // namespace arcade
