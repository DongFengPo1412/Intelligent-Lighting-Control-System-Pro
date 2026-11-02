#include "game_090_sunsetriders.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game090SunsetRiders::Game090SunsetRiders() {
    Init();
}

void Game090SunsetRiders::Init() {
    ResetMission(true);
}

void Game090SunsetRiders::Reset() {
    ResetMission(true);
}

void Game090SunsetRiders::ResetMission(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        stage_ = 1;
        has_dual_guns_ = false;
        has_rapid_fire_ = false;
    }
    state_ = STATE_SALOON_BRAWL;
    state_timer_ = 0.0f;
    bandits_defeated_ = 0;

    px_ = 2.5f;
    py_ = 13.0f;
    vy_ = 0.0f;
    facing_ = 1;
    on_ground_ = true;
    is_sliding_ = false;
    slide_timer_ = 0.0f;
    fire_cooldown_ = 0.0f;

    badge_x_ = 8.0f;
    badge_y_ = 8.0f;
    badge_active_ = true;
    badge_type_ = (stage_ % 2 == 1) ? 0 : 1;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    for (int i = 0; i < MAX_BANDITS; ++i) {
        bandits_[i].active = true;
        bandits_[i].hp = 1;
        bandits_[i].shoot_timer = 0.8f + i * 0.7f;
        bandits_[i].respawn_timer = 0.0f;
        if (i == 0) {
            bandits_[i].x = 13.5f;
            bandits_[i].y = 13.0f; // ground
        } else if (i == 1) {
            bandits_[i].x = 12.0f;
            bandits_[i].y = 8.0f;  // balcony
        } else {
            bandits_[i].x = 5.0f;
            bandits_[i].y = 8.0f;  // saloon roof
        }
    }

    for (int i = 0; i < MAX_BULLS; ++i) {
        bulls_[i].active = false;
        bulls_[i].x = 18.0f + i * 5.0f;
        bulls_[i].y = 13.0f;
        bulls_[i].vx = -4.5f;
    }
}

void Game090SunsetRiders::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_HERO_HIT) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetMission(false);
            }
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.2f) {
            stage_++;
            ResetMission(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetMission(true);
        }
        return;
    }

    // STATE_SALOON_BRAWL or STATE_STAMPEDE
    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateBullets(dt);

    if (state_ == STATE_STAMPEDE) {
        UpdateBulls(dt);
    } else {
        UpdateBandits(dt);
        if (bandits_defeated_ >= 3 && bandits_defeated_ < 6) {
            // Trigger wild stampede wave
            state_ = STATE_STAMPEDE;
            state_timer_ = 0.0f;
            for (int i = 0; i < MAX_BULLS; ++i) {
                bulls_[i].active = true;
                bulls_[i].x = 17.0f + i * 5.5f;
            }
        }
    }

    CheckCombat();

    if (bandits_defeated_ >= 6) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 2000;
    }
}

