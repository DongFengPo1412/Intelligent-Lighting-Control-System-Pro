#include "game_086_kikikaikai.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace arcade {

Game086KiKiKaiKai::Game086KiKiKaiKai() {
    Reset();
}

void Game086KiKiKaiKai::Init() {
    Reset();
}

void Game086KiKiKaiKai::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    yokai_defeated_ = 0;
    empowered_talisman_ = false;
    ResetStage();
}

void Game086KiKiKaiKai::ResetStage() {
    px_ = 7.5f;
    py_ = 12.0f;
    facing_x_ = 0;
    facing_y_ = -1;
    gohei_timer_ = 0.0f;
    spawn_timer_ = 0.0f;
    scroll_offset_ = 0.0f;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = false;
    }
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        projs_[i].active = false;
    }

    // Spawn 2 initial yokai
    enemies_[0].active = true;
    enemies_[0].x = 4.0f;
    enemies_[0].y = 2.0f;
    enemies_[0].type = EN_BAKE_NEKO;
    enemies_[0].hp = 1;

    enemies_[1].active = true;
    enemies_[1].x = 11.0f;
    enemies_[1].y = 3.0f;
    enemies_[1].type = EN_TENGU;
    enemies_[1].hp = 2;
    enemies_[1].shoot_timer = 1.5f;
}

void Game086KiKiKaiKai::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_HERO_DEAD || state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.5f && (buttons & (BUTTON_A | BUTTON_B))) {
            Reset();
        }
        return;
    }

    // Spawning cadence
    spawn_timer_ += dt;
    if (spawn_timer_ > 2.2f) {
        spawn_timer_ = 0.0f;
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (!enemies_[i].active && yokai_defeated_ + i < 15) {
                enemies_[i].active = true;
                enemies_[i].x = 2.0f + (std::rand() % 12);
                enemies_[i].y = 1.0f;
                enemies_[i].type = static_cast<EnemyType>(std::rand() % 3);
                enemies_[i].hp = (enemies_[i].type == EN_TENGU) ? 2 : 1;
                enemies_[i].shoot_timer = 1.8f;
                break;
            }
        }
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateEnemies(dt);
    UpdateProjectiles(dt);
    CheckCollisions();

    if (yokai_defeated_ >= 15) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 6000;
    }

    scroll_offset_ += 2.0f * dt;
}

void Game086KiKiKaiKai::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float speed = 5.2f;
    float mx = 0.0f;
    float my = 0.0f;

    if (buttons & BUTTON_LEFT)  mx -= 1.0f;
    if (buttons & BUTTON_RIGHT) mx += 1.0f;
    if (buttons & BUTTON_UP)    my -= 1.0f;
    if (buttons & BUTTON_DOWN)  my += 1.0f;

    if (mx != 0.0f || my != 0.0f) {
        facing_x_ = static_cast<int>(mx);
        facing_y_ = static_cast<int>(my);
    }

    px_ += mx * speed * dt;
    py_ += my * speed * dt;

    px_ = std::max(1.0f, std::min(14.0f, px_));
    py_ = std::max(2.0f, std::min(14.0f, py_));

    if (gohei_timer_ > 0.0f) {
        gohei_timer_ -= dt;
    }

    // Ofuda Talisman Throw (Button A)
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        FireTalisman();
    }

    // Gohei Purifying Wand Swing (Button B)
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        SwingGohei();
    }
}

void Game086KiKiKaiKai::FireTalisman() {
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projs_[i].active) {
            projs_[i].active = true;
            projs_[i].x = px_ + facing_x_ * 0.8f;
            projs_[i].y = py_ + facing_y_ * 0.8f;

            float spd = 14.0f;
            projs_[i].vx = facing_x_ * spd;
            projs_[i].vy = (facing_x_ == 0 && facing_y_ == 0) ? -spd : facing_y_ * spd;
            projs_[i].is_talisman = true;
            break;
        }
    }
}

