#include "game_039_legend_of_kage.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

Game039LegendOfKage::Game039LegendOfKage()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      lives_(3),
      enemies_defeated_(0),
      target_kills_(10),
      player_x_(8.0f),
      player_y_(13.0f),
      player_vx_(0.0f),
      player_vy_(0.0f),
      player_facing_(1),
      is_grounded_(true),
      slash_timer_(0.0f) {
}

void Game039LegendOfKage::Init() {
    Reset();
}

void Game039LegendOfKage::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    enemies_defeated_ = 0;
    target_kills_ = 10;
    player_x_ = 8.0f;
    player_y_ = 13.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;
    player_facing_ = 1;
    is_grounded_ = true;
    slash_timer_ = 0.0f;

    InitForest();

    for (int i = 0; i < MAX_SHURIKENS; ++i) shurikens_[i].active = false;
    for (int i = 0; i < MAX_ENEMY_PROJECTILES; ++i) enemy_bullets_[i].active = false;

    // Initialize 3 enemy ninjas
    enemies_[0] = {3.0f, 9.0f, 2.5f, 0.0f, false, true, 1.0f};
    enemies_[1] = {13.0f, 5.0f, -2.5f, 0.0f, true, true, 1.5f}; // Red ninja
    enemies_[2] = {8.0f, 2.0f, 2.0f, 0.0f, false, true, 2.0f};
}

void Game039LegendOfKage::InitForest() {
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            tree_map_[y][x] = 0;
        }
    }

    // Ground (Row 14..15)
    for (int x = 0; x < 16; ++x) {
        tree_map_[14][x] = 3;
        tree_map_[15][x] = 3;
    }

    // Tree Trunks at x = 3, 8, 13
    const int trunks[3] = {3, 8, 13};
    for (int t = 0; t < 3; ++t) {
        int tx = trunks[t];
        for (int y = 2; y <= 13; ++y) {
            tree_map_[y][tx] = 1;
        }
    }

    // Branch Platforms (y = 10, 6, 3)
    const int branch_y[3] = {10, 6, 3};
    for (int b = 0; b < 3; ++b) {
        int by = branch_y[b];
        for (int t = 0; t < 3; ++t) {
            int tx = trunks[t];
            tree_map_[by][tx - 1] = 2;
            tree_map_[by][tx] = 2;
            tree_map_[by][tx + 1] = 2;
        }
    }
}

void Game039LegendOfKage::ThrowShuriken() {
    for (int i = 0; i < MAX_SHURIKENS; ++i) {
        if (!shurikens_[i].active) {
            shurikens_[i].active = true;
            shurikens_[i].x = player_x_ + player_facing_ * 0.6f;
            shurikens_[i].y = player_y_;
            shurikens_[i].vx = player_facing_ * 14.0f;
            shurikens_[i].vy = 0.0f;
            break;
        }
    }
}

void Game039LegendOfKage::SlashSword() {
    slash_timer_ = 0.22f; // Active sword parrying arc
}

void Game039LegendOfKage::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    const float gravity = 20.0f;
    const float run_speed = 5.5f;

    // 1. Horizontal Motion
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
    // Screen clamp
    player_x_ = std::max(0.5f, std::min(14.5f, player_x_));

    // 2. Ninja Super Leap (KEY_UP or KEY_A while grounded)
    if ((buttons & KEY_UP) && !(prev_buttons & KEY_UP) && is_grounded_) {
        player_vy_ = -13.5f; // Super high treetop leap!
        is_grounded_ = false;
    }

    // 3. Attack Controls
    if ((buttons & KEY_A) && !(prev_buttons & KEY_A)) {
        ThrowShuriken();
    }
    if ((buttons & KEY_B) && !(prev_buttons & KEY_B)) {
        SlashSword();
    }
    if (slash_timer_ > 0.0f) {
        slash_timer_ -= dt;
    }

    // 4. Vertical Physics
    if (!is_grounded_) {
        player_vy_ += gravity * dt;
        player_y_ += player_vy_ * dt;

        // Check landing on branches or ground when falling
        if (player_vy_ >= 0.0f) {
            int check_y = static_cast<int>(std::round(player_y_ + 1.0f));
            int check_x = static_cast<int>(std::round(player_x_));

            if (check_y >= 0 && check_y < 16 && check_x >= 0 && check_x < 16) {
                uint8_t tile = tree_map_[check_y][check_x];
                if ((tile == 2 || tile == 3) && player_y_ <= static_cast<float>(check_y - 0.75f)) {
                    player_y_ = static_cast<float>(check_y - 1.0f);
                    player_vy_ = 0.0f;
                    is_grounded_ = true;
                }
            }
        }
    } else {
        // Grounded: check if still supported
        int check_y = static_cast<int>(std::round(player_y_ + 1.0f));
        int check_x = static_cast<int>(std::round(player_x_));
        if (check_y >= 0 && check_y < 16 && check_x >= 0 && check_x < 16) {
            uint8_t tile = tree_map_[check_y][check_x];
            if (tile != 2 && tile != 3) {
                is_grounded_ = false; // Step off branch
            }
        }
    }
}

