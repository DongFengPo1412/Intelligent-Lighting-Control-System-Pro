#include "game_051_shinobi.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game051Shinobi::Game051Shinobi()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(1000),
      lives_(3),
      hostages_rescued_(0),
      enemies_defeated_(0),
      total_enemies_(0),
      player_x_(1.0f),
      player_tier_(1),
      player_facing_(1),
      is_crouching_(false),
      is_leaping_tier_(false),
      leap_progress_(0.0f),
      is_melee_slashing_(false),
      melee_timer_(0.0f),
      has_gun_upgrade_(false),
      has_ninjutsu_(true),
      ninjutsu_flash_timer_(0.0f) {
}

void Game051Shinobi::Init() {
    Reset();
}

void Game051Shinobi::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    has_gun_upgrade_ = false;
    has_ninjutsu_ = true;
    ninjutsu_flash_timer_ = 0.0f;
    InitStage();
}

void Game051Shinobi::InitStage() {
    player_x_ = 1.0f;
    player_tier_ = 1;
    player_facing_ = 1;
    is_crouching_ = false;
    is_leaping_tier_ = false;
    leap_progress_ = 0.0f;
    is_melee_slashing_ = false;
    melee_timer_ = 0.0f;
    hostages_rescued_ = 0;
    enemies_defeated_ = 0;

    // Hostages: 1 on upper tier, 1 on lower tier
    hostages_[0] = {6.0f, 0, false};
    hostages_[1] = {11.0f, 1, false};

    // Enemies
    enemies_[0] = {8.0f, 1, -1.5f, 1, true, 2.0f};
    enemies_[1] = {14.0f, 1, -2.0f, 1, true, 1.5f};
    enemies_[2] = {10.0f, 0, -1.0f, 1, true, 2.5f};
    enemies_[3] = {13.0f, 0, -1.2f, 2, true, 1.8f};
    total_enemies_ = 4;

    for (int i = 0; i < MAX_SHURIKENS; ++i) {
        shurikens_[i].active = false;
    }
}

int Game051Shinobi::GetHostagesRemaining() const {
    int remaining = 0;
    for (int i = 0; i < MAX_HOSTAGES; ++i) {
        if (!hostages_[i].rescued) remaining++;
    }
    return remaining;
}

void Game051Shinobi::ThrowShuriken() {
    for (int i = 0; i < MAX_SHURIKENS; ++i) {
        if (!shurikens_[i].active) {
            shurikens_[i].active = true;
            shurikens_[i].tier = player_tier_;
            shurikens_[i].x = player_x_ + (player_facing_ > 0 ? 1.0f : -1.0f);
            shurikens_[i].vx = (has_gun_upgrade_ ? 18.0f : 12.0f) * player_facing_;
            shurikens_[i].is_gunshot = has_gun_upgrade_;
            break;
        }
    }
}

void Game051Shinobi::TriggerNinjutsu() {
    if (!has_ninjutsu_) return;
    has_ninjutsu_ = false;
    ninjutsu_flash_timer_ = 0.6f;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].active) {
            enemies_[i].active = false;
            enemies_defeated_++;
            score_ += 200;
        }
    }
}

void Game051Shinobi::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.5f) {
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

    if (ninjutsu_flash_timer_ > 0.0f) {
        ninjutsu_flash_timer_ -= dt;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateEnemies(dt);
    UpdateShurikens(dt);
    CheckCollisions();

    // Check Victory condition: all hostages rescued and all enemies defeated
    if (GetHostagesRemaining() == 0 && enemies_defeated_ >= total_enemies_) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 500;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game051Shinobi::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (is_melee_slashing_) {
        melee_timer_ -= dt;
        if (melee_timer_ <= 0.0f) {
            is_melee_slashing_ = false;
        }
    }

    // Tier leap progress
    if (is_leaping_tier_) {
        leap_progress_ += dt * 3.5f;
        if (leap_progress_ >= 1.0f) {
            is_leaping_tier_ = false;
            leap_progress_ = 0.0f;
            player_tier_ = 1 - player_tier_; // Flip tier (0 -> 1 or 1 -> 0)
        }
        return; // In-air leaping lock
    }

    // Crouching
    is_crouching_ = (buttons & BUTTON_DOWN) != 0;

    // Movement horizontal
    if (!is_crouching_) {
        if (buttons & BUTTON_LEFT) {
            player_x_ -= 5.0f * dt;
            player_facing_ = -1;
        } else if (buttons & BUTTON_RIGHT) {
            player_x_ += 5.0f * dt;
            player_facing_ = 1;
        }
    }

    if (player_x_ < 0.5f) player_x_ = 0.5f;
    if (player_x_ > 15.0f) player_x_ = 15.0f;

    // Leap Tier trigger: Button B (or UP if on lower tier / DOWN if on upper tier with B)
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        is_leaping_tier_ = true;
        leap_progress_ = 0.0f;
    }

    // Ninjutsu trigger: SELECT or UP+A
    if ((buttons & BUTTON_SELECT) && !(prev_buttons & BUTTON_SELECT)) {
        TriggerNinjutsu();
    }

    // Attack trigger: Button A
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        // Check for close-range melee
        bool melee_target = false;
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (enemies_[i].active && enemies_[i].tier == player_tier_) {
                float dist = std::abs(enemies_[i].x - player_x_);
                if (dist <= 1.8f) {
                    enemies_[i].health -= 2;
                    if (enemies_[i].health <= 0) {
                        enemies_[i].active = false;
                        enemies_defeated_++;
                        score_ += 100;
                    }
                    melee_target = true;
                }
            }
        }

        if (melee_target) {
            is_melee_slashing_ = true;
            melee_timer_ = 0.2f;
        } else {
            ThrowShuriken();
        }
    }
}

