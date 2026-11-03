#include "game_122_bosconian.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static float WrapCoord(float val, float max_val = 48.0f) {
    while (val < 0.0f) val += max_val;
    while (val >= max_val) val -= max_val;
    return val;
}

static float WrapDiff(float a, float b, float max_val = 48.0f) {
    float diff = a - b;
    while (diff > max_val * 0.5f) diff -= max_val;
    while (diff < -max_val * 0.5f) diff += max_val;
    return diff;
}

Game122Bosconian::Game122Bosconian() {
    Reset();
}

void Game122Bosconian::Init() {
    Reset();
}

void Game122Bosconian::Reset() {
    score_ = 0;
    lives_ = 3;
    round_ = 1;
    InitSector();
}

void Game122Bosconian::InitSector() {
    state_ = STATE_FLYING;
    state_timer_ = 0.0f;
    alert_ = ALERT_GREEN;
    spawn_timer_ = 1.0f;

    px_ = 24.0f;
    py_ = 24.0f;
    vx_ = 0.0f;
    vy_ = -5.0f;
    dir_x_ = 0;
    dir_y_ = -1;

    // 3 Space Stations positioned across 48x48 sector
    float station_coords[3][2] = {
        {12.0f, 12.0f},
        {36.0f, 12.0f},
        {24.0f, 36.0f}
    };

    for (int i = 0; i < MAX_STATIONS; ++i) {
        stations_[i].x = station_coords[i][0];
        stations_[i].y = station_coords[i][1];
        stations_[i].core_alive = true;
        for (int p = 0; p < 6; ++p) stations_[i].pods_alive[p] = true;
        stations_[i].active = true;
    }

    for (int i = 0; i < MAX_BULLETS; ++i) bullets_[i].active = false;
    for (int i = 0; i < MAX_INTERCEPTORS; ++i) interceptors_[i].active = false;
}

void Game122Bosconian::FireTwinCannons() {
    if (state_ != STATE_FLYING) return;

    // Fire Forward Bullet
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].x = WrapCoord(px_ + static_cast<float>(dir_x_) * 1.0f);
            bullets_[i].y = WrapCoord(py_ + static_cast<float>(dir_y_) * 1.0f);
            bullets_[i].vx = static_cast<float>(dir_x_) * 22.0f;
            bullets_[i].vy = static_cast<float>(dir_y_) * 22.0f;
            bullets_[i].life = 0.8f;
            bullets_[i].active = true;
            break;
        }
    }

    // Fire Backward Bullet (Simultaneous twin cannon signature!)
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].x = WrapCoord(px_ - static_cast<float>(dir_x_) * 1.0f);
            bullets_[i].y = WrapCoord(py_ - static_cast<float>(dir_y_) * 1.0f);
            bullets_[i].vx = -static_cast<float>(dir_x_) * 22.0f;
            bullets_[i].vy = -static_cast<float>(dir_y_) * 22.0f;
            bullets_[i].life = 0.8f;
            bullets_[i].active = true;
            break;
        }
    }
}

void Game122Bosconian::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PLAYER_EXPLODING) {
        if (state_timer_ > 1.2f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_FLYING;
                px_ = 24.0f;
                py_ = 24.0f;
                vx_ = 0.0f;
                vy_ = -5.0f;
                dir_x_ = 0;
                dir_y_ = -1;
            }
        }
        return;
    }

    if (state_ == STATE_SECTOR_CLEAR) {
        if (state_timer_ > 1.6f) {
            round_++;
            score_ += 2000;
            InitSector();
        }
        return;
    }

    if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
        FireTwinCannons();
    }

    UpdateShip(dt, buttons);
    UpdateStations(dt);
    UpdateInterceptors(dt);
    UpdateBullets(dt);
    CheckCollisions();
    CheckSectorClear();
}

