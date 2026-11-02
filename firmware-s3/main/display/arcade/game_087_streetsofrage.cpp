#include "game_087_streetsofrage.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace arcade {

Game087StreetsOfRage::Game087StreetsOfRage() {
    Reset();
}

void Game087StreetsOfRage::Init() {
    Reset();
}

void Game087StreetsOfRage::Reset() {
    state_ = STATE_STREET_BRAWL;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    hero_hp_ = 100;
    backup_calls_ = 1;
    thugs_defeated_ = 0;
    ResetStage();
}

void Game087StreetsOfRage::ResetStage() {
    px_ = 3.5f;
    py_ = 10.5f;
    facing_ = 1;
    atk_state_ = ATK_NONE;
    atk_timer_ = 0.0f;

    for (int i = 0; i < MAX_THUGS; ++i) {
        thugs_[i].active = true;
        thugs_[i].x = 13.0f + i * 3.5f;
        thugs_[i].y = 8.5f + (i * 2.0f);
        thugs_[i].vx = -2.2f;
        thugs_[i].hp = 3;
        thugs_[i].is_boss = false;
        thugs_[i].respawn_timer = 0.0f;
    }

    rocket_x_ = 0.0f;
    rocket_y_ = 14.0f;
    explosion_timer_ = 0.0f;
}

void Game087StreetsOfRage::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_HERO_DEAD || state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.5f && (buttons & (BUTTON_A | BUTTON_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_POLICE_BACKUP) {
        UpdatePoliceBackup(dt);
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateThugs(dt);
    CheckCombat();

    if (thugs_defeated_ >= 7) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 10000;
    }
}

void Game087StreetsOfRage::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_speed = 5.0f;

    if (atk_timer_ > 0.0f) {
        atk_timer_ -= dt;
        if (atk_timer_ <= 0.0f) {
            atk_state_ = ATK_NONE;
        }
        return;
    }

    // Call Police Backup (A + B)
    if ((buttons & BUTTON_A) && (buttons & BUTTON_B) &&
        (!(prev_buttons & BUTTON_A) || !(prev_buttons & BUTTON_B))) {
        if (backup_calls_ > 0) {
            backup_calls_--;
            state_ = STATE_POLICE_BACKUP;
            state_timer_ = 0.0f;
            rocket_x_ = 1.0f;
            rocket_y_ = 13.0f;
            explosion_timer_ = 0.0f;
            return;
        }
    }

    // Jump Kick (Button B)
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        atk_state_ = ATK_FLYING_KICK;
        atk_timer_ = 0.35f;
        px_ += facing_ * 1.5f;
        return;
    }

    // Punch or Suplex (Button A)
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        // Check if behind an enemy for German Suplex
        bool suplexed = false;
        for (int i = 0; i < MAX_THUGS; ++i) {
            if (!thugs_[i].active) continue;
            float dx = (thugs_[i].x - px_) * facing_;
            float dy = std::abs(thugs_[i].y - py_);

            // If behind enemy (same direction) within 0.9 units
            if (dx > 0.0f && dx < 0.9f && dy < 0.8f) {
                atk_state_ = ATK_SUPLEX;
                atk_timer_ = 0.45f;
                thugs_[i].hp -= 3;
                thugs_[i].x -= facing_ * 3.0f; // Thrown overhead behind hero!
                score_ += 600;
                suplexed = true;
                if (thugs_[i].hp <= 0) {
                    thugs_[i].active = false;
                    thugs_[i].respawn_timer = 2.0f;
                    thugs_defeated_++;
                }
                break;
            }
        }

        if (!suplexed) {
            atk_state_ = ATK_PUNCH;
            atk_timer_ = 0.22f;
        }
        return;
    }

    // Walk
    if (buttons & BUTTON_LEFT)  { px_ -= move_speed * dt; facing_ = -1; }
    if (buttons & BUTTON_RIGHT) { px_ += move_speed * dt; facing_ = 1; }
    if (buttons & BUTTON_UP)    py_ -= (move_speed * 0.7f) * dt;
    if (buttons & BUTTON_DOWN)  py_ += (move_speed * 0.7f) * dt;

    px_ = std::max(1.0f, std::min(14.5f, px_));
    py_ = std::max(7.5f, std::min(13.5f, py_));
}

