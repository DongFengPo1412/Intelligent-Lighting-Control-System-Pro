#include "game_100_timepilot.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

Game100TimePilot::Game100TimePilot() {
    Reset();
}

void Game100TimePilot::Init() {
    Reset();
}

void Game100TimePilot::Reset() {
    score_ = 0;
    lives_ = 3;
    era_ = 0;
    ResetEra();
}

void Game100TimePilot::ResetEra() {
    state_ = STATE_DOGFIGHT;
    state_timer_ = 0.0f;
    squadron_defeated_ = 0;
    boss_active_ = false;
    player_angle_ = -1.5707963f; // Facing Up
    speed_ = 4.5f;
    fire_cooldown_ = 0.0f;

    for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) {
        player_bullets_[i].active = false;
    }
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
        enemy_bullets_[i].active = false;
    }
    for (int i = 0; i < MAX_PARACHUTES; ++i) {
        parachutes_[i].active = false;
    }
    for (int i = 0; i < MAX_CLOUDS; ++i) {
        clouds_[i].x = static_cast<float>((i * 7) % 16);
        clouds_[i].y = static_cast<float>((i * 5) % 16);
        clouds_[i].speed = 0.5f + static_cast<float>(i) * 0.2f;
    }

    for (int i = 0; i <= MAX_ENEMIES; ++i) {
        enemies_[i].active = false;
    }

    // Spawn initial escorts
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = true;
        enemies_[i].is_boss = false;
        enemies_[i].hp = 1;
        enemies_[i].x = (i % 2 == 0) ? -2.0f : 18.0f;
        enemies_[i].y = 2.0f + static_cast<float>(i * 3);
        enemies_[i].vx = (i % 2 == 0) ? 3.0f : -3.0f;
        enemies_[i].vy = 0.5f;
        enemies_[i].fire_timer = 1.0f + static_cast<float>(i) * 0.8f;
    }
}

void Game100TimePilot::SpawnBoss() {
    boss_active_ = true;
    EnemyFighter& boss = enemies_[MAX_ENEMIES];
    boss.active = true;
    boss.is_boss = true;
    boss.hp = 4 + era_;
    boss.x = 8.0f;
    boss.y = -3.0f;
    boss.vx = 1.2f;
    boss.vy = 1.0f;
    boss.fire_timer = 0.8f;
}

void Game100TimePilot::SpawnParachute(float x, float y) {
    for (int i = 0; i < MAX_PARACHUTES; ++i) {
        if (!parachutes_[i].active) {
            parachutes_[i].active = true;
            parachutes_[i].x = x;
            parachutes_[i].y = y;
            parachutes_[i].vy = 0.8f;
            break;
        }
    }
}

