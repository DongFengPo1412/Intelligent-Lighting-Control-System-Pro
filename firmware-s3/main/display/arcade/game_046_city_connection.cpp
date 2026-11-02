#include "game_046_city_connection.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

static const int TIER_Y[Game046CityConnection::NUM_TIERS] = {3, 7, 11, 15};

Game046CityConnection::Game046CityConnection()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      lives_(3),
      oil_ammo_(6),
      unpainted_tiles_(NUM_TIERS * 16),
      player_x_(1.0f),
      player_tier_(3),
      player_vx_(0.0f),
      player_dir_(1),
      is_jumping_(false),
      jump_vy_(0.0f),
      jump_y_offset_(0.0f) {
}

void Game046CityConnection::Init() {
    Reset();
}

void Game046CityConnection::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    oil_ammo_ = 6;
    unpainted_tiles_ = NUM_TIERS * 16;
    player_x_ = 1.0f;
    player_tier_ = 3;
    player_vx_ = 0.0f;
    player_dir_ = 1;
    is_jumping_ = false;
    jump_vy_ = 0.0f;
    jump_y_offset_ = 0.0f;

    for (int i = 0; i < MAX_OIL_CANS; ++i) {
        oil_shots_[i].active = false;
    }

    InitHighways();

    // Initialize 3 police patrol cars on different tiers
    police_[0] = {14.0f, 0, -3.5f, true, false, 0.0f};
    police_[1] = {12.0f, 1, -4.0f, true, false, 0.0f};
    police_[2] = {15.0f, 2, -3.8f, true, false, 0.0f};
}

void Game046CityConnection::InitHighways() {
    unpainted_tiles_ = 0;
    for (int t = 0; t < NUM_TIERS; ++t) {
        for (int c = 0; c < 16; ++c) {
            painted_[t][c] = false;
            unpainted_tiles_++;
        }
    }
}

void Game046CityConnection::FireOilCan() {
    if (oil_ammo_ <= 0) return;

    for (int i = 0; i < MAX_OIL_CANS; ++i) {
        if (!oil_shots_[i].active) {
            oil_shots_[i].x = player_x_ + player_dir_ * 0.8f;
            oil_shots_[i].tier = player_tier_;
            oil_shots_[i].vx = player_dir_ * 12.0f;
            oil_shots_[i].active = true;
            oil_ammo_--;
            break;
        }
    }
}

void Game046CityConnection::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    const float max_speed = 7.0f;

    // Horizontal acceleration & U-Turn
    if (buttons & KEY_LEFT) {
        player_dir_ = -1;
        player_vx_ = -max_speed;
    } else if (buttons & KEY_RIGHT) {
        player_dir_ = 1;
        player_vx_ = max_speed;
    } else {
        // Coasting
        if (player_vx_ > 0.0f) player_vx_ = std::max(0.0f, player_vx_ - 10.0f * dt);
        if (player_vx_ < 0.0f) player_vx_ = std::min(0.0f, player_vx_ + 10.0f * dt);
    }

    player_x_ += player_vx_ * dt;
    // Highway screen wrap
    if (player_x_ < 0.0f) player_x_ += 16.0f;
    if (player_x_ >= 16.0f) player_x_ -= 16.0f;

    // Paint highway underneath car
    if (!is_jumping_) {
        int col = static_cast<int>(std::round(player_x_));
        if (col >= 0 && col < 16) {
            if (!painted_[player_tier_][col]) {
                painted_[player_tier_][col] = true;
                unpainted_tiles_--;
                score_ += 10;
                if (score_ > high_score_) high_score_ = score_;

                if (unpainted_tiles_ <= 0) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 1000;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
            }
        }
    }

    // Jump (KEY_A)
    if ((buttons & KEY_A) && !(prev_buttons & KEY_A) && !is_jumping_) {
        is_jumping_ = true;
        jump_vy_ = 9.5f;
        jump_y_offset_ = 0.0f;
    }

    // Jumping physics
    if (is_jumping_) {
        const float gravity = 22.0f;
        jump_vy_ -= gravity * dt;
        jump_y_offset_ += jump_vy_ * dt;

        // Leap to upper tier if pressing UP and reached height of 4 units
        if ((buttons & KEY_UP) && player_tier_ > 0 && jump_y_offset_ >= 3.8f && jump_vy_ > 0.0f) {
            player_tier_--;
            jump_y_offset_ = 0.0f;
            jump_vy_ = 0.0f;
            is_jumping_ = false;
        }
        // Fall back down
        else if (jump_y_offset_ <= 0.0f) {
            jump_y_offset_ = 0.0f;
            jump_vy_ = 0.0f;
            is_jumping_ = false;
        }
    } else {
        // Drop down to lower tier if pressing DOWN
        if ((buttons & KEY_DOWN) && !(prev_buttons & KEY_DOWN) && player_tier_ < 3) {
            player_tier_++;
        }
    }

    // Throw Oil Can (KEY_B)
    if ((buttons & KEY_B) && !(prev_buttons & KEY_B)) {
        FireOilCan();
    }
}

