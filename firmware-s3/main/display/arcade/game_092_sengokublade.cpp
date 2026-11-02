#include "game_092_sengokublade.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game092SengokuBlade::Game092SengokuBlade() {
    Init();
}

void Game092SengokuBlade::Init() {
    ResetBattle(true);
}

void Game092SengokuBlade::Reset() {
    ResetBattle(true);
}

void Game092SengokuBlade::ResetBattle(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        bombs_ = 2;
        stage_ = 1;
    }
    state_ = STATE_AIR_BATTLE;
    state_timer_ = 0.0f;
    enemies_defeated_ = 0;

    px_ = 2.0f;
    py_ = 8.0f;
    charge_timer_ = 0.0f;
    is_charging_ = false;
    melee_timer_ = 0.0f;
    bomb_timer_ = 0.0f;
    fire_cooldown_ = 0.0f;
    cloud_scroll_ = 0.0f;

    for (int i = 0; i < MAX_HERO_BULLETS; ++i) {
        hero_bullets_[i].active = false;
    }
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
        enemy_bullets_[i].active = false;
    }

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = true;
        enemies_[i].hp = (i == 0) ? 4 : 2;
        enemies_[i].is_boss = (i == 0);
        enemies_[i].x = 12.0f + i * 1.5f;
        enemies_[i].y = 4.0f + i * 4.0f;
        enemies_[i].vy = (i % 2 == 0) ? 1.5f : -1.5f;
        enemies_[i].shoot_timer = 0.8f + i * 0.6f;
        enemies_[i].respawn_timer = 0.0f;
    }
}

void Game092SengokuBlade::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;
    cloud_scroll_ += 2.0f * dt;
    if (cloud_scroll_ >= 16.0f) cloud_scroll_ -= 16.0f;

    if (state_ == STATE_HERO_HIT) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetBattle(false);
            }
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.0f) {
            stage_++;
            ResetBattle(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetBattle(true);
        }
        return;
    }

    // STATE_AIR_BATTLE
    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateHeroProjectiles(dt);
    UpdateEnemies(dt);
    UpdateEnemyBullets(dt);
    CheckCombat();

    if (enemies_defeated_ >= 6) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1500;
    }
}

void Game092SengokuBlade::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (fire_cooldown_ > 0.0f) fire_cooldown_ -= dt;
    if (melee_timer_ > 0.0f) melee_timer_ -= dt;

    if (bomb_timer_ > 0.0f) {
        bomb_timer_ -= dt;
    }

    // 8-Way Flight
    float flight_speed = 6.5f;
    if (buttons & BTN_LEFT) px_ -= flight_speed * dt;
    if (buttons & BTN_RIGHT) px_ += flight_speed * dt;
    if (buttons & BTN_UP) py_ -= flight_speed * dt;
    if (buttons & BTN_DOWN) py_ += flight_speed * dt;

    px_ = std::clamp(px_, 1.0f, 14.5f);
    py_ = std::clamp(py_, 1.5f, 14.5f);

    // Button B: Ninja Mandala Bomb
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        if (bombs_ > 0 && bomb_timer_ <= 0.0f) {
            bombs_--;
            bomb_timer_ = 1.2f;
            score_ += 50;

            // Dissolve all enemy bullets
            for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
                if (enemy_bullets_[i].active) {
                    enemy_bullets_[i].active = false;
                    score_ += 100; // Gold bonus
                }
            }

            // Damage all active enemies
            for (int i = 0; i < MAX_ENEMIES; ++i) {
                if (enemies_[i].active) {
                    enemies_[i].hp -= 3;
                    if (enemies_[i].hp <= 0) {
                        enemies_[i].active = false;
                        enemies_[i].respawn_timer = 2.0f;
                        score_ += 300;
                        enemies_defeated_++;
                    }
                }
            }
        }
    }

    // Button A: Tap for Melee/Talisman, Hold for Shikigami Charge
    if (buttons & BTN_A) {
        charge_timer_ += dt;
        is_charging_ = true;
    } else {
        if (is_charging_) {
            // Released Button A!
            if (charge_timer_ >= 0.75f) {
                // Unleash Shikigami Familiar Charge Shot!
                for (int i = 0; i < MAX_HERO_BULLETS; ++i) {
                    if (!hero_bullets_[i].active) {
                        hero_bullets_[i].active = true;
                        hero_bullets_[i].is_charge_shot = true;
                        hero_bullets_[i].x = px_ + 1.2f;
                        hero_bullets_[i].y = py_;
                        hero_bullets_[i].vx = 14.0f;
                        hero_bullets_[i].vy = 0.0f;
                        score_ += 20;
                        break;
                    }
                }
            } else if (fire_cooldown_ <= 0.0f) {
                // Short tap: Check if near enemy for Close-Range Melee Katana Slash!
                bool nearby_enemy = false;
                for (int i = 0; i < MAX_ENEMIES; ++i) {
                    if (enemies_[i].active) {
                        float dx = enemies_[i].x - px_;
                        float dy = std::fabs(enemies_[i].y - py_);
                        if (dx > 0.0f && dx < 2.5f && dy < 1.4f) {
                            nearby_enemy = true;
                            break;
                        }
                    }
                }

                if (nearby_enemy) {
                    // Close-range Melee Slash!
                    melee_timer_ = 0.22f;
                    fire_cooldown_ = 0.25f;
                    score_ += 30;

                    // Erase adjacent incoming enemy bullets
                    for (int k = 0; k < MAX_ENEMY_BULLETS; ++k) {
                        if (enemy_bullets_[k].active) {
                            float bdx = enemy_bullets_[k].x - px_;
                            float bdy = std::fabs(enemy_bullets_[k].y - py_);
                            if (bdx > 0.0f && bdx < 2.5f && bdy < 1.5f) {
                                enemy_bullets_[k].active = false;
                                score_ += 50; // Sliced bullet points
                            }
                        }
                    }
                } else {
                    // Normal Talisman projectile
                    for (int i = 0; i < MAX_HERO_BULLETS; ++i) {
                        if (!hero_bullets_[i].active) {
                            hero_bullets_[i].active = true;
                            hero_bullets_[i].is_charge_shot = false;
                            hero_bullets_[i].x = px_ + 0.8f;
                            hero_bullets_[i].y = py_;
                            hero_bullets_[i].vx = 12.0f;
                            hero_bullets_[i].vy = 0.0f;
                            fire_cooldown_ = 0.18f;
                            break;
                        }
                    }
                }
            }
            charge_timer_ = 0.0f;
            is_charging_ = false;
        }
    }
}