void Game122Bosconian::UpdateShip(float dt, uint32_t buttons) {
    // 8-way directional heading
    int in_x = 0;
    int in_y = 0;
    if (buttons & BTN_LEFT)  in_x -= 1;
    if (buttons & BTN_RIGHT) in_x += 1;
    if (buttons & BTN_UP)    in_y -= 1;
    if (buttons & BTN_DOWN)  in_y += 1;

    if (in_x != 0 || in_y != 0) {
        dir_x_ = in_x;
        dir_y_ = in_y;
    }

    float cruise_speed = 6.0f;
    float len = std::sqrt(static_cast<float>(dir_x_ * dir_x_ + dir_y_ * dir_y_));
    if (len > 0.0f) {
        vx_ = (static_cast<float>(dir_x_) / len) * cruise_speed;
        vy_ = (static_cast<float>(dir_y_) / len) * cruise_speed;
    }

    px_ = WrapCoord(px_ + vx_ * dt);
    py_ = WrapCoord(py_ + vy_ * dt);
}

void Game122Bosconian::UpdateStations(float dt) {
    for (int i = 0; i < MAX_STATIONS; ++i) {
        if (!stations_[i].active) continue;

        // Check if all 6 outer pods are destroyed
        bool any_pod_alive = false;
        for (int p = 0; p < 6; ++p) {
            if (stations_[i].pods_alive[p]) {
                any_pod_alive = true;
                break;
            }
        }

        if (!any_pod_alive || !stations_[i].core_alive) {
            // Station eliminated!
            stations_[i].active = false;
            score_ += (!stations_[i].core_alive) ? 1500 : 800;
        }
    }
}

void Game122Bosconian::UpdateInterceptors(float dt) {
    spawn_timer_ -= dt;
    if (spawn_timer_ <= 0.0f) {
        spawn_timer_ = (alert_ == ALERT_RED) ? 1.5f : 3.5f;

        for (int i = 0; i < MAX_INTERCEPTORS; ++i) {
            if (!interceptors_[i].active) {
                // Spawn offscreen relative to player
                interceptors_[i].x = WrapCoord(px_ + ((i % 2 == 0) ? 14.0f : -14.0f));
                interceptors_[i].y = WrapCoord(py_ + ((i > 1) ? 14.0f : -14.0f));
                interceptors_[i].is_spy = (i == 0 && alert_ != ALERT_RED);
                interceptors_[i].active = true;
                break;
            }
        }
    }

    for (int i = 0; i < MAX_INTERCEPTORS; ++i) {
        if (!interceptors_[i].active) continue;

        float dx = WrapDiff(px_, interceptors_[i].x);
        float dy = WrapDiff(py_, interceptors_[i].y);
        float dist = std::sqrt(dx * dx + dy * dy);

        if (interceptors_[i].is_spy) {
            // Spy ship flees away from player
            interceptors_[i].vx = (dx > 0) ? -4.5f : 4.5f;
            interceptors_[i].vy = (dy > 0) ? -4.5f : 4.5f;
            if (dist > 18.0f) {
                // Spy escaped! Sound Condition Red!
                alert_ = ALERT_RED;
                interceptors_[i].active = false;
            }
        } else {
            // Attack interceptor chases player
            if (dist > 0.5f) {
                float spd = (alert_ == ALERT_RED) ? 5.2f : 3.8f;
                interceptors_[i].vx = (dx / dist) * spd;
                interceptors_[i].vy = (dy / dist) * spd;
            }
        }

        interceptors_[i].x = WrapCoord(interceptors_[i].x + interceptors_[i].vx * dt);
        interceptors_[i].y = WrapCoord(interceptors_[i].y + interceptors_[i].vy * dt);
    }
}

void Game122Bosconian::UpdateBullets(float dt) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        bullets_[i].life -= dt;
        if (bullets_[i].life <= 0.0f) {
            bullets_[i].active = false;
            continue;
        }
        bullets_[i].x = WrapCoord(bullets_[i].x + bullets_[i].vx * dt);
        bullets_[i].y = WrapCoord(bullets_[i].y + bullets_[i].vy * dt);
    }
}

