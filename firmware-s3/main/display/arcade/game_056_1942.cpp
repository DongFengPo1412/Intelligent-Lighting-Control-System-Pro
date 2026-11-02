#include "game_056_1942.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game056_1942::Game056_1942()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(4000),
      lives_(3),
      player_x_(7.5f),
      player_y_(13.5f),
      is_looping_(false),
      loop_timer_(0.0f),
      loops_remaining_(3),
      has_wingmen_(false),
      scroll_y_(0.0f),
      planes_defeated_(0),
      boss_active_(false),
      boss_x_(7.5f),
      boss_y_(3.0f),
      boss_vx_(2.5f),
      boss_health_(10),
      boss_shoot_cooldown_(1.2f) {
}

void Game056_1942::Init() {
    Reset();
}

void Game056_1942::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game056_1942::InitStage() {
    player_x_ = 7.5f;
    player_y_ = 13.5f;
    is_looping_ = false;
    loop_timer_ = 0.0f;
    loops_remaining_ = 3;
    has_wingmen_ = false;
    scroll_y_ = 0.0f;
    planes_defeated_ = 0;
    boss_active_ = false;
    boss_x_ = 7.5f;
    boss_y_ = 3.0f;
    boss_vx_ = 2.5f;
    boss_health_ = 10;
    boss_shoot_cooldown_ = 1.2f;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    // Normal green zeros & red squad
    planes_[0] = {3.0f, -2.0f, 1.2f, 2.5f, 0, 1, true, 1.5f};
    planes_[1] = {12.0f, -4.0f, -1.2f, 2.2f, 0, 1, true, 2.0f};
    planes_[2] = {7.5f, -6.0f, 0.0f, 3.0f, 1, 1, true, 1.8f}; // Red squadron plane (drops POW)
    planes_[3] = {4.0f, -9.0f, 1.5f, 2.0f, 0, 1, true, 2.2f};
    planes_[4] = {11.0f, -12.0f, -1.5f, 2.0f, 0, 1, true, 1.6f};
}

void Game056_1942::TriggerLoop() {
    if (!is_looping_ && loops_remaining_ > 0) {
        is_looping_ = true;
        loop_timer_ = 0.6f;
        loops_remaining_--;
    }
}

void Game056_1942::FireBullets() {
    // Center twin guns
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].active = true;
            bullets_[i].x = player_x_;
            bullets_[i].y = player_y_ - 1.0f;
            bullets_[i].vx = 0.0f;
            bullets_[i].vy = -18.0f;
            bullets_[i].is_player = true;
            break;
        }
    }

    // Wingmen escort streams
    if (has_wingmen_) {
        for (int side = -1; side <= 1; side += 2) {
            for (int i = 0; i < MAX_BULLETS; ++i) {
                if (!bullets_[i].active) {
                    bullets_[i].active = true;
                    bullets_[i].x = player_x_ + side * 1.5f;
                    bullets_[i].y = player_y_ - 0.5f;
                    bullets_[i].vx = side * 1.5f;
                    bullets_[i].vy = -18.0f;
                    bullets_[i].is_player = true;
                    break;
                }
            }
        }
    }
}

void Game056_1942::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
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

    scroll_y_ += 6.0f * dt;

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateBullets(dt);

    if (boss_active_) {
        UpdateBoss(dt);
    } else {
        UpdatePlanes(dt);
        if (planes_defeated_ >= 5) {
            boss_active_ = true;
            boss_y_ = 3.0f;
            for (int i = 0; i < MAX_PLANES; ++i) planes_[i].active = false;
        }
    }

    CheckCollisions();
}

void Game056_1942::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (is_looping_) {
        loop_timer_ -= dt;
        if (loop_timer_ <= 0.0f) {
            is_looping_ = false;
        }
        return; // Complete control lock while looping in 3D
    }

    float speed = 7.0f;
    if (buttons & BUTTON_LEFT)  player_x_ -= speed * dt;
    if (buttons & BUTTON_RIGHT) player_x_ += speed * dt;
    if (buttons & BUTTON_UP)    player_y_ -= speed * dt;
    if (buttons & BUTTON_DOWN)  player_y_ += speed * dt;

    player_x_ = std::max(1.0f, std::min(14.5f, player_x_));
    player_y_ = std::max(2.0f, std::min(14.5f, player_y_));

    // Stunt Loop Button B
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        TriggerLoop();
    }

    // Fire Button A
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        FireBullets();
    }
}

