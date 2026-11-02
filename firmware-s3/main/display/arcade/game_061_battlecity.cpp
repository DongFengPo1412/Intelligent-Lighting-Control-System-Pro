#include "game_061_battlecity.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game061BattleCity::Game061BattleCity()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(4000),
      lives_(3),
      player_x_(4.0f),
      player_y_(14.0f),
      player_dir_(0),
      tank_tier_(1),
      shoot_cooldown_(0.0f),
      eagle_alive_(true),
      shovel_timer_(0.0f),
      enemies_defeated_(0),
      total_enemies_spawn_(6),
      enemy_spawn_timer_(0.0f) {
}

void Game061BattleCity::Init() {
    Reset();
}

void Game061BattleCity::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    eagle_alive_ = true;
    shovel_timer_ = 0.0f;
    tank_tier_ = 1;
    enemies_defeated_ = 0;
    total_enemies_spawn_ = 6;
    InitMap();
}

void Game061BattleCity::InitMap() {
    std::memset(map_, TILE_EMPTY, sizeof(map_));

    // Eagle Headquarters at (7, 14) and (8, 14)
    map_[14][7] = TILE_EAGLE;
    map_[14][8] = TILE_EAGLE;

    // Brick perimeter around Eagle
    map_[14][6] = TILE_BRICK;
    map_[13][6] = TILE_BRICK;
    map_[13][7] = TILE_BRICK;
    map_[13][8] = TILE_BRICK;
    map_[13][9] = TILE_BRICK;
    map_[14][9] = TILE_BRICK;

    // Strategic brick corridors & steel posts
    for (int y = 3; y <= 10; y += 2) {
        for (int x = 2; x <= 13; x += 3) {
            map_[y][x] = TILE_BRICK;
            map_[y + 1][x] = TILE_BRICK;
        }
    }

    // Steel armor center barrier
    map_[7][7] = TILE_STEEL;
    map_[7][8] = TILE_STEEL;

    // Water river moat
    map_[5][0] = TILE_WATER;
    map_[5][1] = TILE_WATER;
    map_[5][14] = TILE_WATER;
    map_[5][15] = TILE_WATER;

    // Forest camouflage
    map_[9][3] = TILE_FOREST;
    map_[9][12] = TILE_FOREST;

    // Player position
    player_x_ = 4.0f;
    player_y_ = 14.0f;
    player_dir_ = 0; // Up
    shoot_cooldown_ = 0.0f;

    for (int i = 0; i < MAX_SHELLS; ++i) shells_[i].active = false;

    // Initialize initial wave of 3 enemy tanks
    enemies_[0] = {1.0f, 1.0f, 2, 1, 0, true, 1.5f, 0.0f};   // Basic tank
    enemies_[1] = {7.0f, 1.0f, 2, 1, 1, true, 2.0f, 0.0f};   // Fast scout
    enemies_[2] = {14.0f, 1.0f, 2, 2, 2, true, 1.8f, 0.0f};  // Heavy armor tank
}

void Game061BattleCity::TriggerShovelReinforce() {
    shovel_timer_ = 8.0f;
    map_[14][6] = TILE_STEEL;
    map_[13][6] = TILE_STEEL;
    map_[13][7] = TILE_STEEL;
    map_[13][8] = TILE_STEEL;
    map_[13][9] = TILE_STEEL;
    map_[14][9] = TILE_STEEL;
}

void Game061BattleCity::DestroyEagle() {
    eagle_alive_ = false;
    map_[14][7] = TILE_EAGLE_DEAD;
    map_[14][8] = TILE_EAGLE_DEAD;
    state_ = STATE_DEAD;
    state_timer_ = 0.0f;
}