void Game087StreetsOfRage::UpdateThugs(float dt) {
    for (int i = 0; i < MAX_THUGS; ++i) {
        if (!thugs_[i].active) {
            if (thugs_[i].respawn_timer > 0.0f) {
                thugs_[i].respawn_timer -= dt;
                if (thugs_[i].respawn_timer <= 0.0f && thugs_defeated_ + i < 6) {
                    thugs_[i].active = true;
                    thugs_[i].x = 15.5f;
                    thugs_[i].y = 8.0f + (i * 2.0f);
                    thugs_[i].hp = 3;
                    thugs_[i].is_boss = false;
                } else if (thugs_[i].respawn_timer <= 0.0f && thugs_defeated_ >= 5 && !thugs_[0].is_boss) {
                    // Spawn Stage Boss Antonio!
                    thugs_[i].active = true;
                    thugs_[i].x = 15.0f;
                    thugs_[i].y = 10.0f;
                    thugs_[i].hp = 8;
                    thugs_[i].is_boss = true;
                }
            }
            continue;
        }

        if (thugs_[i].x > px_ + 1.2f) {
            thugs_[i].x -= 2.2f * dt;
        } else if (thugs_[i].x < px_ - 1.2f) {
            thugs_[i].x += 2.2f * dt;
        }

        if (thugs_[i].y > py_ + 0.3f) {
            thugs_[i].y -= 1.2f * dt;
        } else if (thugs_[i].y < py_ - 0.3f) {
            thugs_[i].y += 1.2f * dt;
        }
    }
}

void Game087StreetsOfRage::CheckCombat() {
    // Punch / Kick combat
    if (atk_state_ == ATK_PUNCH || atk_state_ == ATK_FLYING_KICK) {
        float reach = (atk_state_ == ATK_FLYING_KICK) ? 2.2f : 1.6f;
        int dmg = (atk_state_ == ATK_FLYING_KICK) ? 2 : 1;

        for (int i = 0; i < MAX_THUGS; ++i) {
            if (!thugs_[i].active) continue;
            float dx = (thugs_[i].x - px_) * facing_;
            float dy = std::abs(thugs_[i].y - py_);

            if (dx > 0.0f && dx < reach && dy < 1.2f) {
                thugs_[i].hp -= dmg;
                thugs_[i].x += facing_ * 1.5f;
                score_ += 200;

                if (thugs_[i].hp <= 0) {
                    thugs_[i].active = false;
                    thugs_[i].respawn_timer = 2.0f;
                    thugs_defeated_++;
                    score_ += thugs_[i].is_boss ? 5000 : 300;
                }
            }
        }
    }

    // Thugs damage hero
    for (int i = 0; i < MAX_THUGS; ++i) {
        if (!thugs_[i].active) continue;
        if (std::abs(thugs_[i].x - px_) < 1.2f && std::abs(thugs_[i].y - py_) < 1.0f) {
            hero_hp_ -= thugs_[i].is_boss ? 2 : 1;
            if (hero_hp_ <= 0) {
                lives_--;
                if (lives_ > 0) {
                    hero_hp_ = 100;
                    px_ = 3.5f;
                    py_ = 10.5f;
                } else {
                    state_ = STATE_HERO_DEAD;
                    state_timer_ = 0.0f;
                }
                return;
            }
        }
    }
}

void Game087StreetsOfRage::UpdatePoliceBackup(float dt) {
    if (explosion_timer_ == 0.0f) {
        // Rocket flies in arc toward center
        rocket_x_ += 16.0f * dt;
        rocket_y_ -= 6.0f * dt;

        if (rocket_x_ >= 8.0f) {
            // Detonate full-screen napalm barrage!
            explosion_timer_ = 1.2f;

            // Deal 6 damage to all thugs
            for (int i = 0; i < MAX_THUGS; ++i) {
                if (!thugs_[i].active) continue;
                thugs_[i].hp -= 6;
                if (thugs_[i].hp <= 0) {
                    thugs_[i].active = false;
                    thugs_[i].respawn_timer = 2.0f;
                    thugs_defeated_++;
                    score_ += thugs_[i].is_boss ? 5000 : 400;
                }
            }
        }
    } else {
        explosion_timer_ -= dt;
        if (explosion_timer_ <= 0.0f) {
            state_ = STATE_STREET_BRAWL;
            state_timer_ = 0.0f;
        }
    }
}