void Game056_1942::UpdateBullets(float dt) {
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

void Game056_1942::UpdatePlanes(float dt) {
    for (int i = 0; i < MAX_PLANES; ++i) {
        if (!planes_[i].active) continue;

        planes_[i].x += planes_[i].vx * dt;
        planes_[i].y += planes_[i].vy * dt;

        if (planes_[i].x < 1.0f) {
            planes_[i].x = 1.0f;
            planes_[i].vx = std::abs(planes_[i].vx);
        } else if (planes_[i].x > 14.5f) {
            planes_[i].x = 14.5f;
            planes_[i].vx = -std::abs(planes_[i].vx);
        }

        // Loop / recycle to top
        if (planes_[i].y > 16.0f) {
            planes_[i].y = -2.0f;
            planes_[i].health = 1;
        }

        // Firing at player
        planes_[i].shoot_cooldown -= dt;
        if (planes_[i].shoot_cooldown <= 0.0f && planes_[i].y > 1.0f) {
            planes_[i].shoot_cooldown = 2.0f;
            for (int b = 0; b < MAX_BULLETS; ++b) {
                if (!bullets_[b].active) {
                    bullets_[b].active = true;
                    bullets_[b].x = planes_[i].x;
                    bullets_[b].y = planes_[i].y + 1.0f;
                    bullets_[b].vx = (player_x_ > planes_[i].x ? 2.5f : -2.5f);
                    bullets_[b].vy = 8.0f;
                    bullets_[b].is_player = false;
                    break;
                }
            }
        }
    }
}

void Game056_1942::UpdateBoss(float dt) {
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
        boss_shoot_cooldown_ = 1.3f;
        // 3-way scatter volley
        for (int dir = -1; dir <= 1; ++dir) {
            for (int b = 0; b < MAX_BULLETS; ++b) {
                if (!bullets_[b].active) {
                    bullets_[b].active = true;
                    bullets_[b].x = boss_x_ + dir * 1.5f;
                    bullets_[b].y = boss_y_ + 1.5f;
                    bullets_[b].vx = dir * 4.0f;
                    bullets_[b].vy = 7.5f;
                    bullets_[b].is_player = false;
                    break;
                }
            }
        }
    }
}

