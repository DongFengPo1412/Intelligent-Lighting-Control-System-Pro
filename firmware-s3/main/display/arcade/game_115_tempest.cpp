#include "game_115_tempest.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr float PI = 3.1415926535f;

static void GetSectorPos(int sector, float depth, float& out_x, float& out_y) {
    float angle = static_cast<float>(sector) * (2.0f * PI / 16.0f) - (PI * 0.5f);
    float r = 1.0f + depth * 6.2f;
    out_x = 7.5f + std::cos(angle) * r;
    out_y = 7.5f + std::sin(angle) * r;
}

Game115Tempest::Game115Tempest() {
    Reset();
}

void Game115Tempest::Init() {
    Reset();
}

void Game115Tempest::Reset() {
    score_ = 0;
    lives_ = 3;
    wave_ = 1;
    InitWave();
}

void Game115Tempest::InitWave() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    super_zappers_ = 1;
    player_sector_ = 0;
    move_timer_ = 0.0f;
    spawn_timer_ = 0.5f;
    enemies_remaining_ = 6 + wave_ * 2;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = false;
    }
    for (int i = 0; i < MAX_SHOTS; ++i) {
        shots_[i].active = false;
    }
}

void Game115Tempest::TriggerSuperZapper() {
    if (super_zappers_ <= 0 || state_ != STATE_PLAYING) return;
    super_zappers_--;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].active) {
            enemies_[i].active = false;
            score_ += 150;
        }
    }
}

void Game115Tempest::FireShot() {
    for (int i = 0; i < MAX_SHOTS; ++i) {
        if (!shots_[i].active) {
            shots_[i].sector = player_sector_;
            shots_[i].depth = 0.95f;
            shots_[i].speed = 3.8f;
            shots_[i].active = true;
            break;
        }
    }
}

void Game115Tempest::SpawnEnemy() {
    if (enemies_remaining_ <= 0) return;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) {
            enemies_[i].sector = (player_sector_ + 4 + (i * 3)) % NUM_SECTORS;
            enemies_[i].depth = 0.05f;
            enemies_[i].speed = 0.35f + static_cast<float>(wave_) * 0.08f;
            enemies_[i].on_rim = false;
            enemies_[i].rim_dir = (i % 2 == 0) ? 1.0f : -1.0f;
            enemies_[i].active = true;
            enemies_remaining_--;
            break;
        }
    }
}

void Game115Tempest::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PLAYER_DYING) {
        if (state_timer_ > 1.2f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_PLAYING;
                player_sector_ = 0;
            }
        }
        return;
    }

    if (state_ == STATE_TUBE_WARP) {
        if (state_timer_ > 1.5f) {
            wave_++;
            InitWave();
        }
        return;
    }

    // Input Handling
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        FireShot();
    }
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        TriggerSuperZapper();
    }

    UpdatePlayer(dt, buttons, prev_buttons);

    // Spawner
    spawn_timer_ -= dt;
    if (spawn_timer_ <= 0.0f) {
        SpawnEnemy();
        spawn_timer_ = 1.2f;
    }

    UpdateEnemies(dt);
    UpdateShots(dt);
    CheckCollisions();
    CheckWaveClear();
}

void Game115Tempest::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    move_timer_ += dt;
    float repeat_rate = 0.12f;

    bool left_press = (buttons & BTN_LEFT) && (!(prev_buttons & BTN_LEFT) || move_timer_ > repeat_rate);
    bool right_press = (buttons & BTN_RIGHT) && (!(prev_buttons & BTN_RIGHT) || move_timer_ > repeat_rate);

    if (left_press) {
        player_sector_ = (player_sector_ - 1 + NUM_SECTORS) % NUM_SECTORS;
        move_timer_ = 0.0f;
    } else if (right_press) {
        player_sector_ = (player_sector_ + 1) % NUM_SECTORS;
        move_timer_ = 0.0f;
    }
}

void Game115Tempest::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (enemies_[i].on_rim) {
            // Flipper crawling along rim towards player
            int target = player_sector_;
            int diff = (target - enemies_[i].sector + NUM_SECTORS) % NUM_SECTORS;
            int step_dir = (diff <= 8) ? 1 : -1;

            enemies_[i].depth += dt; // use depth as rim crawl timer
            if (enemies_[i].depth >= 0.35f) {
                enemies_[i].depth = 0.0f;
                enemies_[i].sector = (enemies_[i].sector + step_dir + NUM_SECTORS) % NUM_SECTORS;
            }

            if (enemies_[i].sector == player_sector_) {
                // Claw crushed on rim!
                state_ = STATE_PLAYER_DYING;
                state_timer_ = 0.0f;
            }
        } else {
            // Climbing out from abyss pit (depth 0.0 -> 1.0)
            enemies_[i].depth += enemies_[i].speed * dt;
            if (enemies_[i].depth >= 1.0f) {
                enemies_[i].depth = 0.0f;
                enemies_[i].on_rim = true;
                if (enemies_[i].sector == player_sector_) {
                    state_ = STATE_PLAYER_DYING;
                    state_timer_ = 0.0f;
                }
            }
        }
    }
}