void Game086KiKiKaiKai::SwingGohei() {
    gohei_timer_ = 0.28f;

    // Check immediate wand strike & fireball reflection in front
    float hit_x = px_ + facing_x_ * 1.4f;
    float hit_y = py_ + (facing_y_ == 0 ? -1.0f : facing_y_) * 1.4f;

    // 1. Deflect & reflect enemy fireballs!
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (projs_[i].active && !projs_[i].is_talisman) {
            float dx = std::abs(projs_[i].x - hit_x);
            float dy = std::abs(projs_[i].y - hit_y);
            if (dx < 1.8f && dy < 1.8f) {
                // Deflects back toward enemies!
                projs_[i].is_talisman = true;
                projs_[i].vx = -projs_[i].vx;
                projs_[i].vy = -projs_[i].vy;
                score_ += 300;
            }
        }
    }

    // 2. Wand melee hit yokai
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        float dx = std::abs(enemies_[i].x - hit_x);
        float dy = std::abs(enemies_[i].y - hit_y);
        if (dx < 1.8f && dy < 1.8f) {
            enemies_[i].hp--;
            if (enemies_[i].hp <= 0) {
                enemies_[i].active = false;
                yokai_defeated_++;
                score_ += 500;
            }
        }
    }
}

void Game086KiKiKaiKai::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (enemies_[i].type == EN_BAKE_NEKO) {
            // Chases Sayo
            float dx = px_ - enemies_[i].x;
            float dy = py_ - enemies_[i].y;
            float dist = std::sqrt(dx * dx + dy * dy);
            if (dist > 0.1f) {
                enemies_[i].x += (dx / dist) * 2.8f * dt;
                enemies_[i].y += (dy / dist) * 2.8f * dt;
            }
        } else if (enemies_[i].type == EN_KASA_OBAKE) {
            // Hops down in zigzag
            enemies_[i].y += 2.0f * dt;
            enemies_[i].x += std::sin(state_timer_ * 6.0f) * 4.0f * dt;
        } else if (enemies_[i].type == EN_TENGU) {
            // Hovers at top & shoots fireballs
            enemies_[i].x += std::cos(state_timer_ * 3.0f) * 3.0f * dt;
            enemies_[i].shoot_timer -= dt;
            if (enemies_[i].shoot_timer <= 0.0f) {
                enemies_[i].shoot_timer = 2.0f;
                // Fire hostile fireball
                for (int p = 0; p < MAX_PROJECTILES; ++p) {
                    if (!projs_[p].active) {
                        projs_[p].active = true;
                        projs_[p].x = enemies_[i].x;
                        projs_[p].y = enemies_[i].y + 0.8f;
                        float dx = px_ - enemies_[i].x;
                        float dy = py_ - enemies_[i].y;
                        float d = std::max(0.1f, std::sqrt(dx * dx + dy * dy));
                        projs_[p].vx = (dx / d) * 7.0f;
                        projs_[p].vy = (dy / d) * 7.0f;
                        projs_[p].is_talisman = false;
                        break;
                    }
                }
            }
        }

        enemies_[i].x = std::max(1.0f, std::min(14.5f, enemies_[i].x));
        if (enemies_[i].y > 15.0f) {
            enemies_[i].y = 0.5f;
            enemies_[i].x = 2.0f + (std::rand() % 12);
        }
    }
}

void Game086KiKiKaiKai::UpdateProjectiles(float dt) {
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projs_[i].active) continue;

        projs_[i].x += projs_[i].vx * dt;
        projs_[i].y += projs_[i].vy * dt;

        if (projs_[i].x < 0.0f || projs_[i].x > 15.5f || projs_[i].y < 0.0f || projs_[i].y > 15.5f) {
            projs_[i].active = false;
        }
    }
}