void Game051Shinobi::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        enemies_[i].x += enemies_[i].vx * dt;

        // Bounce patrol bounds
        if (enemies_[i].x < 2.0f) {
            enemies_[i].x = 2.0f;
            enemies_[i].vx = std::abs(enemies_[i].vx);
        } else if (enemies_[i].x > 14.5f) {
            enemies_[i].x = 14.5f;
            enemies_[i].vx = -std::abs(enemies_[i].vx);
        }

        // Enemy shooting
        enemies_[i].shoot_cooldown -= dt;
        if (enemies_[i].shoot_cooldown <= 0.0f) {
            enemies_[i].shoot_cooldown = 2.0f;
            // Throw enemy star towards player if on same tier
            if (enemies_[i].tier == player_tier_ && !is_leaping_tier_) {
                for (int s = 0; s < MAX_SHURIKENS; ++s) {
                    if (!shurikens_[s].active) {
                        shurikens_[s].active = true;
                        shurikens_[s].tier = enemies_[i].tier;
                        shurikens_[s].x = enemies_[i].x;
                        shurikens_[s].vx = (enemies_[i].x > player_x_ ? -6.0f : 6.0f);
                        shurikens_[s].is_gunshot = false;
                        break;
                    }
                }
            }
        }
    }
}

void Game051Shinobi::UpdateShurikens(float dt) {
    for (int i = 0; i < MAX_SHURIKENS; ++i) {
        if (!shurikens_[i].active) continue;
        shurikens_[i].x += shurikens_[i].vx * dt;
        if (shurikens_[i].x < -1.0f || shurikens_[i].x > 16.0f) {
            shurikens_[i].active = false;
        }
    }
}

