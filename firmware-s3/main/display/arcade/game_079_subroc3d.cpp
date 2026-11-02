#include "game_079_subroc3d.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace arcade {

Game079SubRoc3D::Game079SubRoc3D() {
    Reset();
}

void Game079SubRoc3D::Init() {
    Reset();
}

void Game079SubRoc3D::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    targets_destroyed_ = 0;
    cx_ = 7.5f;
    cy_ = 7.5f;
    spawn_timer_ = 0.0f;

    for (int i = 0; i < MAX_TARGETS; ++i) {
        targets_[i].active = false;
    }
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        projs_[i].active = false;
    }

    // Spawn 2 initial targets
    SpawnTarget();
    SpawnTarget();
}

int Game079SubRoc3D::GetActiveTargetsCount() const {
    int count = 0;
    for (int i = 0; i < MAX_TARGETS; ++i) {
        if (targets_[i].active) count++;
    }
    return count;
}

void Game079SubRoc3D::SpawnTarget() {
    for (int i = 0; i < MAX_TARGETS; ++i) {
        if (!targets_[i].active) {
            targets_[i].active = true;
            targets_[i].z = 10.0f;
            targets_[i].hp = 1;
            targets_[i].vz = -1.2f - (std::rand() % 10) * 0.08f;

            int z_type = std::rand() % 3;
            if (z_type == 0) {
                // Sky Air Fighter (y: 2..5)
                targets_[i].zone = ZONE_AIR;
                targets_[i].x = 4.0f + (std::rand() % 8);
                targets_[i].y = 2.0f + (std::rand() % 4);
                targets_[i].vx = ((std::rand() % 20) - 10) * 0.15f;
                targets_[i].vy = 0.2f;
            } else if (z_type == 1) {
                // Surface Destroyer (y: 6..8)
                targets_[i].zone = ZONE_SURFACE;
                targets_[i].x = (std::rand() % 2 == 0) ? 1.0f : 14.0f;
                targets_[i].y = 7.0f;
                targets_[i].vx = (targets_[i].x < 7.5f) ? 0.8f : -0.8f;
                targets_[i].vy = 0.0f;
            } else {
                // Underwater Mine / Sub (y: 9..13)
                targets_[i].zone = ZONE_DEPTH;
                targets_[i].x = 3.0f + (std::rand() % 10);
                targets_[i].y = 9.0f + (std::rand() % 4);
                targets_[i].vx = ((std::rand() % 20) - 10) * 0.1f;
                targets_[i].vy = 0.1f;
            }
            break;
        }
    }
}

void Game079SubRoc3D::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f && (buttons & (BUTTON_A | BUTTON_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PLAYER_HIT) {
        if (state_timer_ > 1.2f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
            } else {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            }
        }
        return;
    }

    // Spawn enemy cadence
    spawn_timer_ += dt;
    if (spawn_timer_ > 2.0f) {
        spawn_timer_ = 0.0f;
        SpawnTarget();
    }

    UpdateCrosshair(dt, buttons);

    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        FireTorpedo();
    }
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        FireAirMissile();
    }

    UpdateTargets(dt);
    UpdateProjectiles(dt);
    CheckHits();
}

void Game079SubRoc3D::UpdateCrosshair(float dt, uint32_t buttons) {
    float speed = 7.5f;
    if (buttons & BUTTON_LEFT)  cx_ -= speed * dt;
    if (buttons & BUTTON_RIGHT) cx_ += speed * dt;
    if (buttons & BUTTON_UP)    cy_ -= speed * dt;
    if (buttons & BUTTON_DOWN)  cy_ += speed * dt;

    cx_ = std::max(1.0f, std::min(14.0f, cx_));
    cy_ = std::max(1.0f, std::min(14.0f, cy_));
}

void Game079SubRoc3D::FireTorpedo() {
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projs_[i].active) {
            projs_[i].active = true;
            projs_[i].x = cx_;
            projs_[i].y = std::max(7.0f, cy_); // Torpedo launches at or below sea level
            projs_[i].z = 1.0f;
            projs_[i].vz = 14.0f;
            projs_[i].is_air_missile = false;
            break;
        }
    }
}

void Game079SubRoc3D::FireAirMissile() {
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projs_[i].active) {
            projs_[i].active = true;
            projs_[i].x = cx_;
            projs_[i].y = std::min(7.0f, cy_); // Air missile launches upwards
            projs_[i].z = 1.0f;
            projs_[i].vz = 14.0f;
            projs_[i].is_air_missile = true;
            break;
        }
    }
}

void Game079SubRoc3D::UpdateTargets(float dt) {
    for (int i = 0; i < MAX_TARGETS; ++i) {
        if (!targets_[i].active) continue;

        targets_[i].x += targets_[i].vx * dt;
        targets_[i].y += targets_[i].vy * dt;
        targets_[i].z += targets_[i].vz * dt;

        // Threat reaches submarine hull
        if (targets_[i].z <= 1.2f) {
            targets_[i].active = false;
            lives_--;
            state_ = STATE_PLAYER_HIT;
            state_timer_ = 0.0f;
            return;
        }

        // Horizontal bounce or re-center
        if (targets_[i].x < 1.0f) {
            targets_[i].x = 1.0f;
            targets_[i].vx = std::abs(targets_[i].vx);
        } else if (targets_[i].x > 14.0f) {
            targets_[i].x = 14.0f;
            targets_[i].vx = -std::abs(targets_[i].vx);
        }
    }
}

