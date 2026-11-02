#include "game_047_double_dragon.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

Game047DoubleDragon::Game047DoubleDragon()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      player_health_(100),
      enemies_defeated_(0),
      total_wave_enemies_(4),
      player_x_(2.0f),
      player_y_(11.0f),
      player_facing_(1),
      has_weapon_(false),
      attack_type_(0),
      attack_timer_(0.0f),
      attack_duration_(0.22f) {
}

void Game047DoubleDragon::Init() {
    Reset();
}

void Game047DoubleDragon::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    player_health_ = 100;
    enemies_defeated_ = 0;
    total_wave_enemies_ = 4;
    player_x_ = 2.0f;
    player_y_ = 11.0f;
    player_facing_ = 1;
    has_weapon_ = false;
    attack_type_ = 0;
    attack_timer_ = 0.0f;

    weapon_ = {7.0f, 10.0f, true}; // Initial iron bat on ground

    InitArena();
}

void Game047DoubleDragon::InitArena() {
    // Spawn thugs
    enemies_[0] = {13.0f, 10.0f, 0.0f, 0.0f, 30, true, false, 0.0f, 0.8f, false};
    enemies_[1] = {14.0f, 12.0f, 0.0f, 0.0f, 30, true, false, 0.0f, 1.2f, false};
    enemies_[2] = {11.0f, 9.0f, 0.0f, 0.0f, 30, true, false, 0.0f, 1.6f, false};
}

int Game047DoubleDragon::GetEnemiesRemaining() const {
    return total_wave_enemies_ - enemies_defeated_;
}

void Game047DoubleDragon::AttackPunch() {
    if (attack_timer_ > 0.0f) return;
    attack_type_ = 1;
    attack_timer_ = attack_duration_;
}

void Game047DoubleDragon::AttackKick() {
    if (attack_timer_ > 0.0f) return;
    attack_type_ = 2;
    attack_timer_ = attack_duration_ + 0.05f;
}

void Game047DoubleDragon::AttackElbow() {
    if (attack_timer_ > 0.0f) return;
    attack_type_ = 3;
    attack_timer_ = attack_duration_ + 0.1f;
}

void Game047DoubleDragon::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    const float walk_speed = 5.2f;

    // Attack cooldown
    if (attack_timer_ > 0.0f) {
        attack_timer_ -= dt;
        if (attack_timer_ <= 0.0f) {
            attack_type_ = 0;
        }
    }

    // Walking controls
    if (attack_timer_ <= 0.0f) {
        float vx = 0.0f;
        float vy = 0.0f;

        if (buttons & KEY_LEFT) {
            vx = -walk_speed;
            player_facing_ = -1;
        }
        if (buttons & KEY_RIGHT) {
            vx = walk_speed;
            player_facing_ = 1;
        }
        if (buttons & KEY_UP)    vy = -walk_speed * 0.75f;
        if (buttons & KEY_DOWN)  vy = walk_speed * 0.75f;

        player_x_ += vx * dt;
        player_y_ += vy * dt;

        // Street arena boundary constraints
        player_x_ = std::max(0.5f, std::min(15.0f, player_x_));
        player_y_ = std::max(8.0f, std::min(14.0f, player_y_));

        // Attack Buttons
        if ((buttons & KEY_A) && (buttons & KEY_B)) {
            AttackElbow();
        } else if ((buttons & KEY_A) && !(prev_buttons & KEY_A)) {
            AttackPunch();
        } else if ((buttons & KEY_B) && !(prev_buttons & KEY_B)) {
            AttackKick();
        }

        // Weapon Pickup
        if (weapon_.on_ground) {
            float dist = fabsf(player_x_ - weapon_.x) + fabsf(player_y_ - weapon_.y);
            if (dist <= 0.85f) {
                has_weapon_ = true;
                weapon_.on_ground = false;
                score_ += 50;
                if (score_ > high_score_) high_score_ = score_;
            }
        }
    }
}