void Game056_1942::CheckCollisions() {
    // Player bullets hit enemy planes or boss
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active || !bullets_[b].is_player) continue;

        if (boss_active_) {
            if (std::abs(bullets_[b].x - boss_x_) < 2.2f &&
                std::abs(bullets_[b].y - boss_y_) < 1.6f) {
                bullets_[b].active = false;
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
            for (int i = 0; i < MAX_PLANES; ++i) {
                if (!planes_[i].active) continue;
                if (std::abs(bullets_[b].x - planes_[i].x) < 1.2f &&
                    std::abs(bullets_[b].y - planes_[i].y) < 1.2f) {
                    bullets_[b].active = false;
                    planes_[i].health--;
                    if (planes_[i].health <= 0) {
                        planes_[i].active = false;
                        planes_defeated_++;
                        score_ += (planes_[i].type == 1 ? 200 : 100);
                        if (planes_[i].type == 1) {
                            has_wingmen_ = true; // Red squadron POW unlocks wingmen!
                        }
                        if (planes_defeated_ >= 5) {
                            boss_active_ = true;
                            boss_y_ = 3.0f;
                            for (int p = 0; p < MAX_PLANES; ++p) planes_[p].active = false;
                        }
                    }
                    break;
                }
            }
        }
    }

    // Invincibility check during loop stunt
    if (is_looping_) return;

    // Enemy bullets hitting player
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active || bullets_[b].is_player) continue;

        if (std::abs(bullets_[b].x - player_x_) < 0.9f &&
            std::abs(bullets_[b].y - player_y_) < 0.9f) {
            bullets_[b].active = false;
            if (has_wingmen_) {
                has_wingmen_ = false; // Wingmen take the hit!
            } else {
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }

    // Direct collision with planes
    for (int i = 0; i < MAX_PLANES; ++i) {
        if (!planes_[i].active) continue;
        if (std::abs(planes_[i].x - player_x_) < 1.0f &&
            std::abs(planes_[i].y - player_y_) < 1.0f) {
            planes_[i].active = false;
            if (has_wingmen_) {
                has_wingmen_ = false;
            } else {
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game056_1942::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Pacific Ocean deep water with wave crests
    int wave_offset = static_cast<int>(scroll_y_) % 6;
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            // Ocean blue
            fb[idx] = 10;
            fb[idx + 1] = 40;
            fb[idx + 2] = 120;

            if ((y + wave_offset) % 5 == 0 && (x % 4 == 0)) {
                // Wave foam
                fb[idx] = 40;
                fb[idx + 1] = 90;
                fb[idx + 2] = 180;
            }
        }
    }

    // Render Planes
    for (int i = 0; i < MAX_PLANES; ++i) {
        if (!planes_[i].active) continue;
        int px = static_cast<int>(std::round(planes_[i].x));
        int py = static_cast<int>(std::round(planes_[i].y));
        if (px >= 0 && px < 16 && py >= 0 && py < 16) {
            int idx = (py * 16 + px) * 3;
            if (planes_[i].type == 1) {
                fb[idx] = 255;
                fb[idx + 1] = 40;
                fb[idx + 2] = 40; // Red formation plane
            } else {
                fb[idx] = 40;
                fb[idx + 1] = 180;
                fb[idx + 2] = 50; // Green Zero
            }
        }
    }

    // Render Boss (Ayako Heavy Bomber: 3x2 Dark Green / Bronze Fortress)
    if (boss_active_) {
        int bx = static_cast<int>(std::round(boss_x_));
        int by = static_cast<int>(std::round(boss_y_));
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dx = -2; dx <= 2; ++dx) {
                int px = bx + dx;
                int py = by + dy;
                if (px >= 0 && px < 16 && py >= 0 && py < 16) {
                    int idx = (py * 16 + px) * 3;
                    fb[idx] = 150;
                    fb[idx + 1] = 120;
                    fb[idx + 2] = 40;
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
                fb[idx + 1] = 255;
                fb[idx + 2] = 80; // Yellow bullet
            } else {
                fb[idx] = 255;
                fb[idx + 1] = 40;
                fb[idx + 2] = 40; // Red bullet
            }
        }
    }

    // Render Player (P-38 Lightning: Silver dual-fuselage plane)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));

    if (is_looping_) {
        // Stunt loop animation: shrinking / flashing white halo
        if (px >= 0 && px < 16 && py >= 0 && py < 16) {
            int idx = (py * 16 + px) * 3;
            fb[idx] = 255;
            fb[idx + 1] = 255;
            fb[idx + 2] = 255; // White loop-the-loop flash
        }
    } else {
        if (px >= 0 && px < 16 && py >= 0 && py < 16) {
            int idx = (py * 16 + px) * 3;
            fb[idx] = 220;
            fb[idx + 1] = 220;
            fb[idx + 2] = 240; // Silver fuselage

            // Wingmen (2 tiny escort planes)
            if (has_wingmen_) {
                if (px > 1) {
                    int left_idx = (py * 16 + (px - 2)) * 3;
                    fb[left_idx] = 180;
                    fb[left_idx + 1] = 200;
                    fb[left_idx + 2] = 255;
                }
                if (px < 14) {
                    int right_idx = (py * 16 + (px + 2)) * 3;
                    fb[right_idx] = 180;
                    fb[right_idx + 1] = 200;
                    fb[right_idx + 2] = 255;
                }
            }
        }
    }

    // HUD: Lives & Loops Remaining on row 0
    for (int l = 0; l < lives_ && l < 3; ++l) {
        int idx = l * 3;
        fb[idx] = 0;
        fb[idx + 1] = 255;
        fb[idx + 2] = 0;
    }

    for (int r = 0; r < loops_remaining_; ++r) {
        int idx = (15 - r) * 3;
        fb[idx] = 255;
        fb[idx + 1] = 200;
        fb[idx + 2] = 0; // Yellow loop pips
    }
}

} // namespace arcade