void Game115Tempest::UpdateShots(float dt) {
    for (int i = 0; i < MAX_SHOTS; ++i) {
        if (!shots_[i].active) continue;

        shots_[i].depth -= shots_[i].speed * dt;
        if (shots_[i].depth <= 0.0f) {
            shots_[i].active = false;
        }
    }
}

void Game115Tempest::CheckCollisions() {
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active) continue;

        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;

            if (enemies_[e].sector == shots_[s].sector) {
                // Same sector lane collision
                if (enemies_[e].on_rim || std::abs(enemies_[e].depth - shots_[s].depth) < 0.25f) {
                    shots_[s].active = false;
                    enemies_[e].active = false;
                    score_ += (enemies_[e].on_rim ? 200 : 150);
                    break;
                }
            }
        }
    }
}

void Game115Tempest::CheckWaveClear() {
    if (enemies_remaining_ > 0) return;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].active) return;
    }

    state_ = STATE_TUBE_WARP;
    state_timer_ = 0.0f;
    score_ += 1000;
}

void Game115Tempest::Render(uint8_t* fb) {
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

    // 1. Vector Wireframe 3D Tunnel Spokes
    for (int s = 0; s < NUM_SECTORS; ++s) {
        float x1, y1, x2, y2;
        GetSectorPos(s, 0.0f, x1, y1);
        GetSectorPos(s, 1.0f, x2, y2);

        int ix1 = static_cast<int>(std::round(x1));
        int iy1 = static_cast<int>(std::round(y1));
        int ix2 = static_cast<int>(std::round(x2));
        int iy2 = static_cast<int>(std::round(y2));

        // Abyss pit ring (Deep blue)
        set_pixel(ix1, iy1, 15, 30, 80);
        // Outer rim ring (Neon cyan / electric blue)
        set_pixel(ix2, iy2, 0, 140, 255);
    }

    // 2. Shots in tunnel
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active) continue;
        float sx, sy;
        GetSectorPos(shots_[s].sector, shots_[s].depth, sx, sy);
        int isx = static_cast<int>(std::round(sx));
        int isy = static_cast<int>(std::round(sy));
        set_pixel(isx, isy, 255, 255, 255); // Radiant white pulse
    }

    // 3. Enemies in tunnel or crawling rim
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        float ex, ey;
        float d = enemies_[e].on_rim ? 1.0f : enemies_[e].depth;
        GetSectorPos(enemies_[e].sector, d, ex, ey);
        int iex = static_cast<int>(std::round(ex));
        int iey = static_cast<int>(std::round(ey));

        if (enemies_[e].on_rim) {
            // Menacing red/orange flipper crawling on rim
            set_pixel(iex, iey, 255, 40, 20);
        } else {
            // Climbing flipper (Bright crimson/yellow)
            set_pixel(iex, iey, 255, 180, 0);
        }
    }

    // 4. Player Yellow Claw on outer rim
    if (state_ == STATE_PLAYING || state_ == STATE_TUBE_WARP) {
        float px, py;
        GetSectorPos(player_sector_, 1.0f, px, py);
        int ipx = static_cast<int>(std::round(px));
        int ipy = static_cast<int>(std::round(py));
        // Golden vector claw
        set_pixel(ipx, ipy, 255, 240, 0);

        // Straddling dual prongs
        float p1x, p1y, p2x, p2y;
        GetSectorPos((player_sector_ + 1) % NUM_SECTORS, 0.95f, p1x, p1y);
        GetSectorPos((player_sector_ - 1 + NUM_SECTORS) % NUM_SECTORS, 0.95f, p2x, p2y);
        set_pixel(static_cast<int>(std::round(p1x)), static_cast<int>(std::round(p1y)), 220, 180, 0);
        set_pixel(static_cast<int>(std::round(p2x)), static_cast<int>(std::round(p2y)), 220, 180, 0);
    } else if (state_ == STATE_PLAYER_DYING) {
        float px, py;
        GetSectorPos(player_sector_, 1.0f, px, py);
        int ipx = static_cast<int>(std::round(px));
        int ipy = static_cast<int>(std::round(py));
        // Claw shattering explosion
        set_pixel(ipx, ipy, 255, 255, 255);
        set_pixel((ipx + 1) % 16, ipy, 255, 60, 20);
        set_pixel((ipx + 15) % 16, ipy, 255, 60, 20);
        set_pixel(ipx, (ipy + 1) % 16, 255, 200, 0);
    }

    // 5. SuperZapper HUD indicator on top-right (x=15, y=0)
    if (super_zappers_ > 0) {
        set_pixel(15, 0, 255, 0, 255); // Magenta Zapper charge
    }

    // 6. Lives HUD on top-left (x=0..2, y=0)
    for (int l = 0; l < lives_; ++l) {
        set_pixel(l * 2, 0, 255, 240, 0);
    }
}

} // namespace arcade