void Game086KiKiKaiKai::CheckCollisions() {
    // 1. Talismans vs Enemies
    for (int p = 0; p < MAX_PROJECTILES; ++p) {
        if (!projs_[p].active || !projs_[p].is_talisman) continue;

        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;

            if (std::abs(projs_[p].x - enemies_[e].x) < 1.4f && std::abs(projs_[p].y - enemies_[e].y) < 1.4f) {
                projs_[p].active = false;
                enemies_[e].hp--;
                if (enemies_[e].hp <= 0) {
                    enemies_[e].active = false;
                    yokai_defeated_++;
                    score_ += 400;
                }
                break;
            }
        }
    }

    // 2. Enemy / Fireball vs Sayo-chan
    for (int p = 0; p < MAX_PROJECTILES; ++p) {
        if (!projs_[p].active || projs_[p].is_talisman) continue;
        if (std::abs(projs_[p].x - px_) < 1.1f && std::abs(projs_[p].y - py_) < 1.1f) {
            projs_[p].active = false;
            lives_--;
            if (lives_ > 0) {
                px_ = 7.5f;
                py_ = 12.0f;
            } else {
                state_ = STATE_HERO_DEAD;
                state_timer_ = 0.0f;
            }
            return;
        }
    }

    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        if (std::abs(enemies_[e].x - px_) < 1.1f && std::abs(enemies_[e].y - py_) < 1.1f) {
            lives_--;
            if (lives_ > 0) {
                px_ = 7.5f;
                py_ = 12.0f;
            } else {
                state_ = STATE_HERO_DEAD;
                state_timer_ = 0.0f;
            }
            return;
        }
    }
}

void Game086KiKiKaiKai::Render(uint8_t* fb) {
    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Shinto Shrine Bamboo Forest (Borders)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x < 2 || x > 13) {
                set_pixel(x, y, 15, 60, 25); // Bamboo grove
            } else {
                set_pixel(x, y, 140, 130, 110); // Gravel path
            }
        }
    }

    // Torii Gate on top
    for (int x = 4; x <= 11; ++x) set_pixel(x, 1, 230, 40, 30);
    set_pixel(5, 2, 230, 40, 30);
    set_pixel(10, 2, 230, 40, 30);

    // 2. Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));

        if (enemies_[i].type == EN_BAKE_NEKO) {
            // White spirit cat with red ears
            set_pixel(ex, ey, 240, 240, 250);
            set_pixel(ex - 1, ey - 1, 255, 40, 40);
            set_pixel(ex + 1, ey - 1, 255, 40, 40);
        } else if (enemies_[i].type == EN_KASA_OBAKE) {
            // Purple umbrella ghost with single giant eye
            set_pixel(ex, ey, 160, 60, 180);
            set_pixel(ex, ey - 1, 255, 255, 255); // Eye
            set_pixel(ex, ey + 1, 180, 140, 80);  // Wooden leg
        } else {
            // Red Tengu mask with long nose
            set_pixel(ex, ey, 220, 30, 30);
            set_pixel(ex, ey - 1, 30, 30, 30); // Black cowl
            set_pixel(ex + 1, ey, 255, 100, 100); // Nose
        }
    }

    // 3. Projectiles
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projs_[i].active) continue;
        int px = static_cast<int>(std::round(projs_[i].x));
        int py = static_cast<int>(std::round(projs_[i].y));

        if (projs_[i].is_talisman) {
            // White and Red Ofuda Paper Talisman
            set_pixel(px, py, 255, 255, 255);
            set_pixel(px, py - 1, 255, 30, 30);
        } else {
            // Blue/Green Ghost Fireball (Onibi)
            set_pixel(px, py, 50, 220, 255);
            set_pixel(px, py + 1, 30, 100, 255);
        }
    }

    // 4. Shrine Maiden Sayo-chan (White Haori & Red Hakama)
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));

    set_pixel(px, py, 220, 30, 30);      // Crimson Hakama pleated skirt
    set_pixel(px, py - 1, 255, 255, 255); // Pure White Kimono Top
    set_pixel(px, py - 2, 240, 180, 140); // Cute Face
    set_pixel(px, py - 3, 20, 20, 20);    // Black Bob Haircut & Ribbon

    // Gohei Wand (Purification Staff with folded white paper zigzags)
    if (gohei_timer_ > 0.0f) {
        int gx = px + facing_x_;
        int gy = py + (facing_y_ == 0 ? -1 : facing_y_);
        set_pixel(gx, gy, 200, 160, 100);     // Bamboo handle
        set_pixel(gx + facing_x_, gy, 255, 255, 255); // White folded shide paper
        set_pixel(gx, gy - 1, 255, 255, 255);
    }

    // 5. HUD (y = 0)
    for (int l = 0; l < lives_; ++l) {
        set_pixel(l * 2, 0, 255, 50, 50); // Red Hakama bows
    }
}

} // namespace arcade