void Game046CityConnection::UpdatePolice(float dt) {
    for (int i = 0; i < NUM_POLICE; ++i) {
        if (!police_[i].active) continue;

        if (police_[i].is_dizzy) {
            police_[i].dizzy_timer -= dt;
            if (police_[i].dizzy_timer <= 0.0f) {
                police_[i].is_dizzy = false;
            }
            continue; // Cannot move while dizzy spinning
        }

        police_[i].x += police_[i].vx * dt;

        // Wrap or bounce on highway tier
        if (police_[i].x < 0.0f) police_[i].x += 16.0f;
        if (police_[i].x >= 16.0f) police_[i].x -= 16.0f;
    }
}

void Game046CityConnection::UpdateOilCans(float dt) {
    for (int i = 0; i < MAX_OIL_CANS; ++i) {
        if (!oil_shots_[i].active) continue;

        oil_shots_[i].x += oil_shots_[i].vx * dt;
        if (oil_shots_[i].x < 0.0f || oil_shots_[i].x > 16.0f) {
            oil_shots_[i].active = false;
        }
    }
}

void Game046CityConnection::CheckCollisions() {
    // 1. Oil cans vs Police cars
    for (int o = 0; o < MAX_OIL_CANS; ++o) {
        if (!oil_shots_[o].active) continue;

        for (int p = 0; p < NUM_POLICE; ++p) {
            if (!police_[p].active || police_[p].tier != oil_shots_[o].tier) continue;

            if (fabsf(oil_shots_[o].x - police_[p].x) <= 0.85f) {
                oil_shots_[o].active = false;
                police_[p].is_dizzy = true;
                police_[p].dizzy_timer = 4.5f;
                score_ += 50;
                if (score_ > high_score_) high_score_ = score_;
                break;
            }
        }
    }

    // 2. Player vs Police cars
    for (int p = 0; p < NUM_POLICE; ++p) {
        if (!police_[p].active || police_[p].tier != player_tier_) continue;

        // If player is airborne high enough above highway, leap over cop car!
        if (is_jumping_ && jump_y_offset_ >= 1.2f) continue;

        if (fabsf(player_x_ - police_[p].x) <= 0.82f) {
            if (police_[p].is_dizzy) {
                // Ram dizzy cop off the overpass!
                police_[p].active = false;
                score_ += 100;
                if (score_ > high_score_) high_score_ = score_;
            } else {
                // Collision with active cop -> Crash!
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game046CityConnection::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

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
                player_x_ = 1.0f;
                player_tier_ = 3;
                player_vx_ = 0.0f;
                is_jumping_ = false;
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
    UpdatePolice(dt);
    UpdateOilCans(dt);
    CheckCollisions();
}

void Game046CityConnection::Render(uint8_t* fb) {
    // 1. City Night Skyline Background (#050510)
    for (int i = 0; i < 256 * 3; ++i) {
        fb[i] = 5;
    }

    // 2. Render 4 Highway Overpasses
    for (int t = 0; t < NUM_TIERS; ++t) {
        int y = TIER_Y[t];
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (painted_[t][x]) {
                // Painted Highway: Bright Emerald Green (#2ECC71)
                fb[idx + 0] = 46; fb[idx + 1] = 204; fb[idx + 2] = 113;
            } else {
                // Unpainted Dark Asphalt (#34495E)
                fb[idx + 0] = 52; fb[idx + 1] = 73; fb[idx + 2] = 94;
            }
        }
    }

    // 3. Render Oil Can Shots (Amber Yellow dots)
    for (int i = 0; i < MAX_OIL_CANS; ++i) {
        if (!oil_shots_[i].active) continue;

        int ox = static_cast<int>(std::round(oil_shots_[i].x));
        int oy = TIER_Y[oil_shots_[i].tier] - 1;
        if (ox >= 0 && ox < 16 && oy >= 0 && oy < 16) {
            int idx = (oy * 16 + ox) * 3;
            fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15;
        }
    }

    // 4. Render Police Patrol Cruisers
    for (int i = 0; i < NUM_POLICE; ++i) {
        if (!police_[i].active) continue;

        int px = static_cast<int>(std::round(police_[i].x));
        int py = TIER_Y[police_[i].tier] - 1;
        if (px >= 0 && px < 16 && py >= 0 && py < 16) {
            int idx = (py * 16 + px) * 3;
            if (police_[i].is_dizzy) {
                // Dizzy Spinning: Flashing Cyan
                fb[idx + 0] = 0; fb[idx + 1] = 255; fb[idx + 2] = 255;
            } else {
                // Active Police Cruiser: Blue & Red
                fb[idx + 0] = 52; fb[idx + 1] = 152; fb[idx + 2] = 219;
            }
        }
    }

    // 5. Render Player Little Honda City (Bright Scarlet #E74C3C)
    int cx = static_cast<int>(std::round(player_x_));
    int cy = TIER_Y[player_tier_] - 1 - static_cast<int>(std::round(jump_y_offset_));
    if (cx >= 0 && cx < 16 && cy >= 0 && cy < 16) {
        int idx = (cy * 16 + cx) * 3;
        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
    }

    // 6. HUD: Oil Ammo on top row
    for (int a = 0; a < oil_ammo_ && a < 6; ++a) {
        int idx = (0 * 16 + a) * 3;
        fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15;
    }
}

} // namespace arcade
