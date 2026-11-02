#include "game_036_missile_command.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

static const int CITY_X[Game036MissileCommand::NUM_CITIES] = {2, 4, 5, 9, 10, 12};
static const int BASE_X[3] = {0, 7, 15};

Game036MissileCommand::Game036MissileCommand()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      wave_(1),
      ammo_(15),
      enemy_spawn_remaining_(10),
      spawn_timer_(0.0f),
      crosshair_x_(7.5f),
      crosshair_y_(7.5f) {
}

void Game036MissileCommand::Init() {
    Reset();
}

void Game036MissileCommand::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    wave_ = 1;
    crosshair_x_ = 7.5f;
    crosshair_y_ = 7.5f;

    for (int i = 0; i < NUM_CITIES; ++i) {
        cities_alive_[i] = true;
    }

    InitWave();
}

void Game036MissileCommand::InitWave() {
    ammo_ = 15;
    enemy_spawn_remaining_ = 8 + wave_ * 2;
    spawn_timer_ = 0.5f;

    for (int i = 0; i < MAX_ENEMY_MISSILES; ++i) enemy_missiles_[i].active = false;
    for (int i = 0; i < MAX_INTERCEPTORS; ++i) interceptors_[i].active = false;
    for (int i = 0; i < MAX_EXPLOSIONS; ++i) explosions_[i].active = false;
}

int Game036MissileCommand::GetSurvivingCities() const {
    int count = 0;
    for (int i = 0; i < NUM_CITIES; ++i) {
        if (cities_alive_[i]) count++;
    }
    return count;
}

void Game036MissileCommand::SpawnEnemyMissile() {
    if (enemy_spawn_remaining_ <= 0) return;

    for (int i = 0; i < MAX_ENEMY_MISSILES; ++i) {
        if (!enemy_missiles_[i].active) {
            enemy_missiles_[i].active = true;
            enemy_missiles_[i].x = 1.0f + static_cast<float>(rand() % 14);
            enemy_missiles_[i].y = 0.0f;

            // Pick an active city or base
            int target_x = 7;
            int alive_cities[NUM_CITIES];
            int num_alive = 0;
            for (int c = 0; c < NUM_CITIES; ++c) {
                if (cities_alive_[c]) alive_cities[num_alive++] = CITY_X[c];
            }

            if (num_alive > 0) {
                target_x = alive_cities[rand() % num_alive];
            } else {
                target_x = BASE_X[rand() % 3];
            }

            enemy_missiles_[i].target_x = static_cast<float>(target_x);
            enemy_missiles_[i].target_y = 15.0f;

            float speed = 1.8f + wave_ * 0.25f;
            float dx = enemy_missiles_[i].target_x - enemy_missiles_[i].x;
            float dy = enemy_missiles_[i].target_y - enemy_missiles_[i].y;
            float dist = sqrtf(dx * dx + dy * dy);
            if (dist < 0.1f) dist = 0.1f;

            enemy_missiles_[i].vx = (dx / dist) * speed;
            enemy_missiles_[i].vy = (dy / dist) * speed;

            enemy_spawn_remaining_--;
            break;
        }
    }
}

bool Game036MissileCommand::FireInterceptor() {
    if (ammo_ <= 0) return false;

    for (int i = 0; i < MAX_INTERCEPTORS; ++i) {
        if (!interceptors_[i].active) {
            interceptors_[i].active = true;
            ammo_--;

            // Pick closest launch base
            int best_base = BASE_X[1];
            float min_d = 999.0f;
            for (int b = 0; b < 3; ++b) {
                float d = fabsf(crosshair_x_ - BASE_X[b]);
                if (d < min_d) {
                    min_d = d;
                    best_base = BASE_X[b];
                }
            }

            interceptors_[i].x = static_cast<float>(best_base);
            interceptors_[i].y = 15.0f;
            interceptors_[i].target_x = crosshair_x_;
            interceptors_[i].target_y = crosshair_y_;

            float speed = 18.0f;
            float dx = crosshair_x_ - interceptors_[i].x;
            float dy = crosshair_y_ - interceptors_[i].y;
            float dist = sqrtf(dx * dx + dy * dy);
            if (dist < 0.1f) dist = 0.1f;

            interceptors_[i].vx = (dx / dist) * speed;
            interceptors_[i].vy = (dy / dist) * speed;
            return true;
        }
    }
    return false;
}

