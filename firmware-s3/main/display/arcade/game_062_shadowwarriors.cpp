#include "game_062_shadowwarriors.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game062ShadowWarriors::Game062ShadowWarriors()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(4000),
      lives_(3),
      player_health_(100),
      enemies_defeated_(0),
      total_enemies_(5),
      player_x_(2.0f),
      player_y_(13.0f),
      player_vx_(0.0f),
      player_vy_(0.0f),
      player_facing_(1),
      is_slashing_(false),
      slash_timer_(0.0f),
      is_wall_clinging_(false),
      history_idx_(0),
      num_clones_(1),
      dog_active_(false),
      dog_x_(0.0f),
      dog_y_(13.0f),
      dog_vx_(0.0f),
      dog_timer_(0.0f) {
}

void Game062ShadowWarriors::Init() {
    Reset();
}

void Game062ShadowWarriors::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    player_health_ = 100;
    num_clones_ = 1; // Starts with 1 shadow clone!
    InitStage();
}

void Game062ShadowWarriors::InitStage() {
    player_x_ = 2.0f;
    player_y_ = 13.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;
    player_facing_ = 1;
    is_slashing_ = false;
    slash_timer_ = 0.0f;
    is_wall_clinging_ = false;

    for (int i = 0; i < HISTORY_LEN; ++i) {
        history_x_[i] = player_x_;
        history_y_[i] = player_y_;
        history_facing_[i] = player_facing_;
        history_slashing_[i] = false;
    }
    history_idx_ = 0;

    dog_active_ = false;
    dog_timer_ = 0.0f;
    fireball_.active = false;

    enemies_defeated_ = 0;
    enemies_[0] = {8.0f, 13.0f, -2.0f, 1, true};   // Foot soldier
    enemies_[1] = {12.0f, 13.0f, -1.8f, 1, true};  // Black ninja
    enemies_[2] = {9.0f, 7.0f, -1.2f, 1, true};    // Catwalk assassin
    enemies_[3] = {14.0f, 13.0f, -1.5f, 3, true};  // Shadow Master Boss
    total_enemies_ = 4;
}

void Game062ShadowWarriors::SummonDog() {
    if (!dog_active_) {
        dog_active_ = true;
        dog_x_ = player_x_;
        dog_y_ = 13.0f;
        dog_vx_ = player_facing_ * 12.0f;
        dog_timer_ = 3.0f;
    }
}

void Game062ShadowWarriors::AddShadowClone() {
    if (num_clones_ < MAX_CLONES) {
        num_clones_++;
    }
}

void Game062ShadowWarriors::TriggerFireDragon() {
    if (!fireball_.active) {
        fireball_.active = true;
        fireball_.x = player_x_ + player_facing_ * 1.0f;
        fireball_.y = player_y_ - 0.5f;
        fireball_.vx = player_facing_ * 8.0f;
        fireball_.vy = -10.0f;
    }
}

