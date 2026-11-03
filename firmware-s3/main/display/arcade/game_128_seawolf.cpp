#include "game_128_seawolf.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace arcade {

static constexpr float LANE_Y[3] = {2.5f, 4.5f, 6.5f};
static constexpr float MINE_Y = 9.0f;

Game128SeaWolf::Game128SeaWolf() {
    Init();
}

void Game128SeaWolf::Init() {
    score_ = 0;
    patrol_round_ = 1;
    InitPatrol();
}

void Game128SeaWolf::Reset() {
    Init();
}

void Game128SeaWolf::InitPatrol() {
    state_ = STATE_HUNTING;
    state_timer_ = 0.0f;
    time_remaining_ = 60.0f;
    ships_sunk_ = 0;
    periscope_x_ = 7.5f;

    for (int i = 0; i < MAX_TORPEDOES; ++i) {
        torpedoes_[i].active = false;
        tube_reload_timers_[i] = 0.0f;
    }

    for (int i = 0; i < MAX_SHIPS; ++i) {
        ships_[i].active = false;
    }
    ship_spawn_timer_ = 0.5f;

    // 2-3 drifting sea mines
    mines_[0].x = 3.0f; mines_[0].y = MINE_Y; mines_[0].vx = 1.0f; mines_[0].active = true;
    mines_[1].x = 9.0f; mines_[1].y = MINE_Y; mines_[1].vx = -1.2f; mines_[1].active = true;
    mines_[2].x = 14.0f; mines_[2].y = MINE_Y; mines_[2].vx = 0.8f; mines_[2].active = (patrol_round_ >= 2);
}

int Game128SeaWolf::GetAvailableTubes() const {
    int count = 0;
    for (int i = 0; i < MAX_TORPEDOES; ++i) {
        if (!torpedoes_[i].active && tube_reload_timers_[i] <= 0.0f) {
            count++;
        }
    }
    return count;
}

void Game128SeaWolf::SpawnShip() {
    for (int i = 0; i < MAX_SHIPS; ++i) {
        if (!ships_[i].active) {
            uint8_t type = rand() % 3; // 0: PT Boat, 1: Destroyer, 2: Cargo
            bool from_left = (rand() % 2 == 0);
            ships_[i].type = type;
            ships_[i].y = LANE_Y[type];
            ships_[i].x = from_left ? -2.0f : 17.5f;

            float base_spd = (type == 0) ? 4.5f : ((type == 1) ? 2.8f : 1.6f);
            base_spd += patrol_round_ * 0.2f;
            ships_[i].vx = from_left ? base_spd : -base_spd;
            ships_[i].active = true;
            break;
        }
    }
}

void Game128SeaWolf::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & 0x0030) && !(prev_buttons & 0x0030)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PATROL_CLEAR) {
        if (state_timer_ > 1.8f) {
            patrol_round_++;
            score_ += 1500;
            InitPatrol();
        }
        return;
    }

    // Countdown patrol time
    time_remaining_ -= dt;
    if (time_remaining_ <= 0.0f) {
        time_remaining_ = 0.0f;
        if (ships_sunk_ >= 8) {
            state_ = STATE_PATROL_CLEAR;
            state_timer_ = 0.0f;
        } else {
            state_ = STATE_GAME_OVER;
        }
        return;
    }

    // Controls
    // Button A: Launch Torpedo
    if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) {
        for (int i = 0; i < MAX_TORPEDOES; ++i) {
            if (!torpedoes_[i].active && tube_reload_timers_[i] <= 0.0f) {
                torpedoes_[i].active = true;
                torpedoes_[i].x = periscope_x_;
                torpedoes_[i].y = 13.5f;
                torpedoes_[i].vy = -12.0f;
                tube_reload_timers_[i] = 2.2f; // Reload delay
                break;
            }
        }
    }

    UpdatePeriscope(dt, buttons);
    UpdateTorpedoes(dt);
    UpdateShips(dt);
    UpdateMines(dt);
    CheckCollisions();
}

void Game128SeaWolf::UpdatePeriscope(float dt, uint16_t buttons) {
    float pan_speed = 10.0f;
    if (buttons & 0x0004) periscope_x_ -= pan_speed * dt; // LEFT
    if (buttons & 0x0008) periscope_x_ += pan_speed * dt; // RIGHT

    if (periscope_x_ < 0.5f) periscope_x_ = 0.5f;
    if (periscope_x_ > 15.5f) periscope_x_ = 15.5f;
}

void Game128SeaWolf::UpdateTorpedoes(float dt) {
    for (int i = 0; i < MAX_TORPEDOES; ++i) {
        if (tube_reload_timers_[i] > 0.0f) {
            tube_reload_timers_[i] -= dt;
        }

        if (!torpedoes_[i].active) continue;
        torpedoes_[i].y += torpedoes_[i].vy * dt;

        if (torpedoes_[i].y < 1.5f) {
            // Out of range (passed horizon)
            torpedoes_[i].active = false;
        }
    }
}

void Game128SeaWolf::UpdateShips(float dt) {
    ship_spawn_timer_ -= dt;
    if (ship_spawn_timer_ <= 0.0f) {
        ship_spawn_timer_ = 2.0f - patrol_round_ * 0.1f;
        if (ship_spawn_timer_ < 0.9f) ship_spawn_timer_ = 0.9f;
        SpawnShip();
    }

    for (int i = 0; i < MAX_SHIPS; ++i) {
        if (!ships_[i].active) continue;
        ships_[i].x += ships_[i].vx * dt;

        if (ships_[i].x < -3.0f || ships_[i].x > 18.5f) {
            ships_[i].active = false;
        }
    }
}