void Game100TimePilot::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_PLAYER_SHOT_DOWN) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                state_ = STATE_DOGFIGHT;
                state_timer_ = 0.0f;
                player_angle_ = -1.5707963f;
            }
        }
        return;
    }

    if (state_ == STATE_TIME_WARP) {
        if (state_timer_ > 2.2f) {
            era_ = (era_ + 1) % 5;
            ResetEra();
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    UpdateFlight(dt, buttons, prev_buttons);

    // Calculate world scroll vector based on player heading & speed
    float scroll_x = -std::cos(player_angle_) * speed_ * dt;
    float scroll_y = -std::sin(player_angle_) * speed_ * dt;

    UpdateClouds(dt, scroll_x, scroll_y);
    UpdateBullets(dt, scroll_x, scroll_y);
    UpdateEnemies(dt, scroll_x, scroll_y);
    UpdateParachutes(dt, scroll_x, scroll_y);
    CheckCollisions();

    // Spawn boss when squadron is decimated
    if (!boss_active_ && squadron_defeated_ >= 5) {
        SpawnBoss();
    }
}

void Game100TimePilot::UpdateFlight(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // 8-Way Heading Control
    float target_dx = 0.0f;
    float target_dy = 0.0f;

    if (buttons & BTN_LEFT)  target_dx -= 1.0f;
    if (buttons & BTN_RIGHT) target_dx += 1.0f;
    if (buttons & BTN_UP)    target_dy -= 1.0f;
    if (buttons & BTN_DOWN)  target_dy += 1.0f;

    if (target_dx != 0.0f || target_dy != 0.0f) {
        float target_angle = std::atan2(target_dy, target_dx);
        // Smooth angular turning towards target
        float angle_diff = target_angle - player_angle_;
        while (angle_diff > static_cast<float>(M_PI)) angle_diff -= static_cast<float>(2.0 * M_PI);
        while (angle_diff < static_cast<float>(-M_PI)) angle_diff += static_cast<float>(2.0 * M_PI);

        float turn_speed = 9.0f;
        if (std::abs(angle_diff) < turn_speed * dt) {
            player_angle_ = target_angle;
        } else {
            player_angle_ += (angle_diff > 0.0f ? 1.0f : -1.0f) * turn_speed * dt;
        }
    }

    // Button B: Afterburner turbo boost
    if (buttons & BTN_B) {
        speed_ = 7.5f;
    } else {
        speed_ = 4.5f;
    }

    // Button A: Dual cannons forward fire
    fire_cooldown_ -= dt;
    if ((buttons & BTN_A) && fire_cooldown_ <= 0.0f) {
        fire_cooldown_ = 0.22f;
        for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) {
            if (!player_bullets_[i].active) {
                player_bullets_[i].active = true;
                player_bullets_[i].x = 7.5f + std::cos(player_angle_) * 1.5f;
                player_bullets_[i].y = 7.5f + std::sin(player_angle_) * 1.5f;
                player_bullets_[i].vx = std::cos(player_angle_) * 12.0f;
                player_bullets_[i].vy = std::sin(player_angle_) * 12.0f;
                player_bullets_[i].life = 1.2f;
                player_bullets_[i].is_enemy = false;
                break;
            }
        }
    }
}

void Game100TimePilot::UpdateClouds(float dt, float scroll_x, float scroll_y) {
    for (int i = 0; i < MAX_CLOUDS; ++i) {
        clouds_[i].x += scroll_x * clouds_[i].speed;
        clouds_[i].y += scroll_y * clouds_[i].speed;

        if (clouds_[i].x < -4.0f) clouds_[i].x += 24.0f;
        if (clouds_[i].x > 20.0f) clouds_[i].x -= 24.0f;
        if (clouds_[i].y < -4.0f) clouds_[i].y += 24.0f;
        if (clouds_[i].y > 20.0f) clouds_[i].y -= 24.0f;
    }
}

void Game100TimePilot::UpdateBullets(float dt, float scroll_x, float scroll_y) {
    // Player bullets
    for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) {
        if (!player_bullets_[i].active) continue;
        player_bullets_[i].x += (player_bullets_[i].vx * dt) + scroll_x;
        player_bullets_[i].y += (player_bullets_[i].vy * dt) + scroll_y;
        player_bullets_[i].life -= dt;
        if (player_bullets_[i].life <= 0.0f ||
            player_bullets_[i].x < -2.0f || player_bullets_[i].x > 18.0f ||
            player_bullets_[i].y < -2.0f || player_bullets_[i].y > 18.0f) {
            player_bullets_[i].active = false;
        }
    }

    // Enemy bullets
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
        if (!enemy_bullets_[i].active) continue;
        enemy_bullets_[i].x += (enemy_bullets_[i].vx * dt) + scroll_x;
        enemy_bullets_[i].y += (enemy_bullets_[i].vy * dt) + scroll_y;
        enemy_bullets_[i].life -= dt;
        if (enemy_bullets_[i].life <= 0.0f ||
            enemy_bullets_[i].x < -2.0f || enemy_bullets_[i].x > 18.0f ||
            enemy_bullets_[i].y < -2.0f || enemy_bullets_[i].y > 18.0f) {
            enemy_bullets_[i].active = false;
        }
    }
}