void Game090SunsetRiders::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (fire_cooldown_ > 0.0f) fire_cooldown_ -= dt;

    // Slide Dodge (Down + Button A)
    if ((buttons & BTN_DOWN) && (buttons & BTN_A) && on_ground_) {
        if (!is_sliding_) {
            is_sliding_ = true;
            slide_timer_ = 0.35f;
        }
    }

    if (is_sliding_) {
        slide_timer_ -= dt;
        px_ += facing_ * 9.0f * dt;
        if (slide_timer_ <= 0.0f) {
            is_sliding_ = false;
        }
    } else {
        // Horizontal Movement
        float move_speed = 6.0f;
        if (buttons & BTN_LEFT) {
            px_ -= move_speed * dt;
            facing_ = -1;
        }
        if (buttons & BTN_RIGHT) {
            px_ += move_speed * dt;
            facing_ = 1;
        }

        // Jump & Floor transitions (Button B)
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            if (on_ground_) {
                if ((buttons & BTN_UP) && py_ >= 12.0f) {
                    // Leap up to balcony floor
                    vy_ = -14.0f;
                    on_ground_ = false;
                } else if ((buttons & BTN_DOWN) && py_ <= 9.0f) {
                    // Drop down through wooden balcony floor
                    py_ += 1.0f;
                    vy_ = 1.0f;
                    on_ground_ = false;
                } else {
                    // Standard vertical jump
                    vy_ = -5.8f;
                    on_ground_ = false;
                }
            }
        }
    }

    float prev_py = py_;
    // Gravity
    if (!on_ground_) {
        vy_ += 16.0f * dt;
        py_ += vy_ * dt;
    }

    // Platform collisions
    if (py_ >= 13.0f) {
        py_ = 13.0f;
        vy_ = 0.0f;
        on_ground_ = true;
    } else {
        // Balcony platform at y=8.0f
        if (vy_ >= 0.0f && prev_py <= 8.0f && py_ >= 8.0f) {
            if (px_ >= 3.0f && px_ <= 14.5f) {
                py_ = 8.0f;
                vy_ = 0.0f;
                on_ground_ = true;
            }
        }
    }

    px_ = std::clamp(px_, 1.0f, 15.0f);

    // Revolver Shoot (Button A alone, when not initiating slide)
    if ((buttons & BTN_A) && !(buttons & BTN_DOWN)) {
        bool can_fire = has_rapid_fire_ ? (fire_cooldown_ <= 0.0f) : (!(prev_buttons & BTN_A) && fire_cooldown_ <= 0.0f);
        if (can_fire) {
            fire_cooldown_ = has_rapid_fire_ ? 0.18f : 0.28f;

            // Primary horizontal shot
            for (int i = 0; i < MAX_BULLETS; ++i) {
                if (!bullets_[i].active) {
                    bullets_[i].active = true;
                    bullets_[i].is_enemy = false;
                    bullets_[i].x = px_ + facing_ * 0.8f;
                    bullets_[i].y = py_ - 0.5f;
                    bullets_[i].vx = facing_ * 12.0f;
                    bullets_[i].vy = 0.0f;
                    break;
                }
            }

            // Dual Gun: Secondary diagonal upward shot
            if (has_dual_guns_) {
                for (int i = 0; i < MAX_BULLETS; ++i) {
                    if (!bullets_[i].active) {
                        bullets_[i].active = true;
                        bullets_[i].is_enemy = false;
                        bullets_[i].x = px_ + facing_ * 0.8f;
                        bullets_[i].y = py_ - 0.7f;
                        bullets_[i].vx = facing_ * 10.0f;
                        bullets_[i].vy = -5.0f;
                        break;
                    }
                }
            }
        }
    }

    // Collect Sheriff Badge item
    if (badge_active_) {
        float dx = std::fabs(px_ - badge_x_);
        float dy = std::fabs(py_ - badge_y_);
        if (dx < 1.2f && dy < 1.2f) {
            badge_active_ = false;
            score_ += 100;
            if (badge_type_ == 0) {
                has_dual_guns_ = true;
            } else {
                has_rapid_fire_ = true;
            }
        }
    }
}

void Game090SunsetRiders::UpdateBandits(float dt) {
    for (int i = 0; i < MAX_BANDITS; ++i) {
        Bandit& b = bandits_[i];
        if (!b.active) {
            if (b.respawn_timer > 0.0f) {
                b.respawn_timer -= dt;
            } else {
                b.active = true;
                b.hp = 1;
                b.shoot_timer = 1.0f + (rand() % 10) * 0.1f;
                b.x = 11.0f + (float)(rand() % 4);
                b.y = (i == 0) ? 13.0f : 8.0f;
            }
            continue;
        }

        b.shoot_timer -= dt;
        if (b.shoot_timer <= 0.0f) {
            b.shoot_timer = 1.5f + (rand() % 5) * 0.2f;
            // Bandit fires bullet left towards player
            for (int k = 0; k < MAX_BULLETS; ++k) {
                if (!bullets_[k].active) {
                    bullets_[k].active = true;
                    bullets_[k].is_enemy = true;
                    bullets_[k].x = b.x - 0.8f;
                    bullets_[k].y = b.y - 0.4f;
                    bullets_[k].vx = -6.5f;
                    bullets_[k].vy = 0.0f;
                    break;
                }
            }
        }
    }
}

