#include "game_064_inthehunt.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game064InTheHunt::Game064InTheHunt()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(4000),
      lives_(3),
      sub_x_(2.5f),
      sub_y_(8.0f),
      sub_facing_(1),
      shoot_cooldown_(0.0f),
      scroll_x_(0.0f),
      enemies_defeated_(0),
      boss_active_(false),
      boss_x_(13.0f),
      boss_y_(8.0f),
      boss_vy_(2.0f),
      boss_health_(10),
      boss_shoot_cooldown_(1.3f) {
}

void Game064InTheHunt::Init() {
    Reset();
}

void Game064InTheHunt::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game064InTheHunt::InitStage() {
    sub_x_ = 2.5f;
    sub_y_ = 8.0f;
    sub_facing_ = 1;
    shoot_cooldown_ = 0.0f;
    scroll_x_ = 0.0f;
    enemies_defeated_ = 0;
    boss_active_ = false;
    boss_x_ = 13.0f;
    boss_y_ = 8.0f;
    boss_vy_ = 2.0f;
    boss_health_ = 10;
    boss_shoot_cooldown_ = 1.3f;

    for (int i = 0; i < MAX_TORPEDOES; ++i) torpedoes_[i].active = false;
    for (int i = 0; i < MAX_MISSILES; ++i) missiles_[i].active = false;
    for (int i = 0; i < MAX_DEPTH_CHARGES; ++i) depth_charges_[i].active = false;

    // Surface gunboat (y=2.0), midget sub (y=7.0), sea mine (y=12.0)
    enemies_[0] = {14.0f, 2.0f, -1.8f, 0, 1, true, 2.0f};  // Surface Gunboat
    enemies_[1] = {15.0f, 7.0f, -2.0f, 1, 1, true, 2.2f};  // Enemy Sub
    enemies_[2] = {11.0f, 12.0f, -0.8f, 2, 1, true, 99.0f}; // Sea Mine
    enemies_[3] = {18.0f, 9.0f, -1.5f, 1, 1, true, 2.5f};  // Enemy Sub 2
}

void Game064InTheHunt::FireTorpedoes() {
    if (shoot_cooldown_ > 0.0f) return;

    // 1. Forward Torpedo
    for (int i = 0; i < MAX_TORPEDOES; ++i) {
        if (!torpedoes_[i].active) {
            torpedoes_[i].active = true;
            torpedoes_[i].x = sub_x_ + sub_facing_ * 1.0f;
            torpedoes_[i].y = sub_y_;
            torpedoes_[i].vx = sub_facing_ * 14.0f;
            torpedoes_[i].vy = 0.0f;
            torpedoes_[i].is_player = true;
            break;
        }
    }

    // 2. Surface Anti-Air Missile if near water surface (y <= 6.0)
    if (sub_y_ <= 6.0f) {
        for (int i = 0; i < MAX_MISSILES; ++i) {
            if (!missiles_[i].active) {
                missiles_[i].active = true;
                missiles_[i].x = sub_x_;
                missiles_[i].y = sub_y_ - 0.8f;
                missiles_[i].vx = sub_facing_ * 2.0f;
                missiles_[i].vy = -16.0f; // Roars upward out of water
                missiles_[i].is_player = true;
                break;
            }
        }
    }

    shoot_cooldown_ = 0.25f;
}

void Game064InTheHunt::DropDepthCharge() {
    for (int i = 0; i < MAX_DEPTH_CHARGES; ++i) {
        if (!depth_charges_[i].active) {
            depth_charges_[i].active = true;
            depth_charges_[i].x = sub_x_;
            depth_charges_[i].y = sub_y_ + 0.8f;
            depth_charges_[i].vx = sub_facing_ * 1.5f;
            depth_charges_[i].vy = 12.0f; // Sinks into seabed
            depth_charges_[i].is_player = true;
            break;
        }
    }
}

void Game064InTheHunt::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.8f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                InitStage();
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
            InitStage();
        }
        return;
    }

    if (shoot_cooldown_ > 0.0f) shoot_cooldown_ -= dt;

    UpdateSubmarine(dt, buttons, prev_buttons);
    UpdateProjectiles(dt);

    if (boss_active_) {
        UpdateBoss(dt);
    } else {
        UpdateEnemies(dt);
        if (enemies_defeated_ >= 5) {
            boss_active_ = true;
            boss_x_ = 13.0f;
            boss_y_ = 8.0f;
            for (int i = 0; i < MAX_ENEMIES; ++i) enemies_[i].active = false;
        }
    }

    CheckCollisions();
}