void Game100TimePilot::UpdateEnemies(float dt, float scroll_x, float scroll_y) {
    for (int i = 0; i <= MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        enemies_[i].x += (enemies_[i].vx * dt) + scroll_x;
        enemies_[i].y += (enemies_[i].vy * dt) + scroll_y;

        // Boss movement & patrol
        if (enemies_[i].is_boss) {
            if (enemies_[i].x < 2.0f) enemies_[i].vx = std::abs(enemies_[i].vx);
            if (enemies_[i].x > 14.0f) enemies_[i].vx = -std::abs(enemies_[i].vx);
            if (enemies_[i].y < 2.0f) enemies_[i].vy = std::abs(enemies_[i].vy);
            if (enemies_[i].y > 10.0f) enemies_[i].vy = -std::abs(enemies_[i].vy);
        } else {
            // Escort screen wraparound / repositioning
            if (enemies_[i].x < -5.0f) enemies_[i].x = 21.0f;
            if (enemies_[i].x > 21.0f) enemies_[i].x = -5.0f;
            if (enemies_[i].y < -5.0f) enemies_[i].y = 21.0f;
            if (enemies_[i].y > 21.0f) enemies_[i].y = -5.0f;

            // Turn toward player center (7.5, 7.5)
            float to_p_x = 7.5f - enemies_[i].x;
            float to_p_y = 7.5f - enemies_[i].y;
            float dist = std::sqrt(to_p_x * to_p_x + to_p_y * to_p_y);
            if (dist > 0.1f) {
                float target_vx = (to_p_x / dist) * 3.2f;
                float target_vy = (to_p_y / dist) * 3.2f;
                enemies_[i].vx += (target_vx - enemies_[i].vx) * 1.5f * dt;
                enemies_[i].vy += (target_vy - enemies_[i].vy) * 1.5f * dt;
            }
        }

        // Enemy shooting
        enemies_[i].fire_timer -= dt;
        if (enemies_[i].fire_timer <= 0.0f) {
            enemies_[i].fire_timer = enemies_[i].is_boss ? 1.0f : (2.0f + static_cast<float>(i) * 0.5f);

            // Fire towards player
            float to_p_x = 7.5f - enemies_[i].x;
            float to_p_y = 7.5f - enemies_[i].y;
            float dist = std::sqrt(to_p_x * to_p_x + to_p_y * to_p_y);
            if (dist > 1.0f && dist < 12.0f) {
                for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
                    if (!enemy_bullets_[b].active) {
                        enemy_bullets_[b].active = true;
                        enemy_bullets_[b].x = enemies_[i].x;
                        enemy_bullets_[b].y = enemies_[i].y;
                        float b_spd = 5.5f + static_cast<float>(era_) * 0.8f;
                        enemy_bullets_[b].vx = (to_p_x / dist) * b_spd;
                        enemy_bullets_[b].vy = (to_p_y / dist) * b_spd;
                        enemy_bullets_[b].life = 2.0f;
                        enemy_bullets_[b].is_enemy = true;
                        break;
                    }
                }
            }
        }
    }
}

void Game100TimePilot::UpdateParachutes(float dt, float scroll_x, float scroll_y) {
    for (int i = 0; i < MAX_PARACHUTES; ++i) {
        if (!parachutes_[i].active) continue;
        parachutes_[i].x += scroll_x;
        parachutes_[i].y += (parachutes_[i].vy * dt) + scroll_y;

        if (parachutes_[i].y > 18.0f || parachutes_[i].x < -4.0f || parachutes_[i].x > 20.0f) {
            parachutes_[i].active = false;
        }
    }
}

