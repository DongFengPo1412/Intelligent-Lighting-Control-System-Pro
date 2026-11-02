#include "game_107_xevious.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game107Xevious::Game107Xevious() {
    Reset();
}

void Game107Xevious::Init() {
    Reset();
}

void Game107Xevious::Reset() {
    score_ = 0;
    lives_ = 3;
    area_ = 1;
    InitArea();
}

void Game107Xevious::InitArea() {
    state_ = STATE_FLYING;
    state_timer_ = 0.0f;
    scroll_y_ = 0.0f;
    enemies_downed_ = 0;

    px_ = 8.0f;
    py_ = 13.0f;
    zapper_cooldown_ = 0.0f;
    blaster_cooldown_ = 0.0f;

    for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) {
        player_bullets_[i].active = false;
    }
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
        enemy_bullets_[i].active = false;
    }
    for (int i = 0; i < MAX_GROUND_BOMBS; ++i) {
        ground_bombs_[i].active = false;
    }

    // Spawn 3 Air Enemies (Toroid rings)
    for (int i = 0; i < MAX_AIR_ENEMIES; ++i) {
        air_enemies_[i].active = true;
        air_enemies_[i].x = 3.0f + static_cast<float>(i * 4.5f);
        air_enemies_[i].y = -2.0f - static_cast<float>(i * 3.0f);
        air_enemies_[i].vx = (i % 2 == 0) ? 1.5f : -1.5f;
        air_enemies_[i].vy = 3.2f;
        air_enemies_[i].type = i % 2;
    }

    // Spawn 4 Ground Targets (Barra, Zolbak, Sol)
    for (int i = 0; i < MAX_GROUND_TARGETS; ++i) {
        ground_targets_[i].active = true;
        ground_targets_[i].x = 4.0f + static_cast<float>((i * 3) % 8);
        ground_targets_[i].y = 2.0f + static_cast<float>(i * 3.5f);
        ground_targets_[i].type = (i == 3) ? 2 : (i % 2); // 2 = Sol hidden citadel
        ground_targets_[i].hp = 1;
    }
}

void Game107Xevious::SpawnAndorGenesis() {
    state_ = STATE_BOSS_ANDOR;
    state_timer_ = 0.0f;
    andor_x_ = 5.0f;
    andor_y_ = 2.5f;
    andor_vx_ = 1.8f;
    andor_hp_ = 6;
}

void Game107Xevious::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_SHIP_EXPLODED) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                state_ = STATE_FLYING;
                state_timer_ = 0.0f;
                px_ = 8.0f;
                py_ = 13.0f;
            }
        }
        return;
    }

    if (state_ == STATE_AREA_CLEAR) {
        if (state_timer_ > 2.2f) {
            area_++;
            InitArea();
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    scroll_y_ += 3.0f * dt;

    UpdateShip(dt, buttons, prev_buttons);
    UpdateAirEntities(dt);
    UpdateGroundEntities(dt);

    if (state_ == STATE_BOSS_ANDOR) {
        UpdateAndorGenesis(dt);
    } else {
        if (enemies_downed_ >= 6) {
            SpawnAndorGenesis();
        }
    }

    CheckAirCollisions();
    CheckGroundBombCollisions();
}

void Game107Xevious::UpdateShip(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float spd = 7.5f;
    if (buttons & BTN_LEFT)  px_ = std::max(1.0f, px_ - spd * dt);
    if (buttons & BTN_RIGHT) px_ = std::min(14.0f, px_ + spd * dt);
    if (buttons & BTN_UP)    py_ = std::max(2.0f, py_ - spd * dt);
    if (buttons & BTN_DOWN)  py_ = std::min(14.0f, py_ + spd * dt);

    // Button A: Air-to-Air Zapper
    zapper_cooldown_ -= dt;
    if ((buttons & BTN_A) && zapper_cooldown_ <= 0.0f) {
        zapper_cooldown_ = 0.2f;
        for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) {
            if (!player_bullets_[i].active) {
                player_bullets_[i].active = true;
                player_bullets_[i].x = px_;
                player_bullets_[i].y = py_ - 1.2f;
                player_bullets_[i].vy = -18.0f;
                player_bullets_[i].is_enemy = false;
                break;
            }
        }
    }

    // Button B: Blaster Ground Bomb towards Crosshair (px, py - 3.5)
    blaster_cooldown_ -= dt;
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B) && blaster_cooldown_ <= 0.0f) {
        blaster_cooldown_ = 0.4f;
        for (int b = 0; b < MAX_GROUND_BOMBS; ++b) {
            if (!ground_bombs_[b].active) {
                ground_bombs_[b].active = true;
                ground_bombs_[b].x = px_;
                ground_bombs_[b].y = py_ - 0.5f;
                ground_bombs_[b].target_x = px_;
                ground_bombs_[b].target_y = py_ - 3.5f;
                ground_bombs_[b].timer = 0.35f;
                break;
            }
        }
    }
}