void Game039LegendOfKage::UpdateProjectiles(float dt) {
    // Player shurikens
    for (int i = 0; i < MAX_SHURIKENS; ++i) {
        if (!shurikens_[i].active) continue;

        shurikens_[i].x += shurikens_[i].vx * dt;
        if (shurikens_[i].x < 0.0f || shurikens_[i].x > 15.5f) {
            shurikens_[i].active = false;
        }
    }

    // Enemy bullets / darts
    for (int i = 0; i < MAX_ENEMY_PROJECTILES; ++i) {
        if (!enemy_bullets_[i].active) continue;

        enemy_bullets_[i].x += enemy_bullets_[i].vx * dt;
        enemy_bullets_[i].y += enemy_bullets_[i].vy * dt;

        if (enemy_bullets_[i].x < 0.0f || enemy_bullets_[i].x > 15.5f ||
            enemy_bullets_[i].y > 15.0f) {
            enemy_bullets_[i].active = false;
        }
    }
}

void Game039LegendOfKage::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) {
            // Respawn
            enemies_[i].active = true;
            enemies_[i].x = (rand() % 2 == 0) ? 1.0f : 14.0f;
            int branch_choices[3] = {10, 6, 3};
            enemies_[i].y = static_cast<float>(branch_choices[rand() % 3] - 1);
            enemies_[i].vx = (enemies_[i].x < 8.0f) ? 2.5f : -2.5f;
            enemies_[i].is_red = (rand() % 3 == 0);
            enemies_[i].shoot_timer = 1.0f + static_cast<float>(rand() % 15) / 10.0f;
            continue;
        }

        enemies_[i].x += enemies_[i].vx * dt;
        if (enemies_[i].x <= 1.0f) {
            enemies_[i].x = 1.0f;
            enemies_[i].vx = -enemies_[i].vx;
        } else if (enemies_[i].x >= 14.0f) {
            enemies_[i].x = 14.0f;
            enemies_[i].vx = -enemies_[i].vx;
        }

        // Shoot dart towards Kage
        enemies_[i].shoot_timer -= dt;
        if (enemies_[i].shoot_timer <= 0.0f) {
            enemies_[i].shoot_timer = 2.0f;

            for (int b = 0; b < MAX_ENEMY_PROJECTILES; ++b) {
                if (!enemy_bullets_[b].active) {
                    enemy_bullets_[b].active = true;
                    enemy_bullets_[b].x = enemies_[i].x;
                    enemy_bullets_[b].y = enemies_[i].y;

                    float dx = player_x_ - enemies_[i].x;
                    float dy = player_y_ - enemies_[i].y;
                    float dist = sqrtf(dx * dx + dy * dy);
                    if (dist < 0.1f) dist = 0.1f;

                    float speed = 7.0f;
                    enemy_bullets_[b].vx = (dx / dist) * speed;
                    enemy_bullets_[b].vy = (dy / dist) * speed;
                    break;
                }
            }
        }
    }
}

