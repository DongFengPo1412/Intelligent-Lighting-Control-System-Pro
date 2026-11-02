#include "game_084_warriorsoffate.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace arcade {

Game084WarriorsOfFate::Game084WarriorsOfFate() {
    Reset();
}

void Game084WarriorsOfFate::Init() {
    Reset();
}

void Game084WarriorsOfFate::Reset() {
    state_ = STATE_BATTLE;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    hero_hp_ = 100;
    enemies_defeated_ = 0;
    mounted_ = true;
    ResetBattle();
}

void Game084WarriorsOfFate::ResetBattle() {
    hx_ = 3.0f;
    hy_ = 10.0f;
    facing_ = 1;
    charging_ = false;
    charge_timer_ = 0.0f;
    atk_timer_ = 0.0f;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = true;
        enemies_[i].x = 14.0f + i * 3.5f;
        enemies_[i].y = 8.5f + (i * 2.0f);
        enemies_[i].vx = -2.2f;
        enemies_[i].hp = 2;
        enemies_[i].is_boss = false;
    }
}

void Game084WarriorsOfFate::StartBonusStage() {
    state_ = STATE_EATING_BONUS;
    state_timer_ = 0.0f;
    baozi_eaten_ = 0;
    eating_timer_ = 8.0f;
}

void Game084WarriorsOfFate::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_HERO_DEAD || state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.5f && (buttons & (BUTTON_A | BUTTON_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_EATING_BONUS) {
        UpdateEating(dt, buttons, prev_buttons);
        return;
    }

    UpdateHero(dt, buttons, prev_buttons);
    UpdateEnemies(dt);
    CheckAttacks();
}

void Game084WarriorsOfFate::UpdateHero(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_speed = mounted_ ? 6.5f : 4.2f;

    if (charging_) {
        charge_timer_ -= dt;
        hx_ += facing_ * 12.0f * dt;
        if (charge_timer_ <= 0.0f) {
            charging_ = false;
        }
    } else {
        if (buttons & BUTTON_LEFT)  { hx_ -= move_speed * dt; facing_ = -1; }
        if (buttons & BUTTON_RIGHT) { hx_ += move_speed * dt; facing_ = 1; }
        if (buttons & BUTTON_UP)    hy_ -= (move_speed * 0.7f) * dt;
        if (buttons & BUTTON_DOWN)  hy_ += (move_speed * 0.7f) * dt;

        hx_ = std::max(1.0f, std::min(14.5f, hx_));
        hy_ = std::max(8.0f, std::min(13.5f, hy_));

        // Horse rear stampede or remount (Button B)
        if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
            if (mounted_) {
                atk_timer_ = 0.3f;
                // Stampede clears close enemies
                for (int i = 0; i < MAX_ENEMIES; ++i) {
                    if (enemies_[i].active && std::abs(enemies_[i].x - hx_) < 2.0f && std::abs(enemies_[i].y - hy_) < 1.5f) {
                        enemies_[i].hp--;
                        enemies_[i].x += facing_ * 2.0f; // Knockback
                    }
                }
            } else {
                mounted_ = true; // Remount warhorse
            }
        }
    }

    if (atk_timer_ > 0.0f) {
        atk_timer_ -= dt;
    }

    // Long Spear Thrust / Cavalry Charge (Button A)
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        atk_timer_ = 0.25f;
        if (mounted_ && ((facing_ == 1 && (buttons & BUTTON_RIGHT)) || (facing_ == -1 && (buttons & BUTTON_LEFT)))) {
            charging_ = true;
            charge_timer_ = 0.35f;
        }
    }
}

void Game084WarriorsOfFate::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) {
            if (enemies_defeated_ < 6) {
                enemies_[i].active = true;
                enemies_[i].x = 15.5f;
                enemies_[i].y = 8.0f + (std::rand() % 5);
                enemies_[i].hp = 2;
                enemies_[i].is_boss = false;
            } else if (enemies_defeated_ == 6) {
                // Spawn Enemy General Boss!
                enemies_[i].active = true;
                enemies_[i].x = 15.0f;
                enemies_[i].y = 10.0f;
                enemies_[i].hp = 8;
                enemies_[i].is_boss = true;
                enemies_defeated_++; // Marks boss spawned
            }
            continue;
        }

        // Enemy moves toward hero
        if (enemies_[i].x > hx_ + 1.4f) {
            enemies_[i].x -= 2.2f * dt;
        } else if (enemies_[i].x < hx_ - 1.4f) {
            enemies_[i].x += 2.2f * dt;
        }

        if (enemies_[i].y > hy_ + 0.3f) {
            enemies_[i].y -= 1.2f * dt;
        } else if (enemies_[i].y < hy_ - 0.3f) {
            enemies_[i].y += 1.2f * dt;
        }
    }
}