void Game047DoubleDragon::UpdateEnemies(float dt) {
    const float enemy_speed = 2.6f;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (enemies_[i].is_knocked_down) {
            enemies_[i].knockdown_timer -= dt;
            if (enemies_[i].knockdown_timer <= 0.0f) {
                enemies_[i].is_knocked_down = false;
            }
            continue; // Cannot move while down
        }

        // Approach player
        float dx = player_x_ - enemies_[i].x;
        float dy = player_y_ - enemies_[i].y;

        if (fabsf(dx) > 0.8f) {
            enemies_[i].x += (dx > 0 ? enemy_speed : -enemy_speed) * dt;
        }
        if (fabsf(dy) > 0.4f) {
            enemies_[i].y += (dy > 0 ? enemy_speed * 0.6f : -enemy_speed * 0.6f) * dt;
        }

        // Keep within street arena
        enemies_[i].x = std::max(0.5f, std::min(15.0f, enemies_[i].x));
        enemies_[i].y = std::max(8.0f, std::min(14.0f, enemies_[i].y));

        // Attack cooldown
        if (enemies_[i].attack_cooldown > 0.0f) {
            enemies_[i].attack_cooldown -= dt;
        } else {
            // Thug strike check
            if (fabsf(dx) <= 1.0f && fabsf(dy) <= 0.5f) {
                player_health_ -= 10;
                enemies_[i].attack_cooldown = 1.2f;

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

void Game047DoubleDragon::CheckHitboxes() {
    if (attack_type_ == 0) return;

    float range_x = has_weapon_ ? 1.6f : 1.2f;
    float range_y = 0.65f;
    int dmg = (attack_type_ == 1) ? (has_weapon_ ? 25 : 12)
            : (attack_type_ == 2) ? 18
            : 35; // Elbow

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active || enemies_[i].is_knocked_down) continue;

        float dx = enemies_[i].x - player_x_;
        float dy = fabsf(enemies_[i].y - player_y_);

        // Must be in front of player
        bool in_front = (player_facing_ > 0 && dx >= 0.0f && dx <= range_x) ||
                        (player_facing_ < 0 && dx <= 0.0f && -dx <= range_x);

        if (in_front && dy <= range_y) {
            enemies_[i].health -= dmg;
            score_ += dmg * 5;
            if (score_ > high_score_) high_score_ = score_;

            // Knockback
            enemies_[i].x += player_facing_ * 1.2f;

            if (enemies_[i].health <= 0) {
                enemies_[i].active = false;
                enemies_defeated_++;

                if (enemies_defeated_ >= total_wave_enemies_) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 1000;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
            } else if (attack_type_ >= 2 || enemies_[i].health <= 15) {
                // Knockdown on kick/elbow
                enemies_[i].is_knocked_down = true;
                enemies_[i].knockdown_timer = 1.4f;
            }
        }
    }
}

void Game047DoubleDragon::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
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
    CheckHitboxes();
}

void Game047DoubleDragon::Render(uint8_t* fb) {
    // 1. Slum City Brick Wall Background (rows 0..7)
    for (int y = 0; y < 8; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            // Dark Brown Brick Wall
            fb[idx + 0] = 50;
            fb[idx + 1] = 20;
            fb[idx + 2] = 20;
        }
    }

    // Top Row HUD: Player Health Bar (x: 0..7)
    int hp_bars = (player_health_ * 7) / 100;
    for (int x = 0; x < 8; ++x) {
        int idx = (0 * 16 + x) * 3;
        if (x < hp_bars) {
            fb[idx + 0] = 46; fb[idx + 1] = 204; fb[idx + 2] = 113; // Green HP
        }
    }

    // 2. Street Asphalt Ground (rows 8..15)
    for (int y = 8; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx + 0] = 30;
            fb[idx + 1] = 35;
            fb[idx + 2] = 40; // Asphalt Slate
        }
    }

    // 3. Dropped Weapon (Iron Bat)
    if (weapon_.on_ground) {
        int wx = static_cast<int>(std::round(weapon_.x));
        int wy = static_cast<int>(std::round(weapon_.y));
        if (wx >= 0 && wx < 16 && wy >= 0 && wy < 16) {
            int idx = (wy * 16 + wx) * 3;
            fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15; // Golden Bat
        }
    }

    // 4. Render Enemies (Thugs)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));

        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            if (enemies_[i].is_knocked_down) {
                fb[idx + 0] = 180; fb[idx + 1] = 100; fb[idx + 2] = 80; // Grounded Brown
            } else {
                fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Crimson Thug
            }
        }
    }

    // 5. Render Player Billy Lee (Cobalt Blue #2980B9)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        if (attack_type_ != 0) {
            fb[idx + 0] = 243; fb[idx + 1] = 156; fb[idx + 2] = 18; // Flash Attack Yellow
        } else {
            fb[idx + 0] = 41;  fb[idx + 1] = 128; fb[idx + 2] = 185; // Billy Lee Blue
        }
    }
}

} // namespace arcade
