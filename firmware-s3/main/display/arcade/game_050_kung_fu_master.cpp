#include "game_050_kung_fu_master.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

Game050KungFuMaster::Game050KungFuMaster()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      player_health_(100),
      enemies_defeated_(0),
      total_stage_enemies_(5),
      player_x_(2.0f),
      player_facing_(1),
      is_crouching_(false),
      is_jumping_(false),
      jump_y_offset_(0.0f),
      jump_vy_(0.0f),
      attack_stance_(0),
      attack_timer_(0.0f),
      attack_duration_(0.18f),
      num_gripping_(0),
      wiggle_counter_(0) {
}

void Game050KungFuMaster::Init() {
    Reset();
}

void Game050KungFuMaster::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    player_health_ = 100;
    enemies_defeated_ = 0;
    total_stage_enemies_ = 5;
    player_x_ = 2.0f;
    player_facing_ = 1;
    is_crouching_ = false;
    is_jumping_ = false;
    jump_y_offset_ = 0.0f;
    jump_vy_ = 0.0f;
    attack_stance_ = 0;
    attack_timer_ = 0.0f;
    num_gripping_ = 0;
    wiggle_counter_ = 0;

    for (int i = 0; i < MAX_DAGGERS; ++i) {
        daggers_[i].active = false;
    }

    InitFloor();
}

void Game050KungFuMaster::InitFloor() {
    // 2 Grippers from right flank
    enemies_[0] = {14.0f, TYPE_GRIPPER, -3.2f, 15, true, false, 0.0f};
    enemies_[1] = {11.0f, TYPE_GRIPPER, -3.0f, 15, true, false, 0.0f};
    // 1 Knife Thrower
    enemies_[2] = {15.0f, TYPE_KNIFE_THROWER, -2.0f, 20, true, false, 1.2f};
    // 1 Boss Staff Master
    enemies_[3] = {13.5f, TYPE_BOSS_STAFF, -1.8f, 60, false, false, 0.8f}; // Spawns after thugs
}

void Game050KungFuMaster::ExecutePunch() {
    if (attack_timer_ > 0.0f) return;
    attack_stance_ = 1; // Punch
    attack_timer_ = attack_duration_;
}

void Game050KungFuMaster::ExecuteKick() {
    if (attack_timer_ > 0.0f) return;
    if (is_jumping_) {
        attack_stance_ = 4; // Jump Kick
    } else if (is_crouching_) {
        attack_stance_ = 3; // Low Sweep
    } else {
        attack_stance_ = 2; // Mid Kick
    }
    attack_timer_ = attack_duration_;
}

void Game050KungFuMaster::ShakeOffGrippers() {
    wiggle_counter_++;
    if (wiggle_counter_ >= 3) {
        // Break free! All clinging thugs knocked away
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (enemies_[i].active && enemies_[i].is_gripping) {
                enemies_[i].active = false;
                enemies_defeated_++;
                score_ += 100;
            }
        }
        num_gripping_ = 0;
        wiggle_counter_ = 0;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game050KungFuMaster::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    const float walk_speed = 5.2f;

    // Continuous health drain if hugged by grippers
    if (num_gripping_ > 0) {
        player_health_ -= static_cast<int>(12.0f * num_gripping_ * dt);
        if (player_health_ <= 0) {
            player_health_ = 0;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }

        // Wiggle joystick to break free
        if ((buttons & (KEY_LEFT | KEY_RIGHT)) && !(prev_buttons & (KEY_LEFT | KEY_RIGHT))) {
            ShakeOffGrippers();
        }
        return; // Clamped by thugs, cannot walk
    }

    // Attack timer
    if (attack_timer_ > 0.0f) {
        attack_timer_ -= dt;
        if (attack_timer_ <= 0.0f) {
            attack_stance_ = 0;
        }
    }

    // Jump physics
    if (is_jumping_) {
        const float gravity = 22.0f;
        jump_vy_ -= gravity * dt;
        jump_y_offset_ += jump_vy_ * dt;

        if (jump_y_offset_ <= 0.0f) {
            jump_y_offset_ = 0.0f;
            jump_vy_ = 0.0f;
            is_jumping_ = false;
        }
    } else {
        // Jump start (KEY_UP)
        if ((buttons & KEY_UP) && !(prev_buttons & KEY_UP)) {
            is_jumping_ = true;
            jump_vy_ = 8.5f;
        }
    }

    // Crouch (KEY_DOWN when not jumping)
    if (!is_jumping_ && (buttons & KEY_DOWN)) {
        is_crouching_ = true;
    } else {
        is_crouching_ = false;
    }

    // Horizontal walk
    if (!is_crouching_ && attack_timer_ <= 0.0f) {
        float vx = 0.0f;
        if (buttons & KEY_LEFT) {
            vx = -walk_speed;
            player_facing_ = -1;
        }
        if (buttons & KEY_RIGHT) {
            vx = walk_speed;
            player_facing_ = 1;
        }

        player_x_ += vx * dt;
        player_x_ = std::max(0.5f, std::min(15.0f, player_x_));
    }

    // Attack triggers
    if ((buttons & KEY_A) && !(prev_buttons & KEY_A)) {
        ExecutePunch();
    } else if ((buttons & KEY_B) && !(prev_buttons & KEY_B)) {
        ExecuteKick();
    }
}