void Game062ShadowWarriors::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.8f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                player_health_ = 100;
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

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateClones();
    UpdateDog(dt);
    UpdateFireball(dt);
    UpdateEnemies(dt);
    CheckCollisions();

    // Check Victory
    if (enemies_defeated_ >= total_enemies_) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 1200;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game062ShadowWarriors::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (is_slashing_) {
        slash_timer_ -= dt;
        if (slash_timer_ <= 0.0f) {
            is_slashing_ = false;
        }
    }

    // Check wall clinging
    if ((player_x_ <= 1.0f && (buttons & BUTTON_LEFT)) ||
        (player_x_ >= 14.5f && (buttons & BUTTON_RIGHT))) {
        is_wall_clinging_ = true;
        player_vy_ = 0.0f;
        if (buttons & BUTTON_UP)   player_y_ -= 5.0f * dt;
        if (buttons & BUTTON_DOWN) player_y_ += 5.0f * dt;
    } else {
        is_wall_clinging_ = false;
    }

    // Horizontal movement
    if (!is_wall_clinging_) {
        float speed = 6.0f;
        player_vx_ = 0.0f;
        if (buttons & BUTTON_LEFT)  { player_vx_ = -speed; player_facing_ = -1; }
        if (buttons & BUTTON_RIGHT) { player_vx_ = speed;  player_facing_ = 1; }

        player_x_ += player_vx_ * dt;

        // Jump physics
        player_y_ += player_vy_ * dt;
        player_vy_ += 30.0f * dt; // Gravity
        if (player_y_ >= 13.0f) {
            player_y_ = 13.0f;
            player_vy_ = 0.0f;
        }

        // Jump trigger
        if ((buttons & BUTTON_UP) && !(prev_buttons & BUTTON_UP) && player_y_ >= 12.9f) {
            player_vy_ = -12.0f;
        }
    }

    player_x_ = std::max(1.0f, std::min(14.5f, player_x_));
    player_y_ = std::max(2.0f, std::min(13.0f, player_y_));

    // Attack trigger: Button A
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        is_slashing_ = true;
        slash_timer_ = 0.18f;

        // Player slash hits
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (!enemies_[i].active) continue;
            float dx = enemies_[i].x - player_x_;
            float dy = enemies_[i].y - player_y_;
            if (std::abs(dx) < 1.6f && std::abs(dy) < 1.2f && (dx * player_facing_ >= 0)) {
                enemies_[i].health -= 1;
                score_ += 100;
                if (enemies_[i].health <= 0) {
                    enemies_[i].active = false;
                    enemies_defeated_++;
                    score_ += 150;
                }
            }
        }
    }

    // Summon Dog trigger: Button B
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        SummonDog();
    }
}

void Game062ShadowWarriors::UpdateClones() {
    // Record current player frame into circular history buffer
    history_x_[history_idx_] = player_x_;
    history_y_[history_idx_] = player_y_;
    history_facing_[history_idx_] = player_facing_;
    history_slashing_[history_idx_] = is_slashing_;

    history_idx_ = (history_idx_ + 1) % HISTORY_LEN;

    // Trigger clone attack damage on enemies if clone was slashing
    for (int c = 1; c <= num_clones_; ++c) {
        int delay = c * 6; // 6 frames delay per clone
        int idx = (history_idx_ - delay + HISTORY_LEN) % HISTORY_LEN;

        if (history_slashing_[idx]) {
            float cx = history_x_[idx];
            float cy = history_y_[idx];
            int cf = history_facing_[idx];

            for (int i = 0; i < MAX_ENEMIES; ++i) {
                if (!enemies_[i].active) continue;
                float dx = enemies_[i].x - cx;
                float dy = enemies_[i].y - cy;
                if (std::abs(dx) < 1.6f && std::abs(dy) < 1.2f && (dx * cf >= 0)) {
                    enemies_[i].health -= 1;
                    score_ += 50;
                    if (enemies_[i].health <= 0) {
                        enemies_[i].active = false;
                        enemies_defeated_++;
                    }
                }
            }
        }
    }
}

void Game062ShadowWarriors::UpdateDog(float dt) {
    if (!dog_active_) return;

    dog_x_ += dog_vx_ * dt;
    dog_timer_ -= dt;

    if (dog_x_ < 0.0f || dog_x_ > 15.5f || dog_timer_ <= 0.0f) {
        dog_active_ = false;
        return;
    }

    // Dog pounce on enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        if (std::abs(dog_x_ - enemies_[i].x) < 1.3f && std::abs(dog_y_ - enemies_[i].y) < 1.2f) {
            enemies_[i].health -= 2;
            score_ += 150;
            if (enemies_[i].health <= 0) {
                enemies_[i].active = false;
                enemies_defeated_++;
            }
            break;
        }
    }
}

void Game062ShadowWarriors::UpdateFireball(float dt) {
    if (!fireball_.active) return;

    fireball_.x += fireball_.vx * dt;
    fireball_.y += fireball_.vy * dt;
    fireball_.vy += 22.0f * dt; // Gravity arc

    if (fireball_.x < 0.0f || fireball_.x > 16.0f || fireball_.y > 15.0f) {
        fireball_.active = false;
    }
}

