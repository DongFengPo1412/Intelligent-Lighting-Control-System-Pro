#include "game_052_gunsmoke.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game052GunSmoke::Game052GunSmoke()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(2000),
      lives_(3),
      player_x_(7.5f),
      player_y_(13.5f),
      has_horse_(false),
      horse_armor_(0),
      scroll_dist_(0.0f),
      scroll_speed_(4.0f),
      boss_active_(false),
      boss_x_(7.5f),
      boss_y_(3.0f),
      boss_vx_(3.0f),
      boss_health_(8),
      boss_shoot_cooldown_(1.5f) {
}

void Game052GunSmoke::Init() {
    Reset();
}

void Game052GunSmoke::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game052GunSmoke::InitStage() {
    player_x_ = 7.5f;
    player_y_ = 13.5f;
    has_horse_ = false;
    horse_armor_ = 0;
    scroll_dist_ = 0.0f;
    boss_active_ = false;
    boss_health_ = 8;
    boss_x_ = 7.5f;
    boss_y_ = 3.0f;
    boss_vx_ = 3.0f;
    boss_shoot_cooldown_ = 1.5f;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    bandits_[0] = {3.0f, -2.0f, 1.5f, 1, true, 1.2f};
    bandits_[1] = {12.0f, -6.0f, -1.8f, 1, true, 2.0f};
    bandits_[2] = {7.0f, -10.0f, 1.0f, 1, true, 1.5f};
    bandits_[3] = {14.0f, -14.0f, -1.2f, 1, true, 2.5f};

    barrels_[0] = {4.0f, -5.0f, true, true};   // Contains horse!
    barrels_[1] = {11.0f, -12.0f, false, true};
}

void Game052GunSmoke::Shoot(int direction) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].active = true;
            bullets_[i].x = player_x_;
            bullets_[i].y = player_y_ - 1.0f;
            bullets_[i].is_player = true;

            if (direction < 0) {
                // Left 45 deg
                bullets_[i].vx = -8.0f;
                bullets_[i].vy = -16.0f;
            } else if (direction > 0) {
                // Right 45 deg
                bullets_[i].vx = 8.0f;
                bullets_[i].vy = -16.0f;
            } else {
                // Center straight
                bullets_[i].vx = 0.0f;
                bullets_[i].vy = -20.0f;
            }
            break;
        }
    }
}

void Game052GunSmoke::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
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

    UpdatePlayer(dt, buttons, prev_buttons);

    // Scroll canyon terrain forward if boss not reached
    if (!boss_active_) {
        scroll_dist_ += scroll_speed_ * dt;
        if (scroll_dist_ >= 40.0f) {
            boss_active_ = true;
            boss_y_ = 3.0f;
            // Clear standard bandits
            for (int i = 0; i < MAX_BANDITS; ++i) bandits_[i].active = false;
        }
    }

    UpdateBullets(dt);
    if (boss_active_) {
        UpdateBoss(dt);
    } else {
        UpdateBandits(dt);
    }
    CheckCollisions();
}

void Game052GunSmoke::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_speed = has_horse_ ? 8.5f : 6.0f;

    if (buttons & BUTTON_LEFT)  player_x_ -= move_speed * dt;
    if (buttons & BUTTON_RIGHT) player_x_ += move_speed * dt;
    if (buttons & BUTTON_UP)    player_y_ -= move_speed * dt;
    if (buttons & BUTTON_DOWN)  player_y_ += move_speed * dt;

    if (player_x_ < 1.0f) player_x_ = 1.0f;
    if (player_x_ > 14.5f) player_x_ = 14.5f;
    if (player_y_ < 2.0f) player_y_ = 2.0f;
    if (player_y_ > 14.5f) player_y_ = 14.5f;

    // Gun.Smoke iconic 3-way shooting logic:
    // A + B pressed simultaneously -> Straight Ahead (0)
    // A pressed alone -> Left (-1)
    // B pressed alone -> Right (+1)
    bool btn_a = (buttons & BUTTON_A) != 0;
    bool btn_b = (buttons & BUTTON_B) != 0;
    bool prev_a = (prev_buttons & BUTTON_A) != 0;
    bool prev_b = (prev_buttons & BUTTON_B) != 0;

    if ((btn_a || btn_b) && (!prev_a || !prev_b)) {
        if (btn_a && btn_b) {
            Shoot(0); // Center forward
        } else if (btn_a) {
            Shoot(-1); // Left 45 deg
        } else {
            Shoot(1); // Right 45 deg
        }
    }
}

void Game052GunSmoke::UpdateBullets(float dt) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        bullets_[i].x += bullets_[i].vx * dt;
        bullets_[i].y += bullets_[i].vy * dt;

        if (bullets_[i].x < 0.0f || bullets_[i].x > 15.5f ||
            bullets_[i].y < 0.0f || bullets_[i].y > 15.5f) {
            bullets_[i].active = false;
        }
    }
}