void Game128SeaWolf::UpdateMines(float dt) {
    for (int i = 0; i < MAX_MINES; ++i) {
        if (!mines_[i].active) continue;
        mines_[i].x += mines_[i].vx * dt;
        if (mines_[i].x < 0.5f) { mines_[i].x = 0.5f; mines_[i].vx = -mines_[i].vx; }
        if (mines_[i].x > 15.5f) { mines_[i].x = 15.5f; mines_[i].vx = -mines_[i].vx; }
    }
}

void Game128SeaWolf::CheckCollisions() {
    for (int t = 0; t < MAX_TORPEDOES; ++t) {
        if (!torpedoes_[t].active) continue;

        // 1. Torpedo vs Sea Mines
        for (int m = 0; m < MAX_MINES; ++m) {
            if (!mines_[m].active) continue;
            if (std::abs(torpedoes_[t].y - mines_[m].y) < 0.8f &&
                std::abs(torpedoes_[t].x - mines_[m].x) < 0.85f) {
                torpedoes_[t].active = false;
                mines_[m].active = false;
                score_ += 20; // Detonated mine
                break;
            }
        }
        if (!torpedoes_[t].active) continue;

        // 2. Torpedo vs Ships
        for (int s = 0; s < MAX_SHIPS; ++s) {
            if (!ships_[s].active) continue;
            if (std::abs(torpedoes_[t].y - ships_[s].y) < 0.8f) {
                float hit_width = (ships_[s].type == 0) ? 0.9f : 1.4f;
                if (std::abs(torpedoes_[t].x - ships_[s].x) < hit_width) {
                    torpedoes_[t].active = false;
                    ships_[s].active = false;
                    ships_sunk_++;

                    if (ships_[s].type == 0) {
                        score_ += 500;
                        time_remaining_ += 5.0f; // Bonus time extension for fast PT boat!
                    } else if (ships_[s].type == 1) {
                        score_ += 200;
                    } else {
                        score_ += 100;
                    }
                    break;
                }
            }
        }
    }
}

void Game128SeaWolf::Render(uint8_t* fb) {
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

    // 1. Sky & Horizon line at y=1
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 0, 20, 30, 60); // Twilight sky
        set_pixel(x, 1, 40, 70, 110); // Horizon
    }

    // 2. Deep ocean water gradient
    for (int y = 2; y < 15; ++y) {
        uint8_t blue = (uint8_t)(40 + y * 8);
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 10, 25, blue);
        }
    }

    // 3. Ships at Depth Lanes
    for (int i = 0; i < MAX_SHIPS; ++i) {
        if (!ships_[i].active) continue;
        int sx = (int)std::round(ships_[i].x);
        int sy = (int)std::round(ships_[i].y);

        if (ships_[i].type == 0) {
            // PT Boat: fast yellow/orange speedboat
            set_pixel(sx, sy, 255, 220, 40);
            set_pixel(sx - (ships_[i].vx > 0 ? 1 : -1), sy, 255, 120, 20);
        } else if (ships_[i].type == 1) {
            // Destroyer: grey/white warship
            set_pixel(sx, sy, 220, 220, 240);
            set_pixel(sx - 1, sy, 160, 170, 190);
            set_pixel(sx + 1, sy, 160, 170, 190);
            set_pixel(sx, sy - 1, 255, 60, 40); // Radar mast
        } else {
            // Cargo transport: red/brown
            set_pixel(sx, sy, 180, 50, 40);
            set_pixel(sx - 1, sy, 140, 40, 30);
            set_pixel(sx + 1, sy, 140, 40, 30);
            set_pixel(sx + 2, sy, 120, 30, 20);
        }
    }

    // 4. Drifting Sea Mines (Flashing spiked mines)
    for (int i = 0; i < MAX_MINES; ++i) {
        if (!mines_[i].active) continue;
        int mx = (int)std::round(mines_[i].x);
        int my = (int)std::round(mines_[i].y);
        bool flash = ((int)(state_timer_ * 6.0f) % 2) == 0;
        set_pixel(mx, my, flash ? 255 : 180, flash ? 40 : 20, 30);
    }

    // 5. Ascending Torpedoes with Bubble Wake
    for (int i = 0; i < MAX_TORPEDOES; ++i) {
        if (!torpedoes_[i].active) continue;
        int tx = (int)std::round(torpedoes_[i].x);
        int ty = (int)std::round(torpedoes_[i].y);
        set_pixel(tx, ty, 255, 255, 255); // Torpedo warhead
        set_pixel(tx, ty + 1, 100, 220, 255); // Bubble wake
    }

    // 6. Periscope Crosshair (Reticle on row 14)
    int px = (int)std::round(periscope_x_);
    set_pixel(px, 14, 255, 220, 30);     // Center bead
    set_pixel(px - 1, 14, 0, 200, 255);  // Left reticle
    set_pixel(px + 1, 14, 0, 200, 255);  // Right reticle
    set_pixel(px, 13, 0, 200, 255);      // Top reticle

    // 7. Torpedo Tubes on bottom row 15
    for (int i = 0; i < MAX_TORPEDOES; ++i) {
        int x_pos = 2 + i * 3;
        if (!torpedoes_[i].active && tube_reload_timers_[i] <= 0.0f) {
            set_pixel(x_pos, 15, 0, 255, 180); // Ready green/cyan
            set_pixel(x_pos + 1, 15, 0, 255, 180);
        } else {
            set_pixel(x_pos, 15, 120, 30, 20); // Reloading red
            set_pixel(x_pos + 1, 15, 60, 20, 10);
        }
    }
}

} // namespace arcade
