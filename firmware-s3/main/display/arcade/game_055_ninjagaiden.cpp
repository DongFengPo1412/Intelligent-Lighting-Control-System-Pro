#include "game_055_ninjagaiden.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game055NinjaGaiden::Game055NinjaGaiden()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(3500),
      lives_(3),
      player_health_(100),
      enemies_defeated_(0),
      total_enemies_(4),
      player_x_(2.0f),
      player_y_(13.0f),
      player_vx_(0.0f),
      player_vy_(0.0f),
      player_facing_(1),
      action_(ACTION_IDLE),
      action_timer_(0.0f),
      is_hanging_bar_(false),
      swing_timer_(0.0f),
      swing_angle_(0.0f),
      crate_x_(6.0f),
      crate_y_(13.0f),
      crate_vx_(0.0f),
      is_carrying_crate_(false),
      crate_thrown_(false),
      crate_active_(true) {
}

void Game055NinjaGaiden::Init() {
    Reset();
}

void Game055NinjaGaiden::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    player_health_ = 100;
    InitStage();
}

void Game055NinjaGaiden::InitStage() {
    player_x_ = 2.0f;
    player_y_ = 13.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;
    player_facing_ = 1;
    action_ = ACTION_IDLE;
    action_timer_ = 0.0f;
    is_hanging_bar_ = false;
    swing_timer_ = 0.0f;

    crate_x_ = 6.0f;
    crate_y_ = 13.0f;
    crate_vx_ = 0.0f;
    is_carrying_crate_ = false;
    crate_thrown_ = false;
    crate_active_ = true;

    enemies_defeated_ = 0;
    enemies_[0] = {8.0f, 13.0f, -2.0f, 2, true};   // Thug 1
    enemies_[1] = {12.0f, 13.0f, -1.5f, 2, true};  // Thug 2
    enemies_[2] = {9.0f, 11.5f, -1.8f, 2, true};   // Ninja thug
    enemies_[3] = {14.0f, 13.0f, -1.0f, 4, true};  // Hockey Mask Boss
    total_enemies_ = 4;
}

void Game055NinjaGaiden::TriggerBarGrab() {
    is_hanging_bar_ = true;
    action_ = ACTION_BAR_SWING;
    swing_timer_ = 0.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;
    player_y_ = 5.0f;
}

void Game055NinjaGaiden::TriggerWallRebound() {
    action_ = ACTION_WALL_JUMP;
    action_timer_ = 0.35f;
    player_vx_ = (player_x_ < 5.0f ? 10.0f : -10.0f);
    player_vy_ = -8.0f;
}