void Game051Shinobi::CheckCollisions() {
    // Check hostage rescues
    for (int i = 0; i < MAX_HOSTAGES; ++i) {
        if (!hostages_[i].rescued) {
            if (player_tier_ == hostages_[i].tier && !is_leaping_tier_) {
                if (std::abs(player_x_ - hostages_[i].x) < 1.0f) {
                    hostages_[i].rescued = true;
                    hostages_rescued_++;
                    score_ += 300;
                    if (i == 0) {
                        has_gun_upgrade_ = true; // First hostage grants gun upgrade
                    } else {
                        has_ninjutsu_ = true;    // Second hostage restores Ninjutsu
                    }
                }
            }
        }
    }

    // Check shuriken hits
    for (int s = 0; s < MAX_SHURIKENS; ++s) {
        if (!shurikens_[s].active) continue;

        // Player projectile hits enemies
        if (shurikens_[s].vx > 0.0f || (shurikens_[s].vx < 0.0f && shurikens_[s].x > player_x_ && player_facing_ < 0)) {
            for (int e = 0; e < MAX_ENEMIES; ++e) {
                if (enemies_[e].active && enemies_[e].tier == shurikens_[s].tier) {
                    if (std::abs(shurikens_[s].x - enemies_[e].x) < 0.8f) {
                        shurikens_[s].active = false;
                        enemies_[e].health -= (shurikens_[s].is_gunshot ? 2 : 1);
                        if (enemies_[e].health <= 0) {
                            enemies_[e].active = false;
                            enemies_defeated_++;
                            score_ += 100;
                        }
                        break;
                    }
                }
            }
        } else {
            // Enemy projectile hits player
            if (shurikens_[s].tier == player_tier_ && !is_leaping_tier_) {
                if (std::abs(shurikens_[s].x - player_x_) < 0.8f) {
                    // If player is crouching, high projectile misses
                    if (!is_crouching_) {
                        shurikens_[s].active = false;
                        lives_--;
                        state_ = STATE_DEAD;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            }
        }
    }

    // Check enemy body contact with player
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (enemies_[e].active && enemies_[e].tier == player_tier_ && !is_leaping_tier_) {
            if (std::abs(enemies_[e].x - player_x_) < 0.7f) {
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game051Shinobi::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Screen flash for Ninjutsu
    if (ninjutsu_flash_timer_ > 0.0f) {
        for (int i = 0; i < 16 * 16 * 3; ++i) {
            fb[i] = 255;
        }
        return;
    }

    // Platforms:
    // Upper tier catwalk: y = 8 (pixels x=0..15)
    // Lower tier ground: y = 14 (pixels x=0..15)
    for (int x = 0; x < 16; ++x) {
        // Catwalk beam
        int idx_catwalk = (8 * 16 + x) * 3;
        fb[idx_catwalk] = 40;
        fb[idx_catwalk + 1] = 40;
        fb[idx_catwalk + 2] = 50;

        // Ground floor
        int idx_ground = (14 * 16 + x) * 3;
        fb[idx_ground] = 50;
        fb[idx_ground + 1] = 30;
        fb[idx_ground + 2] = 20;
    }

    // Render Hostages (Cyan / Yellow kid)
    for (int i = 0; i < MAX_HOSTAGES; ++i) {
        if (!hostages_[i].rescued) {
            int hx = static_cast<int>(std::round(hostages_[i].x));
            int hy = (hostages_[i].tier == 0 ? 7 : 13);
            if (hx >= 0 && hx < 16 && hy >= 0 && hy < 16) {
                int idx = (hy * 16 + hx) * 3;
                fb[idx] = 0;
                fb[idx + 1] = 255;
                fb[idx + 2] = 255; // Cyan hostage
            }
        }
    }

    // Render Enemies (Red ninja / thug)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].active) {
            int ex = static_cast<int>(std::round(enemies_[i].x));
            int ey = (enemies_[i].tier == 0 ? 7 : 13);
            if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
                int idx = (ey * 16 + ex) * 3;
                fb[idx] = 255;
                fb[idx + 1] = 30;
                fb[idx + 2] = 30; // Red
            }
        }
    }

    // Render Shurikens / Projectiles
    for (int i = 0; i < MAX_SHURIKENS; ++i) {
        if (shurikens_[i].active) {
            int sx = static_cast<int>(std::round(shurikens_[i].x));
            int sy = (shurikens_[i].tier == 0 ? 7 : 13);
            if (sx >= 0 && sx < 16 && sy >= 0 && sy < 16) {
                int idx = (sy * 16 + sx) * 3;
                if (shurikens_[i].is_gunshot) {
                    fb[idx] = 255;
                    fb[idx + 1] = 200;
                    fb[idx + 2] = 0; // Gold gunshot
                } else {
                    fb[idx] = 220;
                    fb[idx + 1] = 220;
                    fb[idx + 2] = 255; // Shuriken glint
                }
            }
        }
    }

    // Render Player (Joe Musashi: White/Blue master shinobi)
    int px = static_cast<int>(std::round(player_x_));
    int py = (player_tier_ == 0 ? 7 : 13);
    if (is_leaping_tier_) {
        // Arc between tiers (7 and 13)
        float start_y = (player_tier_ == 0 ? 7.0f : 13.0f);
        float end_y = (player_tier_ == 0 ? 13.0f : 7.0f);
        float mid_y = std::min(start_y, end_y) - 3.0f; // High parabolic arc
        float t = leap_progress_;
        float current_y = (1.0f - t) * (1.0f - t) * start_y + 2.0f * (1.0f - t) * t * mid_y + t * t * end_y;
        py = static_cast<int>(std::round(current_y));
    } else if (is_crouching_) {
        py += 0; // lower profile represented
    }

    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx] = 240;
        fb[idx + 1] = 240;
        fb[idx + 2] = 255; // White shinobi suit

        // Katana swing slash pixel
        if (is_melee_slashing_) {
            int slash_x = px + player_facing_;
            if (slash_x >= 0 && slash_x < 16) {
                int s_idx = (py * 16 + slash_x) * 3;
                fb[s_idx] = 100;
                fb[s_idx + 1] = 220;
                fb[s_idx + 2] = 255; // Azure blade slash
            }
        }
    }

    // HUD top bar: Lives (Red/Green indicators) & Ninjutsu icon
    for (int l = 0; l < lives_ && l < 4; ++l) {
        int idx = (0 * 16 + l) * 3;
        fb[idx] = 0;
        fb[idx + 1] = 255;
        fb[idx + 2] = 0;
    }

    if (has_ninjutsu_) {
        int idx = (0 * 16 + 15) * 3;
        fb[idx] = 255;
        fb[idx + 1] = 0;
        fb[idx + 2] = 255; // Purple ninjutsu scroll indicator
    }
}

} // namespace arcade