void Game064InTheHunt::UpdateSubmarine(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float speed = 6.0f;

    if (buttons & BUTTON_LEFT)  { sub_x_ -= speed * dt; sub_facing_ = -1; }
    if (buttons & BUTTON_RIGHT) { sub_x_ += speed * dt; sub_facing_ = 1; }
    if (buttons & BUTTON_UP)    sub_y_ -= speed * dt;
    if (buttons & BUTTON_DOWN)  sub_y_ += speed * dt;

    // Granvia submarine bounds (Surfaces at y=3.0, dives to seabed y=14.0)
    sub_x_ = std::max(1.0f, std::min(14.5f, sub_x_));
    sub_y_ = std::max(3.0f, std::min(14.0f, sub_y_));

    // Torpedo / Anti-air: Button A
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        FireTorpedoes();
    }

    // Depth charge: Button B
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        DropDepthCharge();
    }
}

void Game064InTheHunt::UpdateProjectiles(float dt) {
    // Torpedoes
    for (int i = 0; i < MAX_TORPEDOES; ++i) {
        if (!torpedoes_[i].active) continue;
        torpedoes_[i].x += torpedoes_[i].vx * dt;
        torpedoes_[i].y += torpedoes_[i].vy * dt;
        if (torpedoes_[i].x < 0.0f || torpedoes_[i].x > 15.5f) torpedoes_[i].active = false;
    }

    // Surface Missiles
    for (int i = 0; i < MAX_MISSILES; ++i) {
        if (!missiles_[i].active) continue;
        missiles_[i].x += missiles_[i].vx * dt;
        missiles_[i].y += missiles_[i].vy * dt;
        if (missiles_[i].y < 0.0f || missiles_[i].x < 0.0f || missiles_[i].x > 15.5f) {
            missiles_[i].active = false;
        }
    }

    // Depth Charges
    for (int i = 0; i < MAX_DEPTH_CHARGES; ++i) {
        if (!depth_charges_[i].active) continue;
        depth_charges_[i].x += depth_charges_[i].vx * dt;
        depth_charges_[i].y += depth_charges_[i].vy * dt;
        if (depth_charges_[i].y > 15.5f) depth_charges_[i].active = false;
    }
}

void Game064InTheHunt::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        enemies_[i].x += enemies_[i].vx * dt;

        // Sea mine vertical bobbing
        if (enemies_[i].type == 2) {
            enemies_[i].y += std::sin(state_timer_ * 3.0f) * 0.8f * dt;
        }

        // Loop / recycle
        if (enemies_[i].x < -1.5f) {
            enemies_[i].x = 17.0f + (i * 4.0f);
            enemies_[i].health = 1;
        }

        // Shooting
        enemies_[i].shoot_cooldown -= dt;
        if (enemies_[i].shoot_cooldown <= 0.0f && enemies_[i].x < 15.0f) {
            enemies_[i].shoot_cooldown = 2.0f;
            if (enemies_[i].type == 0) {
                // Gunboat drops depth charge downward
                for (int d = 0; d < MAX_DEPTH_CHARGES; ++d) {
                    if (!depth_charges_[d].active) {
                        depth_charges_[d].active = true;
                        depth_charges_[d].x = enemies_[i].x;
                        depth_charges_[d].y = enemies_[i].y + 1.0f;
                        depth_charges_[d].vx = 0.0f;
                        depth_charges_[d].vy = 8.0f;
                        depth_charges_[d].is_player = false;
                        break;
                    }
                }
            } else if (enemies_[i].type == 1) {
                // Enemy sub fires torpedo leftward
                for (int t = 0; t < MAX_TORPEDOES; ++t) {
                    if (!torpedoes_[t].active) {
                        torpedoes_[t].active = true;
                        torpedoes_[t].x = enemies_[i].x - 1.0f;
                        torpedoes_[t].y = enemies_[i].y;
                        torpedoes_[t].vx = -9.0f;
                        torpedoes_[t].vy = 0.0f;
                        torpedoes_[t].is_player = false;
                        break;
                    }
                }
            }
        }
    }
}