void Game122Bosconian::CheckCollisions() {
    // 1. Bullets vs Stations
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;

        for (int s = 0; s < MAX_STATIONS; ++s) {
            if (!stations_[s].active) continue;

            // Check Central Core hit
            float cdx = std::abs(WrapDiff(bullets_[b].x, stations_[s].x));
            float cdy = std::abs(WrapDiff(bullets_[b].y, stations_[s].y));
            if (cdx < 0.9f && cdy < 0.9f && stations_[s].core_alive) {
                bullets_[b].active = false;
                stations_[s].core_alive = false; // Core pierced!
                break;
            }

            // Check 6 Outer Pods hit
            float pod_offsets[6][2] = {
                {0.0f, -1.8f}, {1.5f, -0.9f}, {1.5f, 0.9f},
                {0.0f, 1.8f}, {-1.5f, 0.9f}, {-1.5f, -0.9f}
            };

            for (int p = 0; p < 6; ++p) {
                if (!stations_[s].pods_alive[p]) continue;
                float px = stations_[s].x + pod_offsets[p][0];
                float py = stations_[s].y + pod_offsets[p][1];
                float pdx = std::abs(WrapDiff(bullets_[b].x, px));
                float pdy = std::abs(WrapDiff(bullets_[b].y, py));
                if (pdx < 0.8f && pdy < 0.8f) {
                    bullets_[b].active = false;
                    stations_[s].pods_alive[p] = false;
                    score_ += 100;
                    break;
                }
            }
        }

        // Bullets vs Interceptors
        for (int i = 0; i < MAX_INTERCEPTORS; ++i) {
            if (!interceptors_[i].active) continue;
            float dx = std::abs(WrapDiff(bullets_[b].x, interceptors_[i].x));
            float dy = std::abs(WrapDiff(bullets_[b].y, interceptors_[i].y));
            if (dx < 0.9f && dy < 0.9f) {
                bullets_[b].active = false;
                interceptors_[i].active = false;
                score_ += (interceptors_[i].is_spy) ? 300 : 100;
                break;
            }
        }
    }

    // 2. Player vs Interceptors
    for (int i = 0; i < MAX_INTERCEPTORS; ++i) {
        if (!interceptors_[i].active) continue;
        float dx = std::abs(WrapDiff(px_, interceptors_[i].x));
        float dy = std::abs(WrapDiff(py_, interceptors_[i].y));
        if (dx < 0.8f && dy < 0.8f) {
            state_ = STATE_PLAYER_EXPLODING;
            state_timer_ = 0.0f;
            interceptors_[i].active = false;
            break;
        }
    }

    // 3. Player vs Station Body / Core
    for (int s = 0; s < MAX_STATIONS; ++s) {
        if (!stations_[s].active) continue;
        float dx = std::abs(WrapDiff(px_, stations_[s].x));
        float dy = std::abs(WrapDiff(py_, stations_[s].y));
        if (dx < 1.4f && dy < 1.4f) {
            state_ = STATE_PLAYER_EXPLODING;
            state_timer_ = 0.0f;
            break;
        }
    }
}