void Game036MissileCommand::UpdateEnemyMissiles(float dt) {
    spawn_timer_ -= dt;
    if (spawn_timer_ <= 0.0f) {
        spawn_timer_ = 1.2f - std::min(0.8f, wave_ * 0.1f);
        SpawnEnemyMissile();
    }

    for (int i = 0; i < MAX_ENEMY_MISSILES; ++i) {
        if (!enemy_missiles_[i].active) continue;

        enemy_missiles_[i].x += enemy_missiles_[i].vx * dt;
        enemy_missiles_[i].y += enemy_missiles_[i].vy * dt;

        // Ground impact
        if (enemy_missiles_[i].y >= 15.0f) {
            enemy_missiles_[i].active = false;

            // Check if city destroyed
            for (int c = 0; c < NUM_CITIES; ++c) {
                if (cities_alive_[c] && fabsf(enemy_missiles_[i].x - CITY_X[c]) <= 1.0f) {
                    cities_alive_[c] = false;
                    break;
                }
            }

            if (GetSurvivingCities() == 0) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
            }
        }
    }
}

void Game036MissileCommand::UpdateInterceptors(float dt) {
    for (int i = 0; i < MAX_INTERCEPTORS; ++i) {
        if (!interceptors_[i].active) continue;

        interceptors_[i].x += interceptors_[i].vx * dt;
        interceptors_[i].y += interceptors_[i].vy * dt;

        // Check if reached detonation target
        float dx = interceptors_[i].target_x - interceptors_[i].x;
        float dy = interceptors_[i].target_y - interceptors_[i].y;
        float dist = sqrtf(dx * dx + dy * dy);

        if (dist <= 0.8f || interceptors_[i].y <= interceptors_[i].target_y) {
            interceptors_[i].active = false;

            // Spawn expanding explosion fireball
            for (int ex = 0; ex < MAX_EXPLOSIONS; ++ex) {
                if (!explosions_[ex].active) {
                    explosions_[ex].active = true;
                    explosions_[ex].x = interceptors_[i].target_x;
                    explosions_[ex].y = interceptors_[i].target_y;
                    explosions_[ex].radius = 0.5f;
                    explosions_[ex].max_radius = 2.0f;
                    explosions_[ex].timer = 0.6f;
                    break;
                }
            }
        }
    }
}

void Game036MissileCommand::UpdateExplosions(float dt) {
    for (int i = 0; i < MAX_EXPLOSIONS; ++i) {
        if (!explosions_[i].active) continue;

        explosions_[i].timer -= dt;
        if (explosions_[i].timer <= 0.0f) {
            explosions_[i].active = false;
            continue;
        }

        // Expand and then contract
        if (explosions_[i].timer > 0.3f) {
            explosions_[i].radius = std::min(explosions_[i].max_radius,
                explosions_[i].radius + 6.0f * dt);
        } else {
            explosions_[i].radius = std::max(0.3f,
                explosions_[i].radius - 4.0f * dt);
        }

        // Check collision with enemy missiles
        for (int m = 0; m < MAX_ENEMY_MISSILES; ++m) {
            if (enemy_missiles_[m].active) {
                float dx = enemy_missiles_[m].x - explosions_[i].x;
                float dy = enemy_missiles_[m].y - explosions_[i].y;
                float dist = sqrtf(dx * dx + dy * dy);
                if (dist <= explosions_[i].radius) {
                    enemy_missiles_[m].active = false;
                    score_ += 100;
                    if (score_ > high_score_) high_score_ = score_;
                }
            }
        }
    }
}

void Game036MissileCommand::CheckWaveEnd() {
    if (enemy_spawn_remaining_ <= 0) {
        bool any_missiles = false;
        for (int i = 0; i < MAX_ENEMY_MISSILES; ++i) {
            if (enemy_missiles_[i].active) {
                any_missiles = true;
                break;
            }
        }

        if (!any_missiles) {
            state_ = STATE_WAVE_CLEAR;
            state_timer_ = 0.0f;
            score_ += GetSurvivingCities() * 100 + ammo_ * 5;
            if (score_ > high_score_) high_score_ = score_;
        }
    }
}

void Game036MissileCommand::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER) {
        if (state_timer_ >= 2.0f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_WAVE_CLEAR) {
        if (state_timer_ >= 1.5f) {
            wave_++;
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            InitWave();
        }
        return;
    }

    // 1. Crosshair Movement
    const float speed = 12.0f;
    if (buttons & KEY_LEFT)  crosshair_x_ = std::max(0.5f, crosshair_x_ - speed * dt);
    if (buttons & KEY_RIGHT) crosshair_x_ = std::min(14.5f, crosshair_x_ + speed * dt);
    if (buttons & KEY_UP)    crosshair_y_ = std::max(1.0f, crosshair_y_ - speed * dt);
    if (buttons & KEY_DOWN)  crosshair_y_ = std::min(14.0f, crosshair_y_ + speed * dt);

    // 2. Fire Interceptor
    if ((buttons & KEY_A) && !(prev_buttons & KEY_A)) {
        FireInterceptor();
    }

    UpdateEnemyMissiles(dt);
    UpdateInterceptors(dt);
    UpdateExplosions(dt);
    CheckWaveEnd();
}