void Game050KungFuMaster::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (enemies_[i].is_gripping) {
            // Glued to player
            enemies_[i].x = player_x_ + (i == 0 ? 0.3f : -0.3f);
            continue;
        }

        enemies_[i].x += enemies_[i].vx * dt;

        // Turn around or wrap
        if (enemies_[i].x < 0.5f) {
            enemies_[i].x = 0.5f;
            enemies_[i].vx = -enemies_[i].vx;
        } else if (enemies_[i].x > 15.0f) {
            enemies_[i].x = 15.0f;
            enemies_[i].vx = -enemies_[i].vx;
        }

        // Knife thrower periodic dagger throw
        if (enemies_[i].type == TYPE_KNIFE_THROWER) {
            enemies_[i].attack_timer -= dt;
            if (enemies_[i].attack_timer <= 0.0f) {
                enemies_[i].attack_timer = 2.0f;
                // Throw dagger
                for (int d = 0; d < MAX_DAGGERS; ++d) {
                    if (!daggers_[d].active) {
                        daggers_[d].x = enemies_[i].x - 0.5f;
                        daggers_[d].y = 11.0f; // Waist height
                        daggers_[d].vx = -8.5f;
                        daggers_[d].active = true;
                        break;
                    }
                }
            }
        }

        // Gripper hug touch check
        if (enemies_[i].type == TYPE_GRIPPER) {
            if (fabsf(player_x_ - enemies_[i].x) <= 0.65f && !is_jumping_) {
                enemies_[i].is_gripping = true;
                num_gripping_++;
            }
        }

        // Boss staff attack
        if (enemies_[i].type == TYPE_BOSS_STAFF) {
            enemies_[i].attack_timer -= dt;
            if (enemies_[i].attack_timer <= 0.0f) {
                enemies_[i].attack_timer = 1.4f;
                if (fabsf(player_x_ - enemies_[i].x) <= 1.4f && !is_crouching_) {
                    player_health_ -= 20;
                    if (player_health_ <= 0) {
                        player_health_ = 0;
                        state_ = STATE_DEAD;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            }
        }
    }
}

void Game050KungFuMaster::UpdateDaggers(float dt) {
    for (int i = 0; i < MAX_DAGGERS; ++i) {
        if (!daggers_[i].active) continue;

        daggers_[i].x += daggers_[i].vx * dt;
        if (daggers_[i].x < 0.0f || daggers_[i].x > 16.0f) {
            daggers_[i].active = false;
        }
    }
}