void Game084WarriorsOfFate::CheckAttacks() {
    // 1. Hero attacks enemies
    if (atk_timer_ > 0.05f || charging_) {
        float reach = mounted_ ? 2.6f : 1.6f;
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (!enemies_[i].active) continue;

            float dx = (enemies_[i].x - hx_) * facing_;
            float dy = std::abs(enemies_[i].y - hy_);

            if (dx > 0.0f && dx < reach && dy < 1.4f) {
                int dmg = charging_ ? 2 : 1;
                enemies_[i].hp -= dmg;
                enemies_[i].x += facing_ * 1.5f; // Pushback

                if (enemies_[i].hp <= 0) {
                    enemies_[i].active = false;
                    score_ += enemies_[i].is_boss ? 3000 : 300;
                    if (enemies_[i].is_boss) {
                        StartBonusStage();
                        return;
                    } else {
                        enemies_defeated_++;
                    }
                }
            }
        }
    }

    // 2. Enemies damage hero
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        if (std::abs(enemies_[i].x - hx_) < 1.3f && std::abs(enemies_[i].y - hy_) < 1.0f) {
            hero_hp_ -= enemies_[i].is_boss ? 2 : 1;

            if (mounted_ && hero_hp_ < 50) {
                mounted_ = false; // Dismounted upon taking heavy damage!
            }

            if (hero_hp_ <= 0) {
                lives_--;
                if (lives_ > 0) {
                    hero_hp_ = 100;
                    mounted_ = true;
                    hx_ = 3.0f;
                    hy_ = 10.0f;
                } else {
                    state_ = STATE_HERO_DEAD;
                    state_timer_ = 0.0f;
                }
                return;
            }
        }
    }
}

void Game084WarriorsOfFate::UpdateEating(float dt, uint32_t buttons, uint32_t prev_buttons) {
    eating_timer_ -= dt;

    // Mash A or B to eat baozi
    if (((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) ||
        ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B))) {
        if (baozi_eaten_ < baozi_total_) {
            baozi_eaten_++;
            score_ += 250;
        }
    }

    if (baozi_eaten_ >= baozi_total_ || eating_timer_ <= 0.0f) {
        if (baozi_eaten_ >= baozi_total_) {
            score_ += 5000; // Perfect eating bonus!
        }
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game084WarriorsOfFate::Render(uint8_t* fb) {
    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    if (state_ == STATE_EATING_BONUS) {
        // Banquet Table
        for (int y = 0; y < 16; ++y) {
            for (int x = 0; x < 16; ++x) set_pixel(x, y, 40, 20, 15);
        }
        // Table surface
        for (int y = 8; y < 15; ++y) {
            for (int x = 2; x < 14; ++x) set_pixel(x, y, 160, 100, 50);
        }
        // Steamers of Baozi
        int remaining = baozi_total_ - baozi_eaten_;
        for (int i = 0; i < std::min(10, remaining); ++i) {
            set_pixel(3 + i, 9, 255, 255, 230);
            set_pixel(3 + i, 10, 240, 240, 200);
        }
        // Hero face eating
        set_pixel(7, 5, 240, 180, 140);
        set_pixel(8, 5, 240, 180, 140);
        set_pixel(7, 6, 20, 100, 40); // Guan Yu Green Robe
        return;
    }

    // 1. Ancient Battlefield Sunset Sky (y: 0..6)
    for (int y = 0; y < 7; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 90, 30, 20); // Crimson sunset
        }
    }
    // Fortress Wall Banners
    set_pixel(2, 4, 255, 200, 0);
    set_pixel(13, 4, 255, 40, 40);

    // 2. Earth Ground (y: 7..14)
    for (int y = 7; y < 15; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 80, 65, 45);
        }
    }

    // 3. Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));

        if (enemies_[i].is_boss) {
            // Boss General (Golden armor & Red cape)
            set_pixel(ex, ey, 220, 180, 40);
            set_pixel(ex, ey - 1, 255, 40, 40);
            set_pixel(ex - 1, ey, 240, 200, 50);
        } else {
            // Foot soldier (Blue armor)
            set_pixel(ex, ey, 50, 100, 200);
            set_pixel(ex, ey - 1, 240, 180, 140);
            set_pixel(ex - 1, ey, 180, 180, 180); // Spear tip
        }
    }

    // 4. Hero (Guan Yu in Green Robe & Red Hare Steed)
    int hx = static_cast<int>(std::round(hx_));
    int hy = static_cast<int>(std::round(hy_));

    if (mounted_) {
        // Red Hare Warhorse
        set_pixel(hx, hy, 180, 40, 30);            // Horse torso
        set_pixel(hx + facing_, hy, 210, 50, 40);   // Horse head
        set_pixel(hx - facing_, hy, 160, 30, 20);   // Flank
        // Hero on top
        set_pixel(hx, hy - 1, 30, 160, 50);         // Green Silk Robe
        set_pixel(hx, hy - 2, 200, 120, 80);        // Face / Black Beard
        // Guan Dao / Spear
        if (atk_timer_ > 0.0f || charging_) {
            set_pixel(hx + facing_ * 2, hy - 1, 240, 240, 255); // Blade gleam
            set_pixel(hx + facing_ * 3, hy - 1, 255, 255, 255);
        }
    } else {
        // Dismounted步战
        set_pixel(hx, hy, 30, 160, 50);
        set_pixel(hx, hy - 1, 200, 120, 80);
        if (atk_timer_ > 0.0f) {
            set_pixel(hx + facing_, hy, 255, 255, 255);
        }
    }

    // 5. HUD (y = 15)
    int hp_bars = std::max(0, std::min(8, hero_hp_ / 12));
    for (int b = 0; b < hp_bars; ++b) {
        set_pixel(b, 15, 50, 220, 50);
    }
    if (mounted_) {
        set_pixel(15, 15, 220, 50, 30); // Horse icon
    }
}

} // namespace arcade