void Game079SubRoc3D::UpdateProjectiles(float dt) {
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projs_[i].active) continue;

        projs_[i].z += projs_[i].vz * dt;
        if (projs_[i].z >= 10.0f) {
            projs_[i].active = false;
        }
    }
}

void Game079SubRoc3D::CheckHits() {
    for (int p = 0; p < MAX_PROJECTILES; ++p) {
        if (!projs_[p].active) continue;

        for (int t = 0; t < MAX_TARGETS; ++t) {
            if (!targets_[t].active) continue;

            // Weapon compatibility check: Air missile for sky, Torpedo for surface & depth
            if (projs_[p].is_air_missile && targets_[t].zone != ZONE_AIR) continue;
            if (!projs_[p].is_air_missile && targets_[t].zone == ZONE_AIR) continue;

            // 3D Hitbox: depth difference < 1.4, screen x & y proximity
            float dz = std::abs(projs_[p].z - targets_[t].z);
            float dx = std::abs(projs_[p].x - targets_[t].x);
            float dy = std::abs(projs_[p].y - targets_[t].y);

            if (dz < 1.5f && dx < 1.6f && dy < 1.6f) {
                targets_[t].active = false;
                projs_[p].active = false;
                targets_destroyed_++;

                int pts = (targets_[t].zone == ZONE_AIR) ? 300 : ((targets_[t].zone == ZONE_SURFACE) ? 500 : 400);
                score_ += pts;
                if (score_ > high_score_) high_score_ = score_;

                if (targets_destroyed_ >= 15) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 5000;
                }
                break;
            }
        }
    }
}

void Game079SubRoc3D::Render(uint8_t* fb) {
    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Sky (y: 0..6)
    for (int y = 0; y < 7; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 10, 20, 50); // Dark marine twilight
        }
    }

    // 2. Horizon Sea Level (y: 7)
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 7, 30, 80, 140);
    }

    // 3. Deep Ocean (y: 8..15)
    for (int y = 8; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 5, 25, 45); // Deep ocean blue
        }
    }

    // Flash red on hit
    if (state_ == STATE_PLAYER_HIT) {
        for (int i = 0; i < 16 * 16 * 3; i += 3) {
            fb[i] = std::min(255, fb[i] + 120);
        }
    }

    // 4. Targets (size scales with z depth: far = 1px, close = 2x2 or 3x3)
    for (int i = 0; i < MAX_TARGETS; ++i) {
        if (!targets_[i].active) continue;

        int tx = static_cast<int>(std::round(targets_[i].x));
        int ty = static_cast<int>(std::round(targets_[i].y));
        float z = targets_[i].z;

        if (targets_[i].zone == ZONE_AIR) {
            // Fighter Jet (Bright red/yellow)
            set_pixel(tx, ty, 255, 60, 40);
            if (z < 5.0f) {
                set_pixel(tx - 1, ty, 255, 180, 0);
                set_pixel(tx + 1, ty, 255, 180, 0);
            }
        } else if (targets_[i].zone == ZONE_SURFACE) {
            // Warship (Grey / orange lights)
            set_pixel(tx, ty, 200, 200, 210);
            if (z < 6.0f) {
                set_pixel(tx - 1, ty, 150, 150, 160);
                set_pixel(tx + 1, ty, 150, 150, 160);
                set_pixel(tx, ty - 1, 255, 100, 0);
            }
        } else {
            // Depth Mine / Sub (Toxic lime / orange)
            set_pixel(tx, ty, 50, 255, 120);
            if (z < 5.0f) {
                set_pixel(tx, ty - 1, 255, 60, 20);
                set_pixel(tx, ty + 1, 255, 60, 20);
            }
        }
    }

    // 5. Projectiles (Torpedo / Air Missile)
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projs_[i].active) continue;
        int px = static_cast<int>(std::round(projs_[i].x));
        int py = static_cast<int>(std::round(projs_[i].y));
        if (projs_[i].is_air_missile) {
            set_pixel(px, py, 255, 255, 100);
            set_pixel(px, py + 1, 255, 100, 0); // exhaust flame
        } else {
            set_pixel(px, py, 80, 220, 255);
            set_pixel(px, py + 1, 40, 140, 255); // bubble wake
        }
    }

    // 6. Periscope Crosshair (Reticle)
    int cx = static_cast<int>(std::round(cx_));
    int cy = static_cast<int>(std::round(cy_));

    // Green crosshair with center dot
    set_pixel(cx - 1, cy, 50, 255, 50);
    set_pixel(cx + 1, cy, 50, 255, 50);
    set_pixel(cx, cy - 1, 50, 255, 50);
    set_pixel(cx, cy + 1, 50, 255, 50);
    set_pixel(cx, cy, 255, 255, 255);

    // 7. Submarine Hull Life Bar (y = 0)
    for (int l = 0; l < lives_; ++l) {
        set_pixel(l * 2, 0, 40, 220, 255);
    }
}

} // namespace arcade