void Game122Bosconian::CheckSectorClear() {
    bool any_station = false;
    for (int s = 0; s < MAX_STATIONS; ++s) {
        if (stations_[s].active) {
            any_station = true;
            break;
        }
    }

    if (!any_station) {
        state_ = STATE_SECTOR_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game122Bosconian::Render(uint8_t* fb) {
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

    // 1. Radar Minimap on Top Row (y = 0)
    for (int rx = 0; rx < 16; ++rx) {
        set_pixel(rx, 0, 10, 20, 40);
    }
    // Radar station dots (Green/Cyan)
    for (int s = 0; s < MAX_STATIONS; ++s) {
        if (stations_[s].active) {
            int rx = static_cast<int>(stations_[s].x / 48.0f * 16.0f);
            set_pixel(rx, 0, 0, 255, 120);
        }
    }
    // Radar player dot (White)
    int r_px = static_cast<int>(px_ / 48.0f * 16.0f);
    set_pixel(r_px, 0, 255, 255, 255);

    // Alert indicator on radar corner
    if (alert_ == ALERT_RED) set_pixel(15, 0, 255, 30, 20);
    else if (alert_ == ALERT_YELLOW) set_pixel(15, 0, 255, 220, 0);

    // 2. Space Stations
    float pod_offsets[6][2] = {
        {0.0f, -1.8f}, {1.5f, -0.9f}, {1.5f, 0.9f},
        {0.0f, 1.8f}, {-1.5f, 0.9f}, {-1.5f, -0.9f}
    };

    for (int s = 0; s < MAX_STATIONS; ++s) {
        if (!stations_[s].active) continue;
        float scx = WrapDiff(stations_[s].x, px_) + 7.5f;
        float scy = WrapDiff(stations_[s].y, py_) + 7.5f;

        // Central Core
        int iscx = static_cast<int>(std::round(scx));
        int iscy = static_cast<int>(std::round(scy));
        if (stations_[s].core_alive) {
            set_pixel(iscx, iscy, 255, 220, 0); // Luminous yellow nuclear core
        }

        // 6 Pods
        for (int p = 0; p < 6; ++p) {
            if (!stations_[s].pods_alive[p]) continue;
            int px_screen = static_cast<int>(std::round(scx + pod_offsets[p][0]));
            int py_screen = static_cast<int>(std::round(scy + pod_offsets[p][1]));
            set_pixel(px_screen, py_screen, 40, 180, 240); // Metallic cyan cannon pod
        }
    }

    // 3. Interceptors
    for (int i = 0; i < MAX_INTERCEPTORS; ++i) {
        if (!interceptors_[i].active) continue;
        float sx = WrapDiff(interceptors_[i].x, px_) + 7.5f;
        float sy = WrapDiff(interceptors_[i].y, py_) + 7.5f;
        int isx = static_cast<int>(std::round(sx));
        int isy = static_cast<int>(std::round(sy));

        if (interceptors_[i].is_spy) {
            set_pixel(isx, isy, 255, 240, 0); // Yellow spy ship
            set_pixel(isx, isy - 1, 255, 120, 0);
        } else {
            set_pixel(isx, isy, 255, 40, 20); // Crimson attack craft
        }
    }

    // 4. Bullets
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;
        float sx = WrapDiff(bullets_[b].x, px_) + 7.5f;
        float sy = WrapDiff(bullets_[b].y, py_) + 7.5f;
        set_pixel(static_cast<int>(std::round(sx)), static_cast<int>(std::round(sy)), 255, 255, 255);
    }

    // 5. Starfighter at Screen Center (7..8)
    if (state_ == STATE_FLYING || state_ == STATE_SECTOR_CLEAR) {
        int cx = 8;
        int cy = 8;
        set_pixel(cx, cy, 255, 255, 255); // White cockpit
        set_pixel(cx + dir_x_, cy + dir_y_, 40, 140, 255); // Forward nose
        set_pixel(cx - dir_x_, cy - dir_y_, 255, 120, 20); // Rear thruster flame
    } else if (state_ == STATE_PLAYER_EXPLODING) {
        int cx = 8;
        int cy = 8;
        set_pixel(cx, cy, 255, 220, 50);
        set_pixel(cx - 1, cy - 1, 255, 60, 20);
        set_pixel(cx + 1, cy + 1, 255, 60, 20);
        set_pixel(cx + 1, cy - 1, 255, 180, 0);
    }

    // 6. Lives Indicator (Top-left x=0..2)
    for (int l = 0; l < lives_; ++l) {
        set_pixel(l * 2, 1, 40, 140, 255);
    }
}

} // namespace arcade