void Game107Xevious::UpdateAirEntities(float dt) {
    // Player bullets
    for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) {
        if (!player_bullets_[i].active) continue;
        player_bullets_[i].y += player_bullets_[i].vy * dt;
        if (player_bullets_[i].y < -1.0f) player_bullets_[i].active = false;
    }

    // Enemy bullets
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
        if (!enemy_bullets_[i].active) continue;
        enemy_bullets_[i].y += enemy_bullets_[i].vy * dt;
        if (enemy_bullets_[i].y > 16.0f) enemy_bullets_[i].active = false;
    }

    // Air Enemies (Toroid/Zakato)
    for (int i = 0; i < MAX_AIR_ENEMIES; ++i) {
        if (!air_enemies_[i].active) {
            air_enemies_[i].active = true;
            air_enemies_[i].x = 2.0f + static_cast<float>((i * 5) % 12);
            air_enemies_[i].y = -2.0f;
            air_enemies_[i].vx = (i % 2 == 0) ? 2.0f : -2.0f;
            air_enemies_[i].vy = 3.5f;
            continue;
        }

        air_enemies_[i].x += air_enemies_[i].vx * dt;
        air_enemies_[i].y += air_enemies_[i].vy * dt;

        if (air_enemies_[i].x < 1.0f || air_enemies_[i].x > 14.0f) {
            air_enemies_[i].vx = -air_enemies_[i].vx;
        }

        // Fire enemy air bullets downward
        if (air_enemies_[i].y > 2.0f && air_enemies_[i].y < 12.0f && (i == 0)) {
            static float e_fire = 0.0f;
            e_fire += dt;
            if (e_fire > 1.2f) {
                e_fire = 0.0f;
                for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
                    if (!enemy_bullets_[b].active) {
                        enemy_bullets_[b].active = true;
                        enemy_bullets_[b].x = air_enemies_[i].x;
                        enemy_bullets_[b].y = air_enemies_[i].y;
                        enemy_bullets_[b].vy = 6.0f;
                        enemy_bullets_[b].is_enemy = true;
                        break;
                    }
                }
            }
        }

        if (air_enemies_[i].y > 17.0f) {
            air_enemies_[i].active = false;
        }
    }
}

void Game107Xevious::UpdateGroundEntities(float dt) {
    // Ground targets scroll down with terrain
    for (int i = 0; i < MAX_GROUND_TARGETS; ++i) {
        if (!ground_targets_[i].active) {
            ground_targets_[i].active = true;
            ground_targets_[i].x = 3.0f + static_cast<float>((i * 4) % 10);
            ground_targets_[i].y = -3.0f;
            ground_targets_[i].type = (i == 3) ? 2 : (i % 2);
            ground_targets_[i].hp = 1;
            continue;
        }

        ground_targets_[i].y += 3.0f * dt;
        if (ground_targets_[i].y > 17.0f) {
            ground_targets_[i].active = false;
        }
    }

    // Ground bombs fly towards target crosshair
    for (int b = 0; b < MAX_GROUND_BOMBS; ++b) {
        if (!ground_bombs_[b].active) continue;
        ground_bombs_[b].timer -= dt;
        float progress = 1.0f - std::max(0.0f, ground_bombs_[b].timer / 0.35f);
        ground_bombs_[b].y = ground_bombs_[b].target_y + (1.0f - progress) * 3.0f;
    }
}

void Game107Xevious::UpdateAndorGenesis(float dt) {
    andor_x_ += andor_vx_ * dt;
    if (andor_x_ <= 2.0f) {
        andor_x_ = 2.0f;
        andor_vx_ = std::abs(andor_vx_);
    } else if (andor_x_ >= 8.0f) {
        andor_x_ = 8.0f;
        andor_vx_ = -std::abs(andor_vx_);
    }
}