void Game052GunSmoke::UpdateBandits(float dt) {
    for (int i = 0; i < MAX_BANDITS; ++i) {
        if (!bandits_[i].active) continue;

        bandits_[i].y += scroll_speed_ * dt * 0.8f;
        bandits_[i].x += bandits_[i].vx * dt;

        if (bandits_[i].x < 2.0f) {
            bandits_[i].x = 2.0f;
            bandits_[i].vx = std::abs(bandits_[i].vx);
        } else if (bandits_[i].x > 13.5f) {
            bandits_[i].x = 13.5f;
            bandits_[i].vx = -std::abs(bandits_[i].vx);
        }

        // Loop / respawn from top if scrolls off screen
        if (bandits_[i].y > 16.0f) {
            bandits_[i].y = -2.0f;
            bandits_[i].health = 1;
        }

        // Shooting towards player
        bandits_[i].shoot_cooldown -= dt;
        if (bandits_[i].shoot_cooldown <= 0.0f && bandits_[i].y > 1.0f) {
            bandits_[i].shoot_cooldown = 2.2f;
            // Spawn enemy bullet
            for (int b = 0; b < MAX_BULLETS; ++b) {
                if (!bullets_[b].active) {
                    bullets_[b].active = true;
                    bullets_[b].x = bandits_[i].x;
                    bullets_[b].y = bandits_[i].y + 1.0f;
                    bullets_[b].is_player = false;

                    float dx = player_x_ - bullets_[b].x;
                    float dy = player_y_ - bullets_[b].y;
                    float len = std::sqrt(dx * dx + dy * dy);
                    if (len > 0.1f) {
                        bullets_[b].vx = (dx / len) * 8.0f;
                        bullets_[b].vy = (dy / len) * 8.0f;
                    } else {
                        bullets_[b].vx = 0.0f;
                        bullets_[b].vy = 8.0f;
                    }
                    break;
                }
            }
        }
    }

    // Barrels drifting down
    for (int i = 0; i < MAX_BARRELS; ++i) {
        if (!barrels_[i].active) continue;
        barrels_[i].y += scroll_speed_ * dt;
        if (barrels_[i].y > 16.0f) {
            barrels_[i].active = false;
        }
    }
}

void Game052GunSmoke::UpdateBoss(float dt) {
    boss_x_ += boss_vx_ * dt;
    if (boss_x_ < 3.0f) {
        boss_x_ = 3.0f;
        boss_vx_ = std::abs(boss_vx_);
    } else if (boss_x_ > 12.0f) {
        boss_x_ = 12.0f;
        boss_vx_ = -std::abs(boss_vx_);
    }

    boss_shoot_cooldown_ -= dt;
    if (boss_shoot_cooldown_ <= 0.0f) {
        boss_shoot_cooldown_ = 1.4f;
        // Shoot 2 bullets in spread
        for (int dir = -1; dir <= 1; dir += 2) {
            for (int b = 0; b < MAX_BULLETS; ++b) {
                if (!bullets_[b].active) {
                    bullets_[b].active = true;
                    bullets_[b].x = boss_x_;
                    bullets_[b].y = boss_y_ + 1.0f;
                    bullets_[b].vx = dir * 4.0f;
                    bullets_[b].vy = 9.0f;
                    bullets_[b].is_player = false;
                    break;
                }
            }
        }
    }
}

void Game052GunSmoke::CheckCollisions() {
    // Player bullets hitting bandits or barrels or boss
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active || !bullets_[b].is_player) continue;

        // Check barrels
        for (int r = 0; r < MAX_BARRELS; ++r) {
            if (!barrels_[r].active) continue;
            if (std::abs(bullets_[b].x - barrels_[r].x) < 1.2f &&
                std::abs(bullets_[b].y - barrels_[r].y) < 1.2f) {
                bullets_[b].active = false;
                barrels_[r].active = false;
                score_ += 50;
                if (barrels_[r].has_horse) {
                    has_horse_ = true;
                    horse_armor_ = 3;
                    score_ += 200;
                }
                break;
            }
        }
        if (!bullets_[b].active) continue;

        // Check bandits
        for (int i = 0; i < MAX_BANDITS; ++i) {
            if (!bandits_[i].active) continue;
            if (std::abs(bullets_[b].x - bandits_[i].x) < 1.1f &&
                std::abs(bullets_[b].y - bandits_[i].y) < 1.1f) {
                bullets_[b].active = false;
                bandits_[i].health--;
                if (bandits_[i].health <= 0) {
                    bandits_[i].active = false;
                    score_ += 100;
                }
                break;
            }
        }
        if (!bullets_[b].active) continue;

        // Check boss
        if (boss_active_) {
            if (std::abs(bullets_[b].x - boss_x_) < 1.6f &&
                std::abs(bullets_[b].y - boss_y_) < 1.6f) {
                bullets_[b].active = false;
                boss_health_--;
                score_ += 50;
                if (boss_health_ <= 0) {
                    boss_active_ = false;
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 1000;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
            }
        }
    }

    // Enemy bullets hitting player
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active || bullets_[b].is_player) continue;

        if (std::abs(bullets_[b].x - player_x_) < 0.9f &&
            std::abs(bullets_[b].y - player_y_) < 0.9f) {
            bullets_[b].active = false;

            if (has_horse_) {
                horse_armor_--;
                if (horse_armor_ <= 0) {
                    has_horse_ = false;
                }
            } else {
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }

    // Direct collision with bandits
    for (int i = 0; i < MAX_BANDITS; ++i) {
        if (!bandits_[i].active) continue;
        if (std::abs(bandits_[i].x - player_x_) < 0.9f &&
            std::abs(bandits_[i].y - player_y_) < 0.9f) {
            if (has_horse_) {
                has_horse_ = false;
                bandits_[i].active = false;
            } else {
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game052GunSmoke::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Desert canyon ground with moving dust lines
    int offset = static_cast<int>(scroll_dist_) % 4;
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            // Sandy terrain
            fb[idx] = 120;
            fb[idx + 1] = 90;
            fb[idx + 2] = 40;

            // Canyon rock walls on left/right borders
            if (x == 0 || x == 15) {
                fb[idx] = 80;
                fb[idx + 1] = 50;
                fb[idx + 2] = 20;
            } else if ((y + offset) % 6 == 0 && (x % 3 == 0)) {
                // Dust pebble
                fb[idx] = 150;
                fb[idx + 1] = 110;
                fb[idx + 2] = 50;
            }
        }
    }

    // Render Barrels (Wood brown / orange)
    for (int r = 0; r < MAX_BARRELS; ++r) {
        if (!barrels_[r].active) continue;
        int rx = static_cast<int>(std::round(barrels_[r].x));
        int ry = static_cast<int>(std::round(barrels_[r].y));
        if (rx >= 0 && rx < 16 && ry >= 0 && ry < 16) {
            int idx = (ry * 16 + rx) * 3;
            fb[idx] = 180;
            fb[idx + 1] = 100;
            fb[idx + 2] = 20;
        }
    }

    // Render Bandits (Blue outlaw coats)
    for (int i = 0; i < MAX_BANDITS; ++i) {
        if (!bandits_[i].active) continue;
        int bx = static_cast<int>(std::round(bandits_[i].x));
        int by = static_cast<int>(std::round(bandits_[i].y));
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            fb[idx] = 40;
            fb[idx + 1] = 80;
            fb[idx + 2] = 200;
        }
    }

    // Render Boss (Red Outlaw King)
    if (boss_active_) {
        int bx = static_cast<int>(std::round(boss_x_));
        int by = static_cast<int>(std::round(boss_y_));
        for (int dy = 0; dy <= 1; ++dy) {
            for (int dx = -1; dx <= 1; ++dx) {
                int px = bx + dx;
                int py = by + dy;
                if (px >= 0 && px < 16 && py >= 0 && py < 16) {
                    int idx = (py * 16 + px) * 3;
                    fb[idx] = 255;
                    fb[idx + 1] = 20;
                    fb[idx + 2] = 20;
                }
            }
        }
    }

    // Render Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        int bx = static_cast<int>(std::round(bullets_[i].x));
        int by = static_cast<int>(std::round(bullets_[i].y));
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            if (bullets_[i].is_player) {
                fb[idx] = 255;
                fb[idx + 1] = 240;
                fb[idx + 2] = 50; // Yellow bullet
            } else {
                fb[idx] = 255;
                fb[idx + 1] = 50;
                fb[idx + 2] = 50; // Red bullet
            }
        }
    }

    // Render Player (Bounty Hunter Billy: White hat / brown vest)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx] = 255;
        fb[idx + 1] = 255;
        fb[idx + 2] = 255;

        // Horse mount (Flanking brown pixels)
        if (has_horse_) {
            if (px > 0) {
                int left_idx = (py * 16 + (px - 1)) * 3;
                fb[left_idx] = 160;
                fb[left_idx + 1] = 82;
                fb[left_idx + 2] = 45; // Saddle brown
            }
            if (px < 15) {
                int right_idx = (py * 16 + (px + 1)) * 3;
                fb[right_idx] = 160;
                fb[right_idx + 1] = 82;
                fb[right_idx + 2] = 45;
            }
        }
    }

    // Top HUD: Lives & Horse Armor
    for (int l = 0; l < lives_ && l < 4; ++l) {
        int idx = l * 3;
        fb[idx] = 0;
        fb[idx + 1] = 255;
        fb[idx + 2] = 0;
    }

    for (int a = 0; a < horse_armor_; ++a) {
        int idx = (15 - a) * 3;
        fb[idx] = 255;
        fb[idx + 1] = 165;
        fb[idx + 2] = 0; // Orange armor pips
    }
}

} // namespace arcade