void Game062ShadowWarriors::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        enemies_[i].x += enemies_[i].vx * dt;
        if (enemies_[i].x < 2.0f) {
            enemies_[i].x = 2.0f;
            enemies_[i].vx = std::abs(enemies_[i].vx);
        } else if (enemies_[i].x > 14.0f) {
            enemies_[i].x = 14.0f;
            enemies_[i].vx = -std::abs(enemies_[i].vx);
        }
    }
}

void Game062ShadowWarriors::CheckCollisions() {
    // Enemy contact with player
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        if (std::abs(enemies_[i].x - player_x_) < 0.8f &&
            std::abs(enemies_[i].y - player_y_) < 0.8f) {
            player_health_ -= 20;
            if (player_health_ <= 0) {
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game062ShadowWarriors::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Moonlight Ninja Fortress (Midnight blue sky & stone catacombs)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = 10;
            fb[idx + 1] = 15;
            fb[idx + 2] = 35; // Midnight blue

            // Upper Catwalk at y=8
            if (y == 8 && x >= 4 && x <= 12) {
                fb[idx] = 60;
                fb[idx + 1] = 60;
                fb[idx + 2] = 80;
            }

            // Ground floor at y=14
            if (y == 14) {
                fb[idx] = 50;
                fb[idx + 1] = 40;
                fb[idx + 2] = 40;
            }
        }
    }

    // Render Enemies (Purple & Red evil ninjas)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));
        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            if (i == 3) {
                fb[idx] = 255; fb[idx + 1] = 30; fb[idx + 2] = 30; // Boss crimson
            } else {
                fb[idx] = 160; fb[idx + 1] = 40; fb[idx + 2] = 180; // Violet ninja
            }
        }
    }

    // Render Shadow Clones (Translucent Red / Orange phantoms)
    for (int c = 1; c <= num_clones_; ++c) {
        int delay = c * 6;
        int idx_h = (history_idx_ - delay + HISTORY_LEN) % HISTORY_LEN;
        int cx = static_cast<int>(std::round(history_x_[idx_h]));
        int cy = static_cast<int>(std::round(history_y_[idx_h]));
        int cf = history_facing_[idx_h];

        if (cx >= 0 && cx < 16 && cy >= 0 && cy < 16) {
            int p_idx = (cy * 16 + cx) * 3;
            fb[p_idx] = 255;
            fb[p_idx + 1] = 60;
            fb[p_idx + 2] = 20; // Fiery phantom clone

            // Clone slash arc
            if (history_slashing_[idx_h]) {
                int csx = cx + cf;
                if (csx >= 0 && csx < 16) {
                    int s_idx = (cy * 16 + csx) * 3;
                    fb[s_idx] = 255;
                    fb[s_idx + 1] = 180;
                    fb[s_idx + 2] = 0;
                }
            }
        }
    }

    // Render Player (Hayabusa: Deep Cobalt suit)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx] = 30;
        fb[idx + 1] = 90;
        fb[idx + 2] = 240; // Cobalt blue

        if (is_slashing_) {
            int sx = px + player_facing_;
            if (sx >= 0 && sx < 16) {
                int s_idx = (py * 16 + sx) * 3;
                fb[s_idx] = 200;
                fb[s_idx + 1] = 240;
                fb[s_idx + 2] = 255; // White/Cyan sword arc
            }
        }
    }

    // Render Ninja Hound (Wolf grey sprinting dog)
    if (dog_active_) {
        int dx = static_cast<int>(std::round(dog_x_));
        int dy = static_cast<int>(std::round(dog_y_));
        if (dx >= 0 && dx < 16 && dy >= 0 && dy < 16) {
            int idx = (dy * 16 + dx) * 3;
            fb[idx] = 200;
            fb[idx + 1] = 200;
            fb[idx + 2] = 210; // Wolf silver
        }
    }

    // Top HUD: Health & Clone count
    int hp_bars = (player_health_ * 5) / 100;
    for (int h = 0; h < hp_bars && h < 5; ++h) {
        int idx = h * 3;
        fb[idx] = 0; fb[idx + 1] = 255; fb[idx + 2] = 0;
    }

    for (int c = 0; c < num_clones_; ++c) {
        int idx = (15 - c) * 3;
        fb[idx] = 255; fb[idx + 1] = 50; fb[idx + 2] = 0; // Clone orbs
    }
}

} // namespace arcade