void Game107Xevious::CheckAirCollisions() {
    // 1. Air bullets vs Air Enemies
    for (int b = 0; b < MAX_PLAYER_BULLETS; ++b) {
        if (!player_bullets_[b].active) continue;
        for (int e = 0; e < MAX_AIR_ENEMIES; ++e) {
            if (!air_enemies_[e].active) continue;
            float dx = std::abs(player_bullets_[b].x - air_enemies_[e].x);
            float dy = std::abs(player_bullets_[b].y - air_enemies_[e].y);
            if (dx < 1.2f && dy < 1.2f) {
                player_bullets_[b].active = false;
                air_enemies_[e].active = false;
                score_ += 100;
                enemies_downed_++;
                break;
            }
        }

        // Air bullets vs Andor Genesis Core
        if (state_ == STATE_BOSS_ANDOR && player_bullets_[b].active) {
            if (player_bullets_[b].y >= andor_y_ - 0.5f && player_bullets_[b].y <= andor_y_ + 3.0f) {
                if (player_bullets_[b].x >= andor_x_ + 1.0f && player_bullets_[b].x <= andor_x_ + 4.0f) {
                    player_bullets_[b].active = false;
                    andor_hp_--;
                    score_ += 200;
                    if (andor_hp_ <= 0) {
                        state_ = STATE_AREA_CLEAR;
                        state_timer_ = 0.0f;
                        score_ += 4000;
                    }
                }
            }
        }
    }

    // 2. Enemy air bullets & enemies vs Solvalou ship
    for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
        if (!enemy_bullets_[b].active) continue;
        if (std::abs(px_ - enemy_bullets_[b].x) < 0.9f && std::abs(py_ - enemy_bullets_[b].y) < 0.9f) {
            enemy_bullets_[b].active = false;
            state_ = STATE_SHIP_EXPLODED;
            state_timer_ = 0.0f;
            return;
        }
    }

    for (int e = 0; e < MAX_AIR_ENEMIES; ++e) {
        if (!air_enemies_[e].active) continue;
        if (std::abs(px_ - air_enemies_[e].x) < 0.9f && std::abs(py_ - air_enemies_[e].y) < 0.9f) {
            state_ = STATE_SHIP_EXPLODED;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game107Xevious::CheckGroundBombCollisions() {
    for (int b = 0; b < MAX_GROUND_BOMBS; ++b) {
        if (!ground_bombs_[b].active) continue;
        if (ground_bombs_[b].timer <= 0.0f) {
            ground_bombs_[b].active = false;
            // Bomb landing footprint
            float bx = ground_bombs_[b].target_x;
            float by = ground_bombs_[b].target_y;

            for (int g = 0; g < MAX_GROUND_TARGETS; ++g) {
                if (!ground_targets_[g].active) continue;
                float dx = std::abs(bx - ground_targets_[g].x);
                float dy = std::abs(by - ground_targets_[g].y);
                if (dx < 1.3f && dy < 1.3f) {
                    ground_targets_[g].active = false;
                    if (ground_targets_[g].type == 2) {
                        // Secret Sol Citadel Unearthed!
                        score_ += 2000;
                    } else if (ground_targets_[g].type == 1) {
                        // Zolbak radar dome
                        score_ += 300;
                    } else {
                        // Barra pyramid
                        score_ += 200;
                    }
                    enemies_downed_++;
                }
            }

            // Bomb hitting Andor Genesis central reactor
            if (state_ == STATE_BOSS_ANDOR) {
                if (std::abs(bx - (andor_x_ + 2.5f)) < 1.8f && std::abs(by - (andor_y_ + 1.5f)) < 1.8f) {
                    andor_hp_ -= 2;
                    score_ += 500;
                    if (andor_hp_ <= 0) {
                        state_ = STATE_AREA_CLEAR;
                        state_timer_ = 0.0f;
                        score_ += 4000;
                    }
                }
            }
        }
    }
}

void Game107Xevious::Render(uint8_t* fb) {
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

    // Ground Terrain (Forest & Nazca Plain)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int pat = (x + y + static_cast<int>(scroll_y_)) % 6;
            if (pat == 0) {
                set_pixel(x, y, 40, 100, 30); // Forest canopy
            } else if (pat == 3) {
                set_pixel(x, y, 120, 110, 70); // Ancient desert road
            } else {
                set_pixel(x, y, 60, 120, 45); // Grassland
            }
        }
    }

    // Ground Layer Targets
    for (int g = 0; g < MAX_GROUND_TARGETS; ++g) {
        if (!ground_targets_[g].active) continue;
        int gx = static_cast<int>(std::round(ground_targets_[g].x));
        int gy = static_cast<int>(std::round(ground_targets_[g].y));

        if (ground_targets_[g].type == 0) {
            // Barra (Red pyramid bunker)
            set_pixel(gx, gy, 220, 50, 40);
            set_pixel(gx, gy - 1, 240, 100, 80);
        } else if (ground_targets_[g].type == 1) {
            // Zolbak (Dome radar)
            set_pixel(gx, gy, 60, 140, 220);
            set_pixel(gx + 1, gy, 180, 220, 255);
        } else {
            // Sol (Golden hidden citadel)
            set_pixel(gx, gy, 255, 200, 0);
            set_pixel(gx, gy - 1, 255, 255, 120);
            set_pixel(gx, gy + 1, 200, 150, 0);
        }
    }

    // Ground Bombs in flight
    for (int b = 0; b < MAX_GROUND_BOMBS; ++b) {
        if (!ground_bombs_[b].active) continue;
        int bx = static_cast<int>(std::round(ground_bombs_[b].x));
        int by = static_cast<int>(std::round(ground_bombs_[b].y));
        set_pixel(bx, by, 255, 255, 200);
    }

    // Andor Genesis Mothership (Massive octagonal gray fortress with glowing center)
    if (state_ == STATE_BOSS_ANDOR) {
        int ax = static_cast<int>(std::round(andor_x_));
        int ay = static_cast<int>(std::round(andor_y_));
        for (int y = ay; y < ay + 3; ++y) {
            for (int x = ax; x < ax + 5; ++x) {
                set_pixel(x, y, 140, 140, 150); // Gray armor plate
            }
        }
        // Glowing red central reactor core
        set_pixel(ax + 2, ay + 1, 255, 40, 20);
    }

    // Air Enemies (Toroid spinning rings)
    for (int e = 0; e < MAX_AIR_ENEMIES; ++e) {
        if (!air_enemies_[e].active) continue;
        int ex = static_cast<int>(std::round(air_enemies_[e].x));
        int ey = static_cast<int>(std::round(air_enemies_[e].y));
        set_pixel(ex, ey, 220, 180, 40);
        set_pixel(ex - 1, ey, 180, 120, 20);
        set_pixel(ex + 1, ey, 180, 120, 20);
    }

    // Air Bullets
    for (int b = 0; b < MAX_PLAYER_BULLETS; ++b) {
        if (!player_bullets_[b].active) continue;
        set_pixel(static_cast<int>(std::round(player_bullets_[b].x)),
                  static_cast<int>(std::round(player_bullets_[b].y)),
                  255, 255, 100);
    }
    for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
        if (!enemy_bullets_[b].active) continue;
        set_pixel(static_cast<int>(std::round(enemy_bullets_[b].x)),
                  static_cast<int>(std::round(enemy_bullets_[b].y)),
                  255, 60, 40);
    }

    // Solvalou Ship & Ground Crosshair
    int px_i = static_cast<int>(std::round(px_));
    int py_i = static_cast<int>(std::round(py_));

    // Ground Crosshair projected ahead (px, py - 3.5)
    int cx = px_i;
    int cy = py_i - 4;
    set_pixel(cx, cy, 255, 255, 0); // Crosshair yellow dot
    set_pixel(cx - 1, cy, 180, 180, 0); // Sight brackets
    set_pixel(cx + 1, cy, 180, 180, 0);

    if (state_ == STATE_SHIP_EXPLODED) {
        set_pixel(px_i, py_i, 255, 60, 20);
        set_pixel(px_i - 1, py_i, 255, 180, 0);
        set_pixel(px_i + 1, py_i, 255, 180, 0);
        set_pixel(px_i, py_i - 1, 255, 220, 0);
    } else {
        // Solvalou Streamlined Silver Fighter
        set_pixel(px_i, py_i, 230, 230, 240);     // Fuselage
        set_pixel(px_i, py_i - 1, 0, 200, 255);   // Blue canopy
        set_pixel(px_i - 1, py_i + 1, 200, 40, 30); // Red port wing
        set_pixel(px_i + 1, py_i + 1, 200, 40, 30); // Red starboard wing
        set_pixel(px_i, py_i + 1, 255, 140, 20);  // Thruster
    }

    // Lives
    for (int l = 0; l < std::min(lives_, 3); ++l) {
        set_pixel(l, 0, 255, 255, 255);
    }
}

} // namespace arcade