void Game092SengokuBlade::UpdateHeroProjectiles(float dt) {
    for (int i = 0; i < MAX_HERO_BULLETS; ++i) {
        Bullet& b = hero_bullets_[i];
        if (!b.active) continue;

        b.x += b.vx * dt;
        b.y += b.vy * dt;

        if (b.x > 17.0f || b.x < -1.0f || b.y < -1.0f || b.y > 17.0f) {
            b.active = false;
        }
    }
}

void Game092SengokuBlade::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        KarakuriEnemy& e = enemies_[i];
        if (!e.active) {
            if (e.respawn_timer > 0.0f) {
                e.respawn_timer -= dt;
            } else {
                e.active = true;
                e.hp = (i == 0) ? 4 : 2;
                e.x = 13.0f + (float)(rand() % 2);
                e.y = 3.0f + (float)(rand() % 9);
                e.vy = (rand() % 2 == 0) ? 1.5f : -1.5f;
                e.shoot_timer = 1.0f + (rand() % 5) * 0.2f;
            }
            continue;
        }

        // Patrol vertically
        e.y += e.vy * dt;
        if (e.y <= 2.5f) {
            e.y = 2.5f;
            e.vy = std::fabs(e.vy);
        } else if (e.y >= 13.5f) {
            e.y = 13.5f;
            e.vy = -std::fabs(e.vy);
        }

        // Firing pattern
        e.shoot_timer -= dt;
        if (e.shoot_timer <= 0.0f) {
            e.shoot_timer = 1.4f + (rand() % 6) * 0.2f;
            for (int k = 0; k < MAX_ENEMY_BULLETS; ++k) {
                if (!enemy_bullets_[k].active) {
                    enemy_bullets_[k].active = true;
                    enemy_bullets_[k].x = e.x - 0.8f;
                    enemy_bullets_[k].y = e.y;
                    enemy_bullets_[k].vx = -6.0f;
                    enemy_bullets_[k].vy = 0.0f;
                    break;
                }
            }
        }
    }
}

void Game092SengokuBlade::UpdateEnemyBullets(float dt) {
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
        EnemyBullet& b = enemy_bullets_[i];
        if (!b.active) continue;

        b.x += b.vx * dt;
        b.y += b.vy * dt;

        if (b.x < -1.0f || b.x > 17.0f || b.y < -1.0f || b.y > 17.0f) {
            b.active = false;
        }
    }
}