bool Game061BattleCity::CanMoveTo(float x, float y) const {
    if (x < 0.2f || x > 14.8f || y < 0.2f || y > 14.8f) return false;

    int gx1 = static_cast<int>(std::floor(x));
    int gy1 = static_cast<int>(std::floor(y));
    int gx2 = static_cast<int>(std::floor(x + 0.8f));
    int gy2 = static_cast<int>(std::floor(y + 0.8f));

    for (int gy = gy1; gy <= gy2; ++gy) {
        for (int gx = gx1; gx <= gx2; ++gx) {
            if (gx >= 0 && gx < 16 && gy >= 0 && gy < 16) {
                uint8_t tile = map_[gy][gx];
                if (tile == TILE_BRICK || tile == TILE_STEEL ||
                    tile == TILE_WATER || tile == TILE_EAGLE || tile == TILE_EAGLE_DEAD) {
                    return false;
                }
            }
        }
    }
    return true;
}

void Game061BattleCity::ShootShell() {
    if (shoot_cooldown_ > 0.0f) return;

    for (int i = 0; i < MAX_SHELLS; ++i) {
        if (!shells_[i].active) {
            shells_[i].active = true;
            shells_[i].is_player = true;

            float speed = (tank_tier_ >= 2) ? 18.0f : 14.0f;
            shells_[i].x = player_x_ + 0.4f;
            shells_[i].y = player_y_ + 0.4f;

            if (player_dir_ == 0) { shells_[i].vx = 0.0f; shells_[i].vy = -speed; }
            else if (player_dir_ == 1) { shells_[i].vx = speed; shells_[i].vy = 0.0f; }
            else if (player_dir_ == 2) { shells_[i].vx = 0.0f; shells_[i].vy = speed; }
            else { shells_[i].vx = -speed; shells_[i].vy = 0.0f; }

            shoot_cooldown_ = (tank_tier_ >= 3) ? 0.2f : 0.35f;
            break;
        }
    }
}

void Game061BattleCity::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 2.0f) {
            if (lives_ > 0 && eagle_alive_) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                player_x_ = 4.0f;
                player_y_ = 14.0f;
            } else {
                state_ = STATE_START;
            }
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f) {
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            Reset();
        }
        return;
    }

    // Shovel timer countdown
    if (shovel_timer_ > 0.0f) {
        shovel_timer_ -= dt;
        if (shovel_timer_ <= 0.0f) {
            // Revert perimeter to brick
            map_[14][6] = TILE_BRICK;
            map_[13][6] = TILE_BRICK;
            map_[13][7] = TILE_BRICK;
            map_[13][8] = TILE_BRICK;
            map_[13][9] = TILE_BRICK;
            map_[14][9] = TILE_BRICK;
        }
    }

    if (shoot_cooldown_ > 0.0f) shoot_cooldown_ -= dt;

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateEnemies(dt);
    UpdateShells(dt);
    CheckCollisions();

    // Check Victory
    if (enemies_defeated_ >= total_enemies_spawn_) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 1500;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game061BattleCity::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float speed = (tank_tier_ >= 2) ? 6.5f : 5.0f;
    float next_x = player_x_;
    float next_y = player_y_;

    if (buttons & BUTTON_UP) {
        player_dir_ = 0;
        next_y -= speed * dt;
    } else if (buttons & BUTTON_DOWN) {
        player_dir_ = 2;
        next_y += speed * dt;
    } else if (buttons & BUTTON_LEFT) {
        player_dir_ = 3;
        next_x -= speed * dt;
    } else if (buttons & BUTTON_RIGHT) {
        player_dir_ = 1;
        next_x += speed * dt;
    }

    if (CanMoveTo(next_x, next_y)) {
        player_x_ = next_x;
        player_y_ = next_y;
    }

    // Fire Button A
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        ShootShell();
    }
}