void Game055NinjaGaiden::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
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
    UpdateEnemies(dt);
    UpdateCrate(dt);
    CheckCollisions();

    // Check Victory
    if (enemies_defeated_ >= total_enemies_) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 1000;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game055NinjaGaiden::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Hanging on gymnastic bar
    if (is_hanging_bar_) {
        swing_timer_ += dt * 8.0f;
        // Press A or B to release into high-speed whirling flying kick!
        if (((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) ||
            ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B))) {
            is_hanging_bar_ = false;
            action_ = ACTION_WALL_JUMP; // Flying kick trajectory
            action_timer_ = 0.45f;
            player_vx_ = player_facing_ * 14.0f;
            player_vy_ = 4.0f;
        }
        return;
    }

    // Special action in progress (Wall jump or Bar release kick)
    if (action_ == ACTION_WALL_JUMP) {
        action_timer_ -= dt;
        player_x_ += player_vx_ * dt;
        player_y_ += player_vy_ * dt;
        player_vy_ += 25.0f * dt; // Gravity

        if (player_y_ >= 13.0f) {
            player_y_ = 13.0f;
            player_vy_ = 0.0f;
            player_vx_ = 0.0f;
            action_ = ACTION_IDLE;
        }
        return;
    }

    // Slash action
    if (action_ == ACTION_SLASH) {
        action_timer_ -= dt;
        if (action_timer_ <= 0.0f) {
            action_ = ACTION_IDLE;
        }
    }

    // Movement (Belt-scroll horizontal + vertical lane)
    float speed = 6.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;

    if (buttons & BUTTON_LEFT) {
        player_vx_ = -speed;
        player_facing_ = -1;
    } else if (buttons & BUTTON_RIGHT) {
        player_vx_ = speed;
        player_facing_ = 1;
    }

    if (buttons & BUTTON_UP) {
        player_vy_ = -speed * 0.7f;
    } else if (buttons & BUTTON_DOWN) {
        player_vy_ = speed * 0.7f;
    }

    player_x_ += player_vx_ * dt;
    player_y_ += player_vy_ * dt;

    if (player_x_ < 0.8f) player_x_ = 0.8f;
    if (player_x_ > 14.8f) player_x_ = 14.8f;
    if (player_y_ < 9.0f) player_y_ = 9.0f;
    if (player_y_ > 14.5f) player_y_ = 14.5f;

    // Carrying crate moves crate with player
    if (is_carrying_crate_) {
        crate_x_ = player_x_;
        crate_y_ = player_y_ - 1.5f;
    }

    // Jump trigger (Button B)
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        // Check wall rebound jump if next to wall
        if (player_x_ <= 1.2f || player_x_ >= 14.2f) {
            TriggerWallRebound();
            return;
        }

        // Check if jumping beneath overhead horizontal bar (x in [4, 11])
        if (player_x_ >= 4.0f && player_x_ <= 11.0f) {
            TriggerBarGrab();
            return;
        }

        // Regular vertical hop
        action_ = ACTION_WALL_JUMP;
        action_timer_ = 0.4f;
        player_vy_ = -9.0f;
        player_vx_ = player_facing_ * 4.0f;
        return;
    }

    // Attack / Action trigger (Button A)
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        if (is_carrying_crate_) {
            // Throw crate forward!
            is_carrying_crate_ = false;
            crate_thrown_ = true;
            crate_vx_ = player_facing_ * 13.0f;
            return;
        }

        // Check picking up crate
        if (crate_active_ && !crate_thrown_ && !is_carrying_crate_) {
            if (std::abs(player_x_ - crate_x_) < 1.4f && std::abs(player_y_ - crate_y_) < 1.4f) {
                is_carrying_crate_ = true;
                return;
            }
        }

        // Regular Dragon Sword melee slash combo
        action_ = ACTION_SLASH;
        action_timer_ = 0.22f;

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
}

void Game055NinjaGaiden::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        // Advance towards player
        float dx = player_x_ - enemies_[i].x;
        float dy = player_y_ - enemies_[i].y;
        float dist = std::hypot(dx, dy);

        if (dist > 0.8f) {
            enemies_[i].x += (dx > 0 ? 1.0f : -1.0f) * 2.2f * dt;
            enemies_[i].y += (dy > 0 ? 1.0f : -1.0f) * 1.5f * dt;
        }

        enemies_[i].x = std::max(1.0f, std::min(14.5f, enemies_[i].x));
        enemies_[i].y = std::max(9.0f, std::min(14.5f, enemies_[i].y));
    }
}

void Game055NinjaGaiden::UpdateCrate(float dt) {
    if (crate_thrown_) {
        crate_x_ += crate_vx_ * dt;
        crate_y_ += 3.0f * dt; // Slight drop

        // Collide with enemies
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (!enemies_[i].active) continue;
            if (std::abs(crate_x_ - enemies_[i].x) < 1.3f && std::abs(crate_y_ - enemies_[i].y) < 1.3f) {
                enemies_[i].health -= 3;
                crate_thrown_ = false;
                crate_active_ = false; // Shatters
                score_ += 250;
                if (enemies_[i].health <= 0) {
                    enemies_[i].active = false;
                    enemies_defeated_++;
                }
                break;
            }
        }

        if (crate_x_ < 0.0f || crate_x_ > 16.0f || crate_y_ > 15.0f) {
            crate_thrown_ = false;
            crate_active_ = false;
        }
    }
}

void Game055NinjaGaiden::CheckCollisions() {
    // Flying kick / wall jump impact on enemies
    if (action_ == ACTION_WALL_JUMP) {
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (!enemies_[i].active) continue;
            if (std::abs(player_x_ - enemies_[i].x) < 1.4f && std::abs(player_y_ - enemies_[i].y) < 1.4f) {
                enemies_[i].health -= 2;
                score_ += 200;
                if (enemies_[i].health <= 0) {
                    enemies_[i].active = false;
                    enemies_defeated_++;
                }
            }
        }
    }

    // Enemy attacks on player
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        if (action_ != ACTION_WALL_JUMP && !is_hanging_bar_) {
            if (std::abs(player_x_ - enemies_[i].x) < 0.8f && std::abs(player_y_ - enemies_[i].y) < 0.7f) {
                player_health_ -= 15;
                if (player_health_ <= 0) {
                    lives_--;
                    state_ = STATE_DEAD;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }
    }
}

void Game055NinjaGaiden::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // City street background (Deep dusk skyline y=0..3)
    for (int y = 0; y < 4; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = 20;
            fb[idx + 1] = 10;
            fb[idx + 2] = 40; // Violet night sky
        }
    }

    // Overhead horizontal scaffold pipe (y=4, x=4..11)
    for (int x = 4; x <= 11; ++x) {
        int idx = (4 * 16 + x) * 3;
        fb[idx] = 180;
        fb[idx + 1] = 180;
        fb[idx + 2] = 190; // Steel gymnastic pipe
    }

    // Wall bricks on left & right borders (x=0, x=15)
    for (int y = 4; y < 16; ++y) {
        int idx_l = (y * 16 + 0) * 3;
        fb[idx_l] = 90;
        fb[idx_l + 1] = 40;
        fb[idx_l + 2] = 30; // Brick red

        int idx_r = (y * 16 + 15) * 3;
        fb[idx_r] = 90;
        fb[idx_r + 1] = 40;
        fb[idx_r + 2] = 30;
    }

    // Asphalt street floor (y=9..15)
    for (int y = 9; y < 16; ++y) {
        for (int x = 1; x < 15; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = 40;
            fb[idx + 1] = 45;
            fb[idx + 2] = 50; // Dark asphalt
        }
    }

    // Render Wooden Crate (Brown square)
    if (crate_active_ || is_carrying_crate_ || crate_thrown_) {
        int cx = static_cast<int>(std::round(crate_x_));
        int cy = static_cast<int>(std::round(crate_y_));
        if (cx >= 0 && cx < 16 && cy >= 0 && cy < 16) {
            int idx = (cy * 16 + cx) * 3;
            fb[idx] = 180;
            fb[idx + 1] = 110;
            fb[idx + 2] = 40; // Wood brown
        }
    }

    // Render Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));
        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            if (i == 3) {
                // Hockey Mask Boss (White mask / purple vest)
                fb[idx] = 255;
                fb[idx + 1] = 255;
                fb[idx + 2] = 255;
            } else {
                fb[idx] = 200;
                fb[idx + 1] = 40;
                fb[idx + 2] = 40; // Red thug
            }
        }
    }

    // Render Player (Ryu Hayabusa: Blue ninja suit with gold headband)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx] = 30;
        fb[idx + 1] = 100;
        fb[idx + 2] = 240; // Cobalt blue ninja suit

        // Slash effect or flying kick trail
        if (action_ == ACTION_SLASH) {
            int sx = px + player_facing_;
            if (sx >= 0 && sx < 16) {
                int s_idx = (py * 16 + sx) * 3;
                fb[s_idx] = 200;
                fb[s_idx + 1] = 230;
                fb[s_idx + 2] = 255; // Katana light arc
            }
        } else if (action_ == ACTION_WALL_JUMP) {
            int trail_x = px - player_facing_;
            if (trail_x >= 0 && trail_x < 16) {
                int t_idx = (py * 16 + trail_x) * 3;
                fb[t_idx] = 255;
                fb[t_idx + 1] = 200;
                fb[t_idx + 2] = 0; // Speed kick spark
            }
        }
    }

    // Top HUD: Health bar & Lives
    int hp_bars = (player_health_ * 6) / 100;
    for (int h = 0; h < hp_bars && h < 6; ++h) {
        int idx = h * 3;
        fb[idx] = 0;
        fb[idx + 1] = 255;
        fb[idx + 2] = 0;
    }

    for (int l = 0; l < lives_ && l < 3; ++l) {
        int idx = (15 - l) * 3;
        fb[idx] = 255;
        fb[idx + 1] = 0;
        fb[idx + 2] = 0;
    }
}

} // namespace arcade