void Game087StreetsOfRage::Render(uint8_t* fb) {
    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Neon City Skyline (y: 0..6)
    for (int y = 0; y < 7; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 10, 15, 30);
        }
    }
    // Neon Signs
    set_pixel(3, 2, 255, 30, 120); // Pink neon
    set_pixel(4, 2, 255, 30, 120);
    set_pixel(12, 3, 30, 220, 255); // Cyan neon

    // 2. Wet Asphalt Street (y: 7..14)
    for (int y = 7; y < 15; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 35, 35, 40);
        }
    }

    // 3. Police Backup Explosion or Rocket
    if (state_ == STATE_POLICE_BACKUP) {
        if (explosion_timer_ > 0.0f) {
            // Full screen napalm firestorm!
            for (int y = 5; y < 15; ++y) {
                for (int x = 0; x < 16; ++x) {
                    if ((x + y) % 2 == 0) {
                        set_pixel(x, y, 255, 140, 20);
                    } else {
                        set_pixel(x, y, 255, 40, 20);
                    }
                }
            }
        } else {
            // Police cruiser on lower left corner
            set_pixel(0, 14, 240, 240, 250);
            set_pixel(1, 14, 20, 20, 20);
            set_pixel(0, 13, 255, 20, 20); // Red siren
            // Flying rocket
            int rx = static_cast<int>(std::round(rocket_x_));
            int ry = static_cast<int>(std::round(rocket_y_));
            set_pixel(rx, ry, 255, 255, 100);
            set_pixel(rx - 1, ry + 1, 255, 120, 0); // exhaust
        }
    }

    // 4. Thugs (Garcia in leather jacket or Boss in red)
    for (int i = 0; i < MAX_THUGS; ++i) {
        if (!thugs_[i].active) continue;
        int ex = static_cast<int>(std::round(thugs_[i].x));
        int ey = static_cast<int>(std::round(thugs_[i].y));

        if (thugs_[i].is_boss) {
            set_pixel(ex, ey, 220, 30, 40);       // Red trench coat
            set_pixel(ex, ey - 1, 240, 180, 140);
            set_pixel(ex - 1, ey - 1, 220, 220, 255); // Claws
        } else {
            set_pixel(ex, ey, 200, 160, 40);      // Yellow vest
            set_pixel(ex, ey - 1, 240, 180, 140);
            set_pixel(ex, ey - 2, 40, 40, 40);    // Bandana
        }
    }

    // 5. Hero Axel Stone (White T-shirt, Blue jeans & Red headband)
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));

    set_pixel(px, py, 40, 100, 220);      // Blue denim
    set_pixel(px, py - 1, 250, 250, 250); // White shirt
    set_pixel(px, py - 2, 240, 180, 140); // Face
    set_pixel(px, py - 3, 255, 30, 30);   // Red Headband

    if (atk_state_ == ATK_PUNCH) {
        set_pixel(px + facing_, py - 1, 255, 200, 120);
    } else if (atk_state_ == ATK_FLYING_KICK) {
        set_pixel(px + facing_ * 2, py - 1, 40, 100, 220); // Kick leg
    } else if (atk_state_ == ATK_SUPLEX) {
        set_pixel(px - facing_, py - 1, 255, 140, 40); // Overhead throw
    }

    // 6. HUD (y = 15)
    int hp_bars = std::max(0, std::min(8, hero_hp_ / 12));
    for (int b = 0; b < hp_bars; ++b) {
        set_pixel(b, 15, 50, 220, 50);
    }
    // Police Backup Badge Icon
    if (backup_calls_ > 0) {
        set_pixel(15, 15, 255, 200, 0); // Gold badge
        set_pixel(14, 15, 20, 100, 255); // Blue siren
    }
}

} // namespace arcade
