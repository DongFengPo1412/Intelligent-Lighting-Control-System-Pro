#include "game_031_rally_x.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

// Directions: 0: Up, 1: Right, 2: Down, 3: Left
static const int DX[4] = {0, 1, 0, -1};
static const int DY[4] = {-1, 0, 1, 0};

Game031RallyX::Game031RallyX()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      lives_(3),
      fuel_(100.0f),
      player_x_(7.0f),
      player_y_(13.0f),
      player_dir_(0),
      next_dir_(0),
      smoke_cooldown_(0.0f) {
}

void Game031RallyX::Init() {
    Reset();
}

void Game031RallyX::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    fuel_ = 100.0f;
    smoke_cooldown_ = 0.0f;
    InitMaze();
    ResetCars();
}

void Game031RallyX::InitMaze() {
    // 0: Road, 1: Wall, 2: Rock
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            maze_[y][x] = 0;
        }
    }

    // Outer border (Row 0 is HUD)
    for (int x = 0; x < 16; ++x) {
        maze_[1][x] = 1;
        maze_[15][x] = 1;
    }
    for (int y = 1; y < 16; ++y) {
        maze_[y][0] = 1;
        maze_[y][15] = 1;
    }

    // Rock obstacles inside the arena
    const int rocks[][2] = {
        {3, 3}, {4, 3}, {7, 3}, {8, 3}, {11, 3}, {12, 3},
        {3, 6}, {3, 7}, {12, 6}, {12, 7},
        {7, 7}, {8, 7},
        {3, 10}, {4, 10}, {7, 10}, {8, 10}, {11, 10}, {12, 10}
    };
    int rock_count = sizeof(rocks) / sizeof(rocks[0]);
    for (int i = 0; i < rock_count; ++i) {
        maze_[rocks[i][1]][rocks[i][0]] = 2;
    }

    // Initialize 8 Checkered Flags
    const int flag_coords[MAX_FLAGS][2] = {
        {2, 2}, {13, 2},
        {7, 5},
        {2, 8}, {13, 8},
        {5, 12}, {10, 12},
        {8, 8} // Special Lucky Flag
    };

    for (int i = 0; i < MAX_FLAGS; ++i) {
        flags_[i].x = flag_coords[i][0];
        flags_[i].y = flag_coords[i][1];
        flags_[i].collected = false;
        flags_[i].is_special = (i == 7);
    }

    for (int i = 0; i < MAX_SMOKES; ++i) {
        smokes_[i].active = false;
    }
}

void Game031RallyX::ResetCars() {
    player_x_ = 7.0f;
    player_y_ = 13.0f;
    player_dir_ = 0; // Up
    next_dir_ = 0;

    // Spawn 2 pursuit red cars
    enemies_[0].x = 2.0f;
    enemies_[0].y = 4.0f;
    enemies_[0].dir = 1; // Right
    enemies_[0].stun_timer = 0.0f;
    enemies_[0].active = true;

    enemies_[1].x = 13.0f;
    enemies_[1].y = 4.0f;
    enemies_[1].dir = 3; // Left
    enemies_[1].stun_timer = 0.0f;
    enemies_[1].active = true;

    enemies_[2].x = 7.0f;
    enemies_[2].y = 2.0f;
    enemies_[2].dir = 2; // Down
    enemies_[2].stun_timer = 0.0f;
    enemies_[2].active = true;
}

bool Game031RallyX::IsWallOrRock(int x, int y) const {
    if (x < 0 || x >= 16 || y < 1 || y >= 16) return true;
    return maze_[y][x] != 0;
}

int Game031RallyX::GetFlagsRemaining() const {
    int rem = 0;
    for (int i = 0; i < MAX_FLAGS; ++i) {
        if (!flags_[i].collected) rem++;
    }
    return rem;
}

bool Game031RallyX::DeploySmoke() {
    if (fuel_ <= 0.0f || smoke_cooldown_ > 0.0f) return false;

    // Find free smoke slot
    for (int i = 0; i < MAX_SMOKES; ++i) {
        if (!smokes_[i].active) {
            // Drop behind car
            int back_dir = (player_dir_ + 2) % 4;
            int sx = static_cast<int>(std::round(player_x_)) + DX[back_dir];
            int sy = static_cast<int>(std::round(player_y_)) + DY[back_dir];
            if (sx < 1) sx = 1;
            if (sx > 14) sx = 14;
            if (sy < 2) sy = 2;
            if (sy > 14) sy = 14;

            smokes_[i].x = sx;
            smokes_[i].y = sy;
            smokes_[i].timer = 3.0f;
            smokes_[i].active = true;
            fuel_ = std::max(0.0f, fuel_ - 6.0f);
            smoke_cooldown_ = 0.4f;
            return true;
        }
    }
    return false;
}