void Game061BattleCity::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        enemies_[i].move_timer += dt;
        if (enemies_[i].move_timer >= 1.2f) {
            enemies_[i].move_timer = 0.0f;
            // Bias toward eagle at (7, 14)
            if (enemies_[i].y < 12.0f && (i % 2 == 0)) {
                enemies_[i].dir = 2; // Down
            } else {
                enemies_[i].dir = (enemies_[i].x < 7.0f) ? 1 : ((enemies_[i].x > 8.0f) ? 3 : 2);
            }
        }

        float speed = (enemies_[i].type == 1) ? 4.5f : 3.0f;
        float nx = enemies_[i].x;
        float ny = enemies_[i].y;

        if (enemies_[i].dir == 0) ny -= speed * dt;
        else if (enemies_[i].dir == 1) nx += speed * dt;
        else if (enemies_[i].dir == 2) ny += speed * dt;
        else nx -= speed * dt;

        if (CanMoveTo(nx, ny)) {
            enemies_[i].x = nx;
            enemies_[i].y = ny;
        } else {
            enemies_[i].dir = (enemies_[i].dir + 1) % 4; // Turn when blocked
        }

        // Enemy shooting
        enemies_[i].shoot_cooldown -= dt;
        if (enemies_[i].shoot_cooldown <= 0.0f) {
            enemies_[i].shoot_cooldown = 1.8f;
            for (int s = 0; s < MAX_SHELLS; ++s) {
                if (!shells_[s].active) {
                    shells_[s].active = true;
                    shells_[s].is_player = false;
                    shells_[s].x = enemies_[i].x + 0.4f;
                    shells_[s].y = enemies_[i].y + 0.4f;
                    float sh_spd = 12.0f;
                    if (enemies_[i].dir == 0) { shells_[s].vx = 0.0f; shells_[s].vy = -sh_spd; }
                    else if (enemies_[i].dir == 1) { shells_[s].vx = sh_spd; shells_[s].vy = 0.0f; }
                    else if (enemies_[i].dir == 2) { shells_[s].vx = 0.0f; shells_[s].vy = sh_spd; }
                    else { shells_[s].vx = -sh_spd; shells_[s].vy = 0.0f; }
                    break;
                }
            }
        }
    }
}

void Game061BattleCity::UpdateShells(float dt) {
    for (int i = 0; i < MAX_SHELLS; ++i) {
        if (!shells_[i].active) continue;

        shells_[i].x += shells_[i].vx * dt;
        shells_[i].y += shells_[i].vy * dt;

        if (shells_[i].x < 0.0f || shells_[i].x > 15.5f ||
            shells_[i].y < 0.0f || shells_[i].y > 15.5f) {
            shells_[i].active = false;
        }
    }
}