void Game064InTheHunt::UpdateBoss(float dt) {
    boss_y_ += boss_vy_ * dt;
    if (boss_y_ < 5.0f) {
        boss_y_ = 5.0f;
        boss_vy_ = std::abs(boss_vy_);
    } else if (boss_y_ > 12.0f) {
        boss_y_ = 12.0f;
        boss_vy_ = -std::abs(boss_vy_);
    }

    boss_shoot_cooldown_ -= dt;
    if (boss_shoot_cooldown_ <= 0.0f) {
        boss_shoot_cooldown_ = 1.4f;
        // Dual torpedo spread
        for (int dy = -1; dy <= 1; dy += 2) {
            for (int t = 0; t < MAX_TORPEDOES; ++t) {
                if (!torpedoes_[t].active) {
                    torpedoes_[t].active = true;
                    torpedoes_[t].x = boss_x_ - 1.5f;
                    torpedoes_[t].y = boss_y_ + dy * 1.0f;
                    torpedoes_[t].vx = -9.0f;
                    torpedoes_[t].vy = dy * 2.5f;
                    torpedoes_[t].is_player = false;
                    break;
                }
            }
        }
    }
}

void Game064InTheHunt::CheckCollisions() {
    // 1. Torpedoes vs Enemies & Boss
    for (int t = 0; t < MAX_TORPEDOES; ++t) {
        if (!torpedoes_[t].active || !torpedoes_[t].is_player) continue;

        if (boss_active_) {
            if (std::abs(torpedoes_[t].x - boss_x_) < 2.0f &&
                std::abs(torpedoes_[t].y - boss_y_) < 2.0f) {
                torpedoes_[t].active = false;
                boss_health_--;
                score_ += 50;
                if (boss_health_ <= 0) {
                    boss_active_ = false;
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 1500;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
            }
        } else {
            for (int e = 0; e < MAX_ENEMIES; ++e) {
                if (!enemies_[e].active) continue;
                if (std::abs(torpedoes_[t].x - enemies_[e].x) < 1.2f &&
                    std::abs(torpedoes_[t].y - enemies_[e].y) < 1.2f) {
                    torpedoes_[t].active = false;
                    enemies_[e].health--;
                    if (enemies_[e].health <= 0) {
                        enemies_[e].active = false;
                        enemies_defeated_++;
                        score_ += 150;
                    }
                    break;
                }
            }
        }
    }

    // 2. Anti-Air Missiles vs Surface Gunboats
    for (int m = 0; m < MAX_MISSILES; ++m) {
        if (!missiles_[m].active || !missiles_[m].is_player) continue;
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active || enemies_[e].type != 0) continue; // Surface boat only
            if (std::abs(missiles_[m].x - enemies_[e].x) < 1.3f &&
                std::abs(missiles_[m].y - enemies_[e].y) < 1.3f) {
                missiles_[m].active = false;
                enemies_[e].active = false;
                enemies_defeated_++;
                score_ += 250;
                break;
            }
        }
    }

    // 3. Depth Charges vs Sea Mines / Deep targets
    for (int d = 0; d < MAX_DEPTH_CHARGES; ++d) {
        if (!depth_charges_[d].active || !depth_charges_[d].is_player) continue;
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;
            if (std::abs(depth_charges_[d].x - enemies_[e].x) < 1.2f &&
                std::abs(depth_charges_[d].y - enemies_[e].y) < 1.2f) {
                depth_charges_[d].active = false;
                enemies_[e].active = false;
                enemies_defeated_++;
                score_ += 200;
                break;
            }
        }
    }

    // 4. Enemy projectiles hit player sub
    // Enemy torpedoes
    for (int t = 0; t < MAX_TORPEDOES; ++t) {
        if (!torpedoes_[t].active || torpedoes_[t].is_player) continue;
        if (std::abs(torpedoes_[t].x - sub_x_) < 0.9f &&
            std::abs(torpedoes_[t].y - sub_y_) < 0.9f) {
            torpedoes_[t].active = false;
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }

    // Enemy depth charges
    for (int d = 0; d < MAX_DEPTH_CHARGES; ++d) {
        if (!depth_charges_[d].active || depth_charges_[d].is_player) continue;
        if (std::abs(depth_charges_[d].x - sub_x_) < 0.9f &&
            std::abs(depth_charges_[d].y - sub_y_) < 0.9f) {
            depth_charges_[d].active = false;
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }

    // Direct collision with enemies / sea mines
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        if (std::abs(enemies_[e].x - sub_x_) < 0.9f &&
            std::abs(enemies_[e].y - sub_y_) < 0.9f) {
            enemies_[e].active = false;
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game064InTheHunt::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Sky y=0..2 (Smoky industrial sky)
    for (int y = 0; y < 3; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = 40; fb[idx + 1] = 50; fb[idx + 2] = 70;
        }
    }

    // Water Surface line at y=3 (Foamy cyan waves)
    for (int x = 0; x < 16; ++x) {
        int idx = (3 * 16 + x) * 3;
        fb[idx] = 80; fb[idx + 1] = 200; fb[idx + 2] = 240;
    }

    // Underwater deep ocean y=4..14 (Graduating deep teal/blue)
    for (int y = 4; y < 15; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = 10;
            fb[idx + 1] = 30 + (14 - y) * 4;
            fb[idx + 2] = 80 + (14 - y) * 6;
        }
    }

    // Seabed reef at y=15 (Dark volcanic rock)
    for (int x = 0; x < 16; ++x) {
        int idx = (15 * 16 + x) * 3;
        fb[idx] = 40; fb[idx + 1] = 30; fb[idx + 2] = 20;
    }

    // Render Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));
        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            if (enemies_[i].type == 0) {
                fb[idx] = 160; fb[idx + 1] = 50;  fb[idx + 2] = 40; // Gunboat
            } else if (enemies_[i].type == 1) {
                fb[idx] = 60;  fb[idx + 1] = 150; fb[idx + 2] = 60; // Enemy sub
            } else {
                fb[idx] = 220; fb[idx + 1] = 40;  fb[idx + 2] = 20; // Red spiked mine
            }
        }
    }

    // Render Boss (Mecha Kraken 3x3 fortress)
    if (boss_active_) {
        int bx = static_cast<int>(std::round(boss_x_));
        int by = static_cast<int>(std::round(boss_y_));
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dx = -1; dx <= 1; ++dx) {
                int px = bx + dx;
                int py = by + dy;
                if (px >= 0 && px < 16 && py >= 0 && py < 16) {
                    int idx = (py * 16 + px) * 3;
                    fb[idx] = 200; fb[idx + 1] = 30; fb[idx + 2] = 30; // Crimson Kraken
                }
            }
        }
    }

    // Render Torpedoes (Cyan streaks)
    for (int t = 0; t < MAX_TORPEDOES; ++t) {
        if (!torpedoes_[t].active) continue;
        int tx = static_cast<int>(std::round(torpedoes_[t].x));
        int ty = static_cast<int>(std::round(torpedoes_[t].y));
        if (tx >= 0 && tx < 16 && ty >= 0 && ty < 16) {
            int idx = (ty * 16 + tx) * 3;
            if (torpedoes_[t].is_player) {
                fb[idx] = 0; fb[idx + 1] = 255; fb[idx + 2] = 255;
            } else {
                fb[idx] = 255; fb[idx + 1] = 50; fb[idx + 2] = 50;
            }
        }
    }

    // Render Missiles (Yellow/Orange)
    for (int m = 0; m < MAX_MISSILES; ++m) {
        if (!missiles_[m].active) continue;
        int mx = static_cast<int>(std::round(missiles_[m].x));
        int my = static_cast<int>(std::round(missiles_[m].y));
        if (mx >= 0 && mx < 16 && my >= 0 && my < 16) {
            int idx = (my * 16 + mx) * 3;
            fb[idx] = 255; fb[idx + 1] = 200; fb[idx + 2] = 0;
        }
    }

    // Render Depth Charges (Grey bombs)
    for (int d = 0; d < MAX_DEPTH_CHARGES; ++d) {
        if (!depth_charges_[d].active) continue;
        int dx = static_cast<int>(std::round(depth_charges_[d].x));
        int dy = static_cast<int>(std::round(depth_charges_[d].y));
        if (dx >= 0 && dx < 16 && dy >= 0 && dy < 16) {
            int idx = (dy * 16 + dx) * 3;
            fb[idx] = 200; fb[idx + 1] = 200; fb[idx + 2] = 200;
        }
    }

    // Render Player Sub (Granvia: Steampunk Yellow & Grey)
    int px = static_cast<int>(std::round(sub_x_));
    int py = static_cast<int>(std::round(sub_y_));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx] = 255; fb[idx + 1] = 215; fb[idx + 2] = 0; // Gold chassis

        // Conning tower periscope
        if (py > 0) {
            int c_idx = ((py - 1) * 16 + px) * 3;
            fb[c_idx] = 180; fb[c_idx + 1] = 180; fb[c_idx + 2] = 190;
        }
    }

    // HUD: Lives on row 0
    for (int l = 0; l < lives_ && l < 3; ++l) {
        int idx = l * 3;
        fb[idx] = 0; fb[idx + 1] = 255; fb[idx + 2] = 0;
    }
}

} // namespace arcade