void Game050KungFuMaster::CheckHitboxes() {
    // 1. Daggers vs Player
    for (int d = 0; d < MAX_DAGGERS; ++d) {
        if (!daggers_[d].active) continue;

        if (fabsf(daggers_[d].x - player_x_) <= 0.75f) {
            // Can jump over or duck under
            if (!is_jumping_ && !is_crouching_) {
                daggers_[d].active = false;
                player_health_ -= 15;
                if (player_health_ <= 0) {
                    player_health_ = 0;
                    state_ = STATE_DEAD;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }
    }

    // 2. Player Attack Hitbox vs Enemies & Daggers
    if (attack_stance_ == 0) return;

    float reach = (attack_stance_ == 2 || attack_stance_ == 4) ? 1.35f : 1.0f;
    int dmg = (attack_stance_ == 1) ? 15 : (attack_stance_ == 2 ? 20 : (attack_stance_ == 3 ? 25 : 30));

    // Mid-air dagger interception
    for (int d = 0; d < MAX_DAGGERS; ++d) {
        if (!daggers_[d].active) continue;

        float dx = daggers_[d].x - player_x_;
        if ((player_facing_ > 0 && dx >= 0.0f && dx <= reach) ||
            (player_facing_ < 0 && dx <= 0.0f && -dx <= reach)) {
            daggers_[d].active = false; // Intercepted and shattered!
            score_ += 100;
            if (score_ > high_score_) high_score_ = score_;
        }
    }

    // Strike enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active || enemies_[i].is_gripping) continue;

        float dx = enemies_[i].x - player_x_;
        bool in_front = (player_facing_ > 0 && dx >= 0.0f && dx <= reach) ||
                        (player_facing_ < 0 && dx <= 0.0f && -dx <= reach);

        if (in_front) {
            enemies_[i].health -= dmg;
            score_ += (attack_stance_ * 50);
            if (score_ > high_score_) high_score_ = score_;

            if (enemies_[i].health <= 0) {
                enemies_[i].active = false;
                enemies_defeated_++;

                // Spawn boss on 3rd defeated enemy
                if (enemies_defeated_ == 3 && !enemies_[3].active) {
                    enemies_[3].active = true;
                    enemies_[3].x = 14.5f;
                    enemies_[3].health = 60;
                }

                if (enemies_defeated_ >= total_stage_enemies_ || (enemies_[i].type == TYPE_BOSS_STAFF)) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 1000;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
            }
        }
    }
}

void Game050KungFuMaster::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DEAD) {
        if (state_timer_ >= 2.0f && (buttons & (KEY_A | KEY_B))) {
            Reset();
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
    UpdateDaggers(dt);
    CheckHitboxes();
}

void Game050KungFuMaster::Render(uint8_t* fb) {
    // 1. Pagoda Interior Pillars (Crimson & Gold #78281F / #B7950B)
    for (int y = 0; y < 8; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (x % 4 == 0) {
                fb[idx + 0] = 183; fb[idx + 1] = 149; fb[idx + 2] = 11; // Gold pillar
            } else {
                fb[idx + 0] = 60;  fb[idx + 1] = 15;  fb[idx + 2] = 15;  // Crimson Wall
            }
        }
    }

    // HUD Health Bar on row 0
    int hp_bars = (player_health_ * 7) / 100;
    for (int x = 0; x < 8; ++x) {
        int idx = (0 * 16 + x) * 3;
        if (x < hp_bars) {
            fb[idx + 0] = 46; fb[idx + 1] = 204; fb[idx + 2] = 113; // Green HP
        }
    }

    // 2. Dojo Wooden Floor (rows 8..15)
    for (int y = 8; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx + 0] = 110; fb[idx + 1] = 65; fb[idx + 2] = 25; // Polished Wood
        }
    }

    // 3. Render Daggers
    for (int d = 0; d < MAX_DAGGERS; ++d) {
        if (!daggers_[d].active) continue;

        int dx = static_cast<int>(std::round(daggers_[d].x));
        int dy = static_cast<int>(std::round(daggers_[d].y));
        if (dx >= 0 && dx < 16 && dy >= 0 && dy < 16) {
            int idx = (dy * 16 + dx) * 3;
            fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255; // Silver dagger
        }
    }

    // 4. Render Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = 11;
        if (ex >= 0 && ex < 16) {
            int idx = (ey * 16 + ex) * 3;
            if (enemies_[i].type == TYPE_GRIPPER) {
                fb[idx + 0] = 41;  fb[idx + 1] = 128; fb[idx + 2] = 185; // Blue Gripper
            } else if (enemies_[i].type == TYPE_KNIFE_THROWER) {
                fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15;  // Yellow Thrower
            } else {
                fb[idx + 0] = 155; fb[idx + 1] = 89;  fb[idx + 2] = 182; // Purple Boss
            }
        }
    }

    // 5. Render Player Thomas
    int px = static_cast<int>(std::round(player_x_));
    int py = 11 - static_cast<int>(std::round(jump_y_offset_));
    if (is_crouching_) py += 1;

    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        if (attack_stance_ != 0) {
            fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Strike Flash Red
        } else {
            fb[idx + 0] = 245; fb[idx + 1] = 245; fb[idx + 2] = 245; // White Gi
        }
    }
}

} // namespace arcade