void Game061BattleCity::CheckCollisions() {
    for (int s = 0; s < MAX_SHELLS; ++s) {
        if (!shells_[s].active) continue;

        int gx = static_cast<int>(std::floor(shells_[s].x));
        int gy = static_cast<int>(std::floor(shells_[s].y));

        // Tile collision
        if (gx >= 0 && gx < 16 && gy >= 0 && gy < 16) {
            uint8_t tile = map_[gy][gx];
            if (tile == TILE_BRICK) {
                map_[gy][gx] = TILE_EMPTY; // Brick destroyed
                shells_[s].active = false;
                score_ += 10;
                continue;
            } else if (tile == TILE_STEEL) {
                shells_[s].active = false; // Steel ricochets normal shell
                if (shells_[s].is_player && tank_tier_ >= 3) {
                    map_[gy][gx] = TILE_EMPTY; // Tier 3 tank chips steel
                }
                continue;
            } else if (tile == TILE_EAGLE) {
                shells_[s].active = false;
                DestroyEagle();
                return;
            }
        }

        // Shell vs Shell collision
        for (int o = s + 1; o < MAX_SHELLS; ++o) {
            if (!shells_[o].active) continue;
            if (std::abs(shells_[s].x - shells_[o].x) < 0.8f &&
                std::abs(shells_[s].y - shells_[o].y) < 0.8f) {
                shells_[s].active = false;
                shells_[o].active = false;
                break;
            }
        }
        if (!shells_[s].active) continue;

        // Player shell vs Enemy tanks
        if (shells_[s].is_player) {
            for (int e = 0; e < MAX_ENEMIES; ++e) {
                if (!enemies_[e].active) continue;
                if (std::abs(shells_[s].x - enemies_[e].x) < 0.9f &&
                    std::abs(shells_[s].y - enemies_[e].y) < 0.9f) {
                    shells_[s].active = false;
                    enemies_[e].health--;
                    if (enemies_[e].health <= 0) {
                        enemies_[e].active = false;
                        enemies_defeated_++;
                        score_ += (enemies_[e].type == 2 ? 300 : 150);

                        // Respawn new enemy if quota remaining
                        if (enemies_defeated_ + MAX_ENEMIES <= total_enemies_spawn_) {
                            enemies_[e] = {7.0f, 1.0f, 2, 1, 0, true, 1.5f, 0.0f};
                        }
                    }
                    break;
                }
            }
        } else {
            // Enemy shell vs Player
            if (std::abs(shells_[s].x - player_x_) < 0.9f &&
                std::abs(shells_[s].y - player_y_) < 0.9f) {
                shells_[s].active = false;
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game061BattleCity::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Map tiles
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            uint8_t tile = map_[y][x];

            if (tile == TILE_BRICK) {
                fb[idx] = 180;
                fb[idx + 1] = 60;
                fb[idx + 2] = 30; // Brick red
            } else if (tile == TILE_STEEL) {
                fb[idx] = 220;
                fb[idx + 1] = 220;
                fb[idx + 2] = 230; // Steel grey
            } else if (tile == TILE_WATER) {
                fb[idx] = 20;
                fb[idx + 1] = 80;
                fb[idx + 2] = 220; // Water blue
            } else if (tile == TILE_FOREST) {
                fb[idx] = 20;
                fb[idx + 1] = 160;
                fb[idx + 2] = 30; // Camouflage forest
            } else if (tile == TILE_EAGLE) {
                fb[idx] = 255;
                fb[idx + 1] = 215;
                fb[idx + 2] = 0; // Golden Eagle
            } else if (tile == TILE_EAGLE_DEAD) {
                fb[idx] = 80;
                fb[idx + 1] = 80;
                fb[idx + 2] = 80; // Destroyed eagle ruins
            }
        }
    }

    // Shells
    for (int i = 0; i < MAX_SHELLS; ++i) {
        if (!shells_[i].active) continue;
        int sx = static_cast<int>(std::round(shells_[i].x));
        int sy = static_cast<int>(std::round(shells_[i].y));
        if (sx >= 0 && sx < 16 && sy >= 0 && sy < 16) {
            int idx = (sy * 16 + sx) * 3;
            fb[idx] = 255;
            fb[idx + 1] = 255;
            fb[idx + 2] = 255; // White shell tracer
        }
    }

    // Enemy Tanks (Silver & Red camo)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));
        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            if (enemies_[i].type == 2) {
                fb[idx] = 200; fb[idx + 1] = 20;  fb[idx + 2] = 20; // Red heavy tank
            } else if (enemies_[i].type == 1) {
                fb[idx] = 255; fb[idx + 1] = 140; fb[idx + 2] = 0; // Orange scout
            } else {
                fb[idx] = 180; fb[idx + 1] = 180; fb[idx + 2] = 180; // Silver basic
            }
        }
    }

    // Player Tank (Bright Yellow / Gold Tank)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx] = 255;
        fb[idx + 1] = 200;
        fb[idx + 2] = 0; // Gold tank chassis

        // Gun barrel pixel
        int bx = px, by = py;
        if (player_dir_ == 0) by--;
        else if (player_dir_ == 1) bx++;
        else if (player_dir_ == 2) by++;
        else bx--;

        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int b_idx = (by * 16 + bx) * 3;
            fb[b_idx] = 255;
            fb[b_idx + 1] = 240;
            fb[b_idx + 2] = 100;
        }
    }

    // HUD: Lives & Enemies remaining on row 0
    for (int l = 0; l < lives_ && l < 3; ++l) {
        int idx = l * 3;
        fb[idx] = 0; fb[idx + 1] = 255; fb[idx + 2] = 0;
    }

    int rem = GetEnemiesRemaining();
    for (int r = 0; r < rem && r < 6; ++r) {
        int idx = (15 - r) * 3;
        fb[idx] = 255; fb[idx + 1] = 50; fb[idx + 2] = 50;
    }
}

} // namespace arcade