void Game031RallyX::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DEAD) {
        if (state_timer_ >= 1.2f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                ResetCars();
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

    // Playing state
    if (smoke_cooldown_ > 0.0f) {
        smoke_cooldown_ -= dt;
    }

    // Fuel consumption: 1.5 fuel / sec
    if (fuel_ > 0.0f) {
        fuel_ = std::max(0.0f, fuel_ - 1.5f * dt);
    }

    // Smoke deployment button (KEY_A)
    if ((buttons & KEY_A) && !(prev_buttons & KEY_A)) {
        DeploySmoke();
    }

    UpdatePlayer(dt, buttons);
    UpdateEnemies(dt);
    UpdateSmokes(dt);
    CheckCollisions();
}

void Game031RallyX::UpdatePlayer(float dt, uint32_t buttons) {
    if (buttons & KEY_UP) next_dir_ = 0;
    else if (buttons & KEY_RIGHT) next_dir_ = 1;
    else if (buttons & KEY_DOWN) next_dir_ = 2;
    else if (buttons & KEY_LEFT) next_dir_ = 3;

    float speed = (fuel_ > 0.0f) ? 4.2f : 2.2f;

    // Grid snapping check for 90-degree turns
    float gx = std::round(player_x_);
    float gy = std::round(player_y_);
    float dist_to_center = fabsf(player_x_ - gx) + fabsf(player_y_ - gy);

    if (dist_to_center < 0.25f && next_dir_ != player_dir_) {
        int nx = static_cast<int>(gx) + DX[next_dir_];
        int ny = static_cast<int>(gy) + DY[next_dir_];
        if (!IsWallOrRock(nx, ny)) {
            player_x_ = gx;
            player_y_ = gy;
            player_dir_ = next_dir_;
        }
    }

    // Move in current dir
    float next_x = player_x_ + DX[player_dir_] * speed * dt;
    float next_y = player_y_ + DY[player_dir_] * speed * dt;

    // Wall collision
    int check_x = static_cast<int>(std::round(next_x + DX[player_dir_] * 0.45f));
    int check_y = static_cast<int>(std::round(next_y + DY[player_dir_] * 0.45f));

    if (!IsWallOrRock(check_x, check_y)) {
        player_x_ = next_x;
        player_y_ = next_y;
    } else {
        // Snap to grid
        player_x_ = gx;
        player_y_ = gy;
    }

    // Clamp
    player_x_ = std::max(1.0f, std::min(14.0f, player_x_));
    player_y_ = std::max(2.0f, std::min(14.0f, player_y_));
}

void Game031RallyX::UpdateEnemies(float dt) {
    const float enemy_speed = 3.2f;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (enemies_[i].stun_timer > 0.0f) {
            enemies_[i].stun_timer -= dt;
            continue; // Stunned in smoke spinout
        }

        float egx = std::round(enemies_[i].x);
        float egy = std::round(enemies_[i].y);
        float dist_to_center = fabsf(enemies_[i].x - egx) + fabsf(enemies_[i].y - egy);

        // At grid intersection, recalculate direction toward player
        if (dist_to_center < 0.22f) {
            int best_dir = enemies_[i].dir;
            float best_dist = 99999.0f;
            int opposite_dir = (enemies_[i].dir + 2) % 4;

            for (int d = 0; d < 4; ++d) {
                // Avoid immediate 180 u-turn unless dead-end
                int test_x = static_cast<int>(egx) + DX[d];
                int test_y = static_cast<int>(egy) + DY[d];

                if (!IsWallOrRock(test_x, test_y)) {
                    float penalty = (d == opposite_dir) ? 8.0f : 0.0f;
                    float d2 = (test_x - player_x_) * (test_x - player_x_) +
                               (test_y - player_y_) * (test_y - player_y_) + penalty;
                    if (d2 < best_dist) {
                        best_dist = d2;
                        best_dir = d;
                    }
                }
            }

            enemies_[i].x = egx;
            enemies_[i].y = egy;
            enemies_[i].dir = best_dir;
        }

        // Advance
        enemies_[i].x += DX[enemies_[i].dir] * enemy_speed * dt;
        enemies_[i].y += DY[enemies_[i].dir] * enemy_speed * dt;
    }
}

void Game031RallyX::UpdateSmokes(float dt) {
    for (int i = 0; i < MAX_SMOKES; ++i) {
        if (!smokes_[i].active) continue;

        smokes_[i].timer -= dt;
        if (smokes_[i].timer <= 0.0f) {
            smokes_[i].active = false;
            continue;
        }

        // Test collision with chasing enemies
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (enemies_[e].active && enemies_[e].stun_timer <= 0.0f) {
                float dist = fabsf(enemies_[e].x - smokes_[i].x) + fabsf(enemies_[e].y - smokes_[i].y);
                if (dist < 0.85f) {
                    enemies_[e].stun_timer = 2.8f; // Spinout!
                    score_ += 100;
                    if (score_ > high_score_) high_score_ = score_;
                }
            }
        }
    }
}