void Game092SengokuBlade::CheckCombat() {
    // 1. Hero Melee Slash vs Enemies
    if (melee_timer_ > 0.0f) {
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            KarakuriEnemy& e = enemies_[i];
            if (!e.active) continue;

            float dx = e.x - px_;
            float dy = std::fabs(e.y - py_);

            if (dx > 0.0f && dx < 2.5f && dy < 1.4f) {
                e.hp -= 3; // Huge melee damage!
                score_ += 150;
                if (e.hp <= 0) {
                    e.active = false;
                    e.respawn_timer = 2.0f;
                    enemies_defeated_++;
                }
            }
        }
    }

    // 2. Hero Bullets vs Enemies
    for (int b_idx = 0; b_idx < MAX_HERO_BULLETS; ++b_idx) {
        Bullet& b = hero_bullets_[b_idx];
        if (!b.active) continue;

        for (int e_idx = 0; e_idx < MAX_ENEMIES; ++e_idx) {
            KarakuriEnemy& e = enemies_[e_idx];
            if (!e.active) continue;

            float dx = std::fabs(b.x - e.x);
            float dy = std::fabs(b.y - e.y);

            if (dx < 1.2f && dy < 1.2f) {
                int dmg = b.is_charge_shot ? 4 : 1;
                e.hp -= dmg;
                score_ += b.is_charge_shot ? 200 : 50;

                if (!b.is_charge_shot) {
                    b.active = false; // Normal shots vanish on hit
                }

                if (e.hp <= 0) {
                    e.active = false;
                    e.respawn_timer = 2.0f;
                    enemies_defeated_++;
                }
                break;
            }
        }
    }

    // 3. Enemy Bullets vs Hero
    if (bomb_timer_ <= 0.0f) {
        for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
            EnemyBullet& b = enemy_bullets_[i];
            if (!b.active) continue;

            float dx = std::fabs(b.x - px_);
            float dy = std::fabs(b.y - py_);

            if (dx < 0.9f && dy < 0.9f) {
                b.active = false;
                state_ = STATE_HERO_HIT;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game092SengokuBlade::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Twilight Sky with clouds
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 40 + y * 4, 20 + y * 2, 70 + y * 3); // Twilight violet sky
        }
    }

    // Background clouds scrolling
    int cloud_offset = (int)cloud_scroll_;
    for (int i = 0; i < 4; ++i) {
        int cx = (cloud_offset + i * 5) % 16;
        int cy = 3 + i * 3;
        set_pixel(cx, cy, 120, 80, 150);
        set_pixel(cx + 1, cy, 120, 80, 150);
    }

    // Mandala Bomb Screen Effect
    if (bomb_timer_ > 0.0f) {
        for (int y = 0; y < 16; ++y) {
            for (int x = 0; x < 16; ++x) {
                if ((x + y) % 3 == 0) {
                    set_pixel(x, y, 255, 220, 50); // Radiant Mandala rays
                }
            }
        }
    }

    // Karakuri Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        const KarakuriEnemy& e = enemies_[i];
        if (!e.active) continue;

        int ex = (int)std::round(e.x);
        int ey = (int)std::round(e.y);

        if (e.is_boss) {
            // Karakuri Mechanoid Giant (2x2 with red eyes)
            set_pixel(ex, ey, 140, 110, 80);        // Wood / Bronze
            set_pixel(ex + 1, ey, 140, 110, 80);
            set_pixel(ex, ey - 1, 240, 30, 30);      // Glowing eye
            set_pixel(ex + 1, ey - 1, 140, 110, 80);
        } else {
            // Flying Kite / Demon Mask
            set_pixel(ex, ey, 200, 50, 40);         // Red Demon kite
            set_pixel(ex, ey - 1, 240, 220, 180);
            set_pixel(ex + 1, ey, 100, 30, 20);
        }
    }

    // Hero Projectiles
    for (int i = 0; i < MAX_HERO_BULLETS; ++i) {
        const Bullet& b = hero_bullets_[i];
        if (!b.active) continue;

        int bx = (int)std::round(b.x);
        int by = (int)std::round(b.y);

        if (b.is_charge_shot) {
            // Giant Golden Shikigami Blast (2x2)
            set_pixel(bx, by, 255, 230, 40);
            set_pixel(bx + 1, by, 255, 255, 180);
            set_pixel(bx, by - 1, 255, 200, 0);
            set_pixel(bx + 1, by - 1, 255, 240, 100);
        } else {
            // White Talisman slip
            set_pixel(bx, by, 255, 255, 255);
            set_pixel(bx + 1, by, 240, 60, 60); // red ink seal
        }
    }

    // Enemy Bullets
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
        const EnemyBullet& b = enemy_bullets_[i];
        if (!b.active) continue;

        int bx = (int)std::round(b.x);
        int by = (int)std::round(b.y);
        set_pixel(bx, by, 255, 40, 180); // Purple/magenta Psikyo bullet
    }

    // Flying Miko Hero (Koyori)
    int px = (int)std::round(px_);
    int py = (int)std::round(py_);

    if (state_ == STATE_HERO_HIT) {
        set_pixel(px, py, 255, 50, 0);
        set_pixel(px, py - 1, 255, 200, 0);
    } else {
        // Red and white Miko kimono
        set_pixel(px, py, 220, 40, 40);         // Red hakama skirt
        set_pixel(px, py - 1, 255, 255, 255);   // White kimono
        set_pixel(px, py - 2, 240, 190, 140);   // Face
        set_pixel(px - 1, py - 2, 40, 40, 40);  // Black hair

        // Close-Range Katana Slash Arc
        if (melee_timer_ > 0.0f) {
            set_pixel(px + 1, py - 2, 220, 240, 255); // Katana flash
            set_pixel(px + 2, py - 1, 255, 255, 255); // Slash crescent
            set_pixel(px + 1, py, 200, 230, 255);
        }

        // Shikigami Charging Aura
        if (is_charging_ && charge_timer_ >= 0.75f) {
            set_pixel(px - 1, py - 1, 255, 220, 0); // Golden spirit aura
            set_pixel(px, py - 3, 255, 240, 100);
        }
    }

    // Top HUD
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 255, 60, 60);
    }
    for (int b = 0; b < bombs_ && b < 3; ++b) {
        set_pixel(15 - b, 0, 255, 215, 0); // Golden bomb scrolls
    }
}

} // namespace arcade