void Game090SunsetRiders::UpdateBulls(float dt) {
    bool all_cleared = true;
    for (int i = 0; i < MAX_BULLS; ++i) {
        Bull& bull = bulls_[i];
        if (!bull.active) continue;

        bull.x += bull.vx * dt;
        if (bull.x < -3.0f) {
            bull.active = false;
        } else {
            all_cleared = false;
        }
    }

    if (all_cleared) {
        // Stampede survived!
        state_ = STATE_SALOON_BRAWL;
        score_ += 500;
        bandits_defeated_ = 4; // allow final wave to spawn
    }
}

void Game090SunsetRiders::UpdateBullets(float dt) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        Bullet& b = bullets_[i];
        if (!b.active) continue;

        b.x += b.vx * dt;
        b.y += b.vy * dt;

        if (b.x < -1.0f || b.x > 17.0f || b.y < -1.0f || b.y > 17.0f) {
            b.active = false;
        }
    }
}

void Game090SunsetRiders::CheckCombat() {
    // 1. Player bullets vs Bandits
    for (int b_idx = 0; b_idx < MAX_BULLETS; ++b_idx) {
        Bullet& b = bullets_[b_idx];
        if (!b.active || b.is_enemy) continue;

        for (int m_idx = 0; m_idx < MAX_BANDITS; ++m_idx) {
            Bandit& bandit = bandits_[m_idx];
            if (!bandit.active) continue;

            float dx = std::fabs(b.x - bandit.x);
            float dy = std::fabs(b.y - bandit.y);

            if (dx < 1.1f && dy < 1.2f) {
                b.active = false;
                bandit.hp--;
                if (bandit.hp <= 0) {
                    bandit.active = false;
                    bandit.respawn_timer = 2.0f;
                    score_ += 200;
                    bandits_defeated_++;
                }
                break;
            }
        }
    }

    // 2. Enemy bullets vs Hero
    for (int b_idx = 0; b_idx < MAX_BULLETS; ++b_idx) {
        Bullet& b = bullets_[b_idx];
        if (!b.active || !b.is_enemy) continue;

        float dx = std::fabs(b.x - px_);
        float dy = std::fabs(b.y - py_);

        if (dx < 1.0f) {
            // If hero is sliding under bullet, high bullet (dy around 0.4 to 1.0) flies right over!
            if (is_sliding_) {
                // Bullet dodged successfully!
                continue;
            }

            if (dy < 1.1f) {
                b.active = false;
                state_ = STATE_HERO_HIT;
                state_timer_ = 0.0f;
                return;
            }
        }
    }

    // 3. Stampeding Bulls vs Hero
    if (state_ == STATE_STAMPEDE) {
        for (int i = 0; i < MAX_BULLS; ++i) {
            Bull& bull = bulls_[i];
            if (!bull.active) continue;

            float dx = std::fabs(bull.x - px_);
            float dy = py_ - bull.y; // hero height relative to bull

            if (dx < 1.3f) {
                // If hero jumped on top of bull back (py between 10.5 and 12.0)
                if (py_ <= 12.0f && py_ >= 10.0f && vy_ >= 0.0f) {
                    // Safe! Hero bounces on bull's back
                    vy_ = -5.5f;
                    on_ground_ = false;
                    score_ += 30; // Cow-hopping points
                } else if (py_ > 12.0f) {
                    // Trampled by bull!
                    state_ = STATE_HERO_HIT;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }
    }
}

void Game090SunsetRiders::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Sunset Sky & Desert Saloon Background
    for (int y = 0; y < 7; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 160 + y * 10, 80 + y * 5, 20); // Sunset gradient
        }
    }

    // Saloon 2nd floor balcony (y=9)
    for (int x = 3; x <= 14; ++x) {
        set_pixel(x, 9, 139, 69, 19);  // Wood platform
    }
    // Saloon support pillars
    set_pixel(4, 10, 100, 50, 15);
    set_pixel(4, 11, 100, 50, 15);
    set_pixel(4, 12, 100, 50, 15);
    set_pixel(13, 10, 100, 50, 15);
    set_pixel(13, 11, 100, 50, 15);
    set_pixel(13, 12, 100, 50, 15);

    // Ground Dirt (y=14 and 15)
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 14, 180, 130, 70);
        set_pixel(x, 15, 120, 80, 40);
    }

    // Sheriff Badge Item
    if (badge_active_) {
        int bx = (int)std::round(badge_x_);
        int by = (int)std::round(badge_y_);
        if (badge_type_ == 0) {
            set_pixel(bx, by, 255, 220, 0); // Gold Star Badge
        } else {
            set_pixel(bx, by, 220, 230, 255); // Silver Star Badge
        }
    }

    // Bulls during stampede
    if (state_ == STATE_STAMPEDE) {
        for (int i = 0; i < MAX_BULLS; ++i) {
            const Bull& bull = bulls_[i];
            if (!bull.active) continue;
            int bx = (int)std::round(bull.x);
            int by = (int)std::round(bull.y);
            set_pixel(bx, by, 110, 50, 20);       // bull body
            set_pixel(bx + 1, by, 110, 50, 20);
            set_pixel(bx - 1, by, 80, 35, 15);     // bull head
            set_pixel(bx - 1, by - 1, 230, 230, 200); // horns
        }
    }

    // Bandits
    for (int i = 0; i < MAX_BANDITS; ++i) {
        const Bandit& b = bandits_[i];
        if (!b.active) continue;
        int bx = (int)std::round(b.x);
        int by = (int)std::round(b.y);
        set_pixel(bx, by, 160, 40, 40);      // Red vest
        set_pixel(bx, by - 1, 220, 160, 120);// face
        set_pixel(bx, by - 2, 60, 30, 10);   // bandit hat
        set_pixel(bx - 1, by - 1, 40, 40, 40); // gun
    }

    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        const Bullet& b = bullets_[i];
        if (!b.active) continue;
        int bx = (int)std::round(b.x);
        int by = (int)std::round(b.y);
        if (b.is_enemy) {
            set_pixel(bx, by, 255, 50, 0); // enemy red bullet
        } else {
            set_pixel(bx, by, 255, 255, 100); // player yellow bullet
        }
    }

    // Cowboy Hero (Steve / Billy)
    int px = (int)std::round(px_);
    int py = (int)std::round(py_);

    if (state_ == STATE_HERO_HIT) {
        set_pixel(px, py, 255, 50, 0);
        set_pixel(px, py - 1, 255, 200, 0);
    } else {
        if (is_sliding_) {
            // Low dust sliding pose
            set_pixel(px, py, 30, 100, 220);       // Blue poncho/jeans
            set_pixel(px + facing_, py, 220, 170, 130);
            set_pixel(px - facing_, py, 200, 180, 100); // dust cloud
        } else {
            // Standing cowboy
            set_pixel(px, py, 30, 100, 220);        // blue jeans
            set_pixel(px, py - 1, 220, 170, 130);   // yellow/tan shirt
            set_pixel(px, py - 2, 180, 120, 40);    // cowboy hat
            set_pixel(px + facing_, py - 1, 240, 240, 240); // silver revolver
            if (has_dual_guns_) {
                set_pixel(px - facing_, py - 1, 240, 240, 240); // second revolver
            }
        }
    }

    // Top HUD
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 255, 50, 50);
    }
    if (has_dual_guns_) {
        set_pixel(14, 0, 255, 220, 0); // Gold badge indicator
    }
    if (has_rapid_fire_) {
        set_pixel(15, 0, 220, 230, 255); // Silver badge indicator
    }
}

} // namespace arcade