void Game031RallyX::CheckCollisions() {
    // 1. Check flag collection
    for (int i = 0; i < MAX_FLAGS; ++i) {
        if (!flags_[i].collected) {
            float dist = fabsf(player_x_ - flags_[i].x) + fabsf(player_y_ - flags_[i].y);
            if (dist < 0.75f) {
                flags_[i].collected = true;
                if (flags_[i].is_special) {
                    score_ += 400 + static_cast<int>(fuel_) * 5;
                } else {
                    score_ += 100;
                }
                if (score_ > high_score_) high_score_ = score_;

                // Check victory condition
                if (GetFlagsRemaining() == 0) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 1000 + static_cast<int>(fuel_) * 10;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
            }
        }
    }

    // 2. Check collision with unstunned enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].active && enemies_[i].stun_timer <= 0.0f) {
            float dist = fabsf(player_x_ - enemies_[i].x) + fabsf(player_y_ - enemies_[i].y);
            if (dist < 0.72f) {
                // Crash!
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game031RallyX::Render(uint8_t* fb) {
    // Clear screen (Dark Road asphalt #101418)
    for (int i = 0; i < 256; ++i) {
        fb[i * 3 + 0] = 16;
        fb[i * 3 + 1] = 20;
        fb[i * 3 + 2] = 24;
    }

    // 1. Draw Top HUD (Row 0): Fuel Bar & Lives
    // Fuel gauge on left (8 dots)
    int fuel_dots = static_cast<int>((fuel_ / 100.0f) * 8.0f);
    for (int x = 0; x < 8; ++x) {
        int idx = x * 3;
        if (x < fuel_dots) {
            if (fuel_ > 50.0f) {
                fb[idx + 0] = 46;  fb[idx + 1] = 204; fb[idx + 2] = 113; // Green
            } else if (fuel_ > 20.0f) {
                fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15;  // Yellow
            } else {
                fb[idx + 0] = 231; fb[idx + 1] = 76;  fb[idx + 2] = 60;  // Red
            }
        } else {
            fb[idx + 0] = 40; fb[idx + 1] = 40; fb[idx + 2] = 40; // Empty gauge
        }
    }

    // Lives on right (Red hearts)
    for (int l = 0; l < lives_ && l < 3; ++l) {
        int idx = (15 - l) * 3;
        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
    }

    // 2. Draw Walls (Cobblestone Grey #7F8C8D) and Rocks (Solid Amber #D35400)
    for (int y = 1; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (maze_[y][x] == 1) {
                // Outer wall
                fb[idx + 0] = 100; fb[idx + 1] = 110; fb[idx + 2] = 120;
            } else if (maze_[y][x] == 2) {
                // Rock block
                fb[idx + 0] = 180; fb[idx + 1] = 90;  fb[idx + 2] = 40;
            }
        }
    }

    // 3. Draw Checkered Flags (Gold #F1C40F, Special Lucky Flag Blinks Red/Gold)
    for (int i = 0; i < MAX_FLAGS; ++i) {
        if (!flags_[i].collected) {
            int idx = (flags_[i].y * 16 + flags_[i].x) * 3;
            if (flags_[i].is_special) {
                // Blinking lucky flag
                bool blink = (static_cast<int>(state_timer_ * 6.0f) % 2 == 0);
                if (blink) {
                    fb[idx + 0] = 255; fb[idx + 1] = 215; fb[idx + 2] = 0; // Pure Gold
                } else {
                    fb[idx + 0] = 231; fb[idx + 1] = 76;  fb[idx + 2] = 60; // Crimson
                }
            } else {
                fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15; // Yellow Flag
            }
        }
    }

    // 4. Draw Smoke Puffs (Cloud Grey #BDC3C7, fading)
    for (int i = 0; i < MAX_SMOKES; ++i) {
        if (smokes_[i].active) {
            int idx = (smokes_[i].y * 16 + smokes_[i].x) * 3;
            fb[idx + 0] = 180; fb[idx + 1] = 190; fb[idx + 2] = 200;
        }
    }

    // 5. Draw Enemy Red Pursuit Cars (#E74C3C, or Purple Stunned #9B59B6)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));
        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            if (enemies_[i].stun_timer > 0.0f) {
                // Stunned spinning car
                fb[idx + 0] = 155; fb[idx + 1] = 89; fb[idx + 2] = 182; // Purple
            } else {
                fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;  // Hot Red
            }
        }
    }

    // 6. Draw Player Blue Rally Car (#3498DB)
    if (state_ != STATE_DEAD || (static_cast<int>(state_timer_ * 8.0f) % 2 == 0)) {
        int px = static_cast<int>(std::round(player_x_));
        int py = static_cast<int>(std::round(player_y_));
        if (px >= 0 && px < 16 && py >= 0 && py < 16) {
            int idx = (py * 16 + px) * 3;
            fb[idx + 0] = 52;  fb[idx + 1] = 152; fb[idx + 2] = 219; // Cyan Blue
        }
    }

    // 7. Victory or Game Over overlays
    if (state_ == STATE_VICTORY) {
        // Golden checkered border flash
        if (static_cast<int>(state_timer_ * 4.0f) % 2 == 0) {
            for (int x = 0; x < 16; ++x) {
                int top_idx = (1 * 16 + x) * 3;
                int btm_idx = (15 * 16 + x) * 3;
                fb[top_idx + 0] = 255; fb[top_idx + 1] = 215; fb[top_idx + 2] = 0;
                fb[btm_idx + 0] = 255; fb[btm_idx + 1] = 215; fb[btm_idx + 2] = 0;
            }
        }
    }
}

} // namespace arcade