void Game100TimePilot::CheckCollisions() {
    float px = 7.5f;
    float py = 7.5f;

    // 1. Player bullets vs Enemies
    for (int b = 0; b < MAX_PLAYER_BULLETS; ++b) {
        if (!player_bullets_[b].active) continue;

        for (int e = 0; e <= MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;

            float hit_radius = enemies_[e].is_boss ? 1.8f : 1.2f;
            float dx = player_bullets_[b].x - enemies_[e].x;
            float dy = player_bullets_[b].y - enemies_[e].y;
            if (std::sqrt(dx * dx + dy * dy) < hit_radius) {
                player_bullets_[b].active = false;
                enemies_[e].hp--;

                if (enemies_[e].hp <= 0) {
                    enemies_[e].active = false;

                    if (enemies_[e].is_boss) {
                        // Boss defeated -> TIME WARP!
                        score_ += 3000 + era_ * 1000;
                        state_ = STATE_TIME_WARP;
                        state_timer_ = 0.0f;
                    } else {
                        score_ += 100 + era_ * 50;
                        squadron_defeated_++;

                        // Chance to drop parachutist
                        if (squadron_defeated_ % 2 == 1) {
                            SpawnParachute(enemies_[e].x, enemies_[e].y);
                        }

                        // Respawn escort if boss not active yet
                        if (!boss_active_) {
                            enemies_[e].active = true;
                            enemies_[e].hp = 1;
                            enemies_[e].x = (e % 2 == 0) ? -3.0f : 19.0f;
                            enemies_[e].y = 2.0f + static_cast<float>((squadron_defeated_ * 3) % 12);
                            enemies_[e].vx = (e % 2 == 0) ? 3.0f : -3.0f;
                            enemies_[e].vy = 0.0f;
                        }
                    }
                }
                break;
            }
        }
    }

    // 2. Parachute rescue by player
    for (int p = 0; p < MAX_PARACHUTES; ++p) {
        if (!parachutes_[p].active) continue;
        float dx = px - parachutes_[p].x;
        float dy = py - parachutes_[p].y;
        if (std::sqrt(dx * dx + dy * dy) < 1.4f) {
            parachutes_[p].active = false;
            score_ += 500; // Parachutist rescued!
        }
    }

    // 3. Enemy bullets vs Player
    for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
        if (!enemy_bullets_[b].active) continue;
        float dx = px - enemy_bullets_[b].x;
        float dy = py - enemy_bullets_[b].y;
        if (std::sqrt(dx * dx + dy * dy) < 0.9f) {
            enemy_bullets_[b].active = false;
            state_ = STATE_PLAYER_SHOT_DOWN;
            state_timer_ = 0.0f;
            return;
        }
    }

    // 4. Enemy ships vs Player collision
    for (int e = 0; e <= MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        float hit_dist = enemies_[e].is_boss ? 1.5f : 1.0f;
        float dx = px - enemies_[e].x;
        float dy = py - enemies_[e].y;
        if (std::sqrt(dx * dx + dy * dy) < hit_dist) {
            state_ = STATE_PLAYER_SHOT_DOWN;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game100TimePilot::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Background Sky / Ambience by Era
    uint8_t bg_r = 10, bg_g = 15, bg_b = 30;
    switch (era_) {
        case 0: bg_r = 40; bg_g = 35; bg_b = 20; break; // 1910 Sepia Tint
        case 1: bg_r = 15; bg_g = 25; bg_b = 50; break; // 1940 Azure Blue
        case 2: bg_r = 50; bg_g = 25; bg_b = 15; break; // 1970 Sunset
        case 3: bg_r = 10; bg_g = 10; bg_b = 35; break; // 2001 Midnight Blue
        case 4: bg_r = 5;  bg_g = 5;  bg_b = 15; break; // Space UFO deep void
    }

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, bg_r, bg_g, bg_b);
        }
    }

    // Clouds
    for (int i = 0; i < MAX_CLOUDS; ++i) {
        int cx = static_cast<int>(std::round(clouds_[i].x));
        int cy = static_cast<int>(std::round(clouds_[i].y));
        uint8_t cr = (era_ == 0) ? 140 : 180;
        uint8_t cg = (era_ == 0) ? 130 : 190;
        uint8_t cb = (era_ == 0) ? 110 : 210;
        set_pixel(cx, cy, cr, cg, cb);
        set_pixel(cx + 1, cy, cr, cg, cb);
        set_pixel(cx, cy + 1, cr, cg, cb);
    }

    // Parachutists (White parachute + flesh pilot)
    for (int p = 0; p < MAX_PARACHUTES; ++p) {
        if (!parachutes_[p].active) continue;
        int px = static_cast<int>(std::round(parachutes_[p].x));
        int py = static_cast<int>(std::round(parachutes_[p].y));
        set_pixel(px, py - 1, 255, 255, 255); // Chute
        set_pixel(px - 1, py - 1, 240, 240, 240);
        set_pixel(px + 1, py - 1, 240, 240, 240);
        set_pixel(px, py, 255, 200, 150);     // Pilot
    }

    // Bullets
    for (int b = 0; b < MAX_PLAYER_BULLETS; ++b) {
        if (!player_bullets_[b].active) continue;
        int bx = static_cast<int>(std::round(player_bullets_[b].x));
        int by = static_cast<int>(std::round(player_bullets_[b].y));
        set_pixel(bx, by, 255, 255, 100);
    }
    for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
        if (!enemy_bullets_[b].active) continue;
        int bx = static_cast<int>(std::round(enemy_bullets_[b].x));
        int by = static_cast<int>(std::round(enemy_bullets_[b].y));
        set_pixel(bx, by, 255, 60, 40);
    }

    // Enemies
    for (int e = 0; e <= MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        int ex = static_cast<int>(std::round(enemies_[e].x));
        int ey = static_cast<int>(std::round(enemies_[e].y));

        if (enemies_[e].is_boss) {
            // Boss Flagship (multi-pixel)
            uint8_t br = 255, bg = 180, bb = 40;
            if (era_ == 4) { br = 80; bg = 255; bb = 120; }
            set_pixel(ex, ey, br, bg, bb);
            set_pixel(ex - 1, ey, br, bg, bb);
            set_pixel(ex + 1, ey, br, bg, bb);
            set_pixel(ex, ey - 1, br, bg, bb);
            set_pixel(ex, ey + 1, br, bg, bb);
        } else {
            // Squadron Escort
            uint8_t er = 220, eg = 80, eb = 60;
            if (era_ == 2) { er = 100; eg = 200; eb = 50; }
            if (era_ == 3) { er = 60;  eg = 150; eb = 240; }
            if (era_ == 4) { er = 220; eg = 60;  eb = 220; }
            set_pixel(ex, ey, er, eg, eb);
        }
    }

    // Time Warp Visual Transition
    if (state_ == STATE_TIME_WARP) {
        int ring = static_cast<int>(state_timer_ * 7.0f) % 8;
        for (int i = 0; i < 16; ++i) {
            set_pixel(i, ring, 255, 255, 255);
            set_pixel(i, 15 - ring, 255, 255, 255);
            set_pixel(ring, i, 255, 255, 255);
            set_pixel(15 - ring, i, 255, 255, 255);
        }
    }

    // Player Craft at Center (7 or 8)
    int px = 7;
    int py = 7;
    if (state_ == STATE_PLAYER_SHOT_DOWN) {
        // Explosion flash
        set_pixel(px, py, 255, 50, 20);
        set_pixel(px - 1, py, 255, 180, 0);
        set_pixel(px + 1, py, 255, 180, 0);
        set_pixel(px, py - 1, 255, 180, 0);
        set_pixel(px, py + 1, 255, 180, 0);
    } else {
        // Player Ship with nose pointing along heading
        set_pixel(px, py, 255, 255, 255); // Cockpit
        int nose_x = px + static_cast<int>(std::round(std::cos(player_angle_)));
        int nose_y = py + static_cast<int>(std::round(std::sin(player_angle_)));
        set_pixel(nose_x, nose_y, 0, 220, 255); // Nose

        int wing_x = px - static_cast<int>(std::round(std::cos(player_angle_)));
        int wing_y = py - static_cast<int>(std::round(std::sin(player_angle_)));
        set_pixel(wing_x, wing_y, 255, 120, 20); // Thruster
    }

    // HUD: Squadron Defeated meter on bottom row
    for (int i = 0; i < std::min(squadron_defeated_, 5); ++i) {
        set_pixel(i, 15, 0, 255, 100);
    }
    // Lives on top row
    for (int l = 0; l < std::min(lives_, 3); ++l) {
        set_pixel(l, 0, 255, 220, 0);
    }
}

} // namespace arcade