void Game036MissileCommand::Render(uint8_t* fb) {
    // Night Sky: Deep Space Black (#050810)
    for (int i = 0; i < 256; ++i) {
        fb[i * 3 + 0] = 5;
        fb[i * 3 + 1] = 8;
        fb[i * 3 + 2] = 16;
    }

    // 1. Ground and Bases (Row 15)
    for (int x = 0; x < 16; ++x) {
        int idx = (15 * 16 + x) * 3;
        fb[idx + 0] = 180; fb[idx + 1] = 130; fb[idx + 2] = 70; // Ochre ground
    }

    // Draw 3 Missile Bases
    for (int b = 0; b < 3; ++b) {
        int bx = BASE_X[b];
        int idx = (15 * 16 + bx) * 3;
        fb[idx + 0] = 52; fb[idx + 1] = 152; fb[idx + 2] = 219; // Blue silo
        if (ammo_ > 0) {
            int top_idx = (14 * 16 + bx) * 3;
            fb[top_idx + 0] = 236; fb[top_idx + 1] = 240; fb[top_idx + 2] = 241;
        }
    }

    // Draw Cities (Cyan / Gold blocks)
    for (int c = 0; c < NUM_CITIES; ++c) {
        if (cities_alive_[c]) {
            int cx = CITY_X[c];
            int idx = (15 * 16 + cx) * 3;
            fb[idx + 0] = 46; fb[idx + 1] = 204; fb[idx + 2] = 113; // Emerald City
        }
    }

    // 2. Enemy Missiles (Red streaks descending)
    for (int i = 0; i < MAX_ENEMY_MISSILES; ++i) {
        if (!enemy_missiles_[i].active) continue;

        int mx = static_cast<int>(std::round(enemy_missiles_[i].x));
        int my = static_cast<int>(std::round(enemy_missiles_[i].y));

        if (mx >= 0 && mx < 16 && my >= 0 && my < 16) {
            int idx = (my * 16 + mx) * 3;
            fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Crimson warhead
        }
    }

    // 3. Interceptors (White trails ascending)
    for (int i = 0; i < MAX_INTERCEPTORS; ++i) {
        if (!interceptors_[i].active) continue;

        int ix = static_cast<int>(std::round(interceptors_[i].x));
        int iy = static_cast<int>(std::round(interceptors_[i].y));

        if (ix >= 0 && ix < 16 && iy >= 0 && iy < 16) {
            int idx = (iy * 16 + ix) * 3;
            fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255;
        }
    }

    // 4. Expanding Explosions (Fiery Red / Amber / Yellow blast sphere)
    for (int i = 0; i < MAX_EXPLOSIONS; ++i) {
        if (!explosions_[i].active) continue;

        int ex = static_cast<int>(std::round(explosions_[i].x));
        int ey = static_cast<int>(std::round(explosions_[i].y));
        int r = static_cast<int>(std::round(explosions_[i].radius));

        for (int dy = -r; dy <= r; ++dy) {
            for (int dx = -r; dx <= r; ++dx) {
                if (dx * dx + dy * dy <= r * r) {
                    int px = ex + dx;
                    int py = ey + dy;
                    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
                        int idx = (py * 16 + px) * 3;
                        fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15; // Golden Fireball
                    }
                }
            }
        }
    }

    // 5. Crosshair (Green Reticle)
    int hx = static_cast<int>(std::round(crosshair_x_));
    int hy = static_cast<int>(std::round(crosshair_y_));

    if (hx >= 0 && hx < 16 && hy >= 0 && hy < 16) {
        int idx = (hy * 16 + hx) * 3;
        fb[idx + 0] = 46; fb[idx + 1] = 204; fb[idx + 2] = 113;
        if (hx > 0) {
            int l_idx = (hy * 16 + (hx - 1)) * 3;
            fb[l_idx + 0] = 46; fb[l_idx + 1] = 204; fb[l_idx + 2] = 113;
        }
        if (hx < 15) {
            int r_idx = (hy * 16 + (hx + 1)) * 3;
            fb[r_idx + 0] = 46; fb[r_idx + 1] = 204; fb[r_idx + 2] = 113;
        }
        if (hy > 0) {
            int u_idx = ((hy - 1) * 16 + hx) * 3;
            fb[u_idx + 0] = 46; fb[u_idx + 1] = 204; fb[u_idx + 2] = 113;
        }
        if (hy < 15) {
            int d_idx = ((hy + 1) * 16 + hx) * 3;
            fb[d_idx + 0] = 46; fb[d_idx + 1] = 204; fb[d_idx + 2] = 113;
        }
    }
}

} // namespace arcade