void Game039LegendOfKage::CheckCollisions() {
    // 1. Shurikens hit Enemy Ninjas
    for (int s = 0; s < MAX_SHURIKENS; ++s) {
        if (!shurikens_[s].active) continue;

        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;

            float dist = fabsf(shurikens_[s].x - enemies_[e].x) + fabsf(shurikens_[s].y - enemies_[e].y);
            if (dist <= 1.1f) {
                shurikens_[s].active = false;
                enemies_[e].active = false;
                enemies_defeated_++;

                int pts = enemies_[e].is_red ? 300 : 100;
                score_ += pts;
                if (score_ > high_score_) high_score_ = score_;

                if (enemies_defeated_ >= target_kills_) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 1000;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
                break;
            }
        }
    }

    // 2. Kodachi Sword Slash hits nearby Enemy or Deflects Projectiles
    if (slash_timer_ > 0.0f) {
        // Deflect enemy bullets
        for (int b = 0; b < MAX_ENEMY_PROJECTILES; ++b) {
            if (!enemy_bullets_[b].active) continue;

            float dist = fabsf(player_x_ - enemy_bullets_[b].x) + fabsf(player_y_ - enemy_bullets_[b].y);
            if (dist <= 1.4f) {
                enemy_bullets_[b].active = false; // Deflected!
                score_ += 50; // Parry bonus
                if (score_ > high_score_) high_score_ = score_;
            }
        }

        // Melee slash enemies
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;

            float dist = fabsf(player_x_ - enemies_[e].x) + fabsf(player_y_ - enemies_[e].y);
            if (dist <= 1.35f) {
                enemies_[e].active = false;
                enemies_defeated_++;
                score_ += 200;
                if (score_ > high_score_) high_score_ = score_;

                if (enemies_defeated_ >= target_kills_) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 1000;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
            }
        }
    }

    // 3. Enemy bullets hit Kage
    for (int b = 0; b < MAX_ENEMY_PROJECTILES; ++b) {
        if (!enemy_bullets_[b].active) continue;

        float dist = fabsf(player_x_ - enemy_bullets_[b].x) + fabsf(player_y_ - enemy_bullets_[b].y);
        if (dist <= 0.75f) {
            enemy_bullets_[b].active = false;
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }

    // 4. Enemy body touch Kage
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;

        float dist = fabsf(player_x_ - enemies_[e].x) + fabsf(player_y_ - enemies_[e].y);
        if (dist <= 0.72f) {
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game039LegendOfKage::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
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
                player_x_ = 8.0f;
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
    UpdateProjectiles(dt);
    UpdateEnemies(dt);
    CheckCollisions();
}

void Game039LegendOfKage::Render(uint8_t* fb) {
    // Night Forest Sky: Deep Emerald Twilight (#051911)
    for (int i = 0; i < 256; ++i) {
        fb[i * 3 + 0] = 5;
        fb[i * 3 + 1] = 25;
        fb[i * 3 + 2] = 17;
    }

    // 1. Draw Forest (Ground, Tree Trunks, Branches)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            uint8_t tile = tree_map_[y][x];

            if (tile == 3) {
                // Ground
                fb[idx + 0] = 30; fb[idx + 1] = 70; fb[idx + 2] = 32;
            } else if (tile == 1) {
                // Tree Trunk (Wood Brown)
                fb[idx + 0] = 100; fb[idx + 1] = 60; fb[idx + 2] = 30;
            } else if (tile == 2) {
                // Foliage Branch (Lush Green)
                fb[idx + 0] = 46; fb[idx + 1] = 125; fb[idx + 2] = 50;
            }
        }
    }

    // 2. Draw Enemy Ninjas (Black/Blue or Crimson Red)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));

        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            if (enemies_[i].is_red) {
                fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Crimson Ninja
            } else {
                fb[idx + 0] = 52; fb[idx + 1] = 73; fb[idx + 2] = 94;  // Shadow Ninja
            }
        }
    }

    // 3. Draw Projectiles
    // Player Shurikens (Bright Silver-Cyan stars)
    for (int i = 0; i < MAX_SHURIKENS; ++i) {
        if (!shurikens_[i].active) continue;
        int sx = static_cast<int>(std::round(shurikens_[i].x));
        int sy = static_cast<int>(std::round(shurikens_[i].y));
        if (sx >= 0 && sx < 16 && sy >= 0 && sy < 16) {
            int idx = (sy * 16 + sx) * 3;
            fb[idx + 0] = 0; fb[idx + 1] = 255; fb[idx + 2] = 255;
        }
    }

    // Enemy Darts (Fiery Orange)
    for (int i = 0; i < MAX_ENEMY_PROJECTILES; ++i) {
        if (!enemy_bullets_[i].active) continue;
        int bx = static_cast<int>(std::round(enemy_bullets_[i].x));
        int by = static_cast<int>(std::round(enemy_bullets_[i].y));
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            fb[idx + 0] = 243; fb[idx + 1] = 156; fb[idx + 2] = 18;
        }
    }

    // 4. Draw Player Kage (Scarlet Red Shinobi Gi #E74C3C with White Headband)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));

    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Red ninja

        // Kodachi Sword Slash Arc (Glinting White blade)
        if (slash_timer_ > 0.0f) {
            int sword_x = px + player_facing_;
            if (sword_x >= 0 && sword_x < 16) {
                int s_idx = (py * 16 + sword_x) * 3;
                fb[s_idx + 0] = 255; fb[s_idx + 1] = 255; fb[s_idx + 2] = 255;
            }
        }
    }

    // 5. HUD: Lives on top row
    for (int l = 0; l < lives_ && l < 3; ++l) {
        int idx = (0 * 16 + l) * 3;
        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
    }
}

} // namespace arcade
