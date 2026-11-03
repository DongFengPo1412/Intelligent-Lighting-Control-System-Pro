#include "game_127_choplifter.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace arcade {

static constexpr float GROUND_Y = 13.8f;
static constexpr float BASE_MAX_X = 3.2f;

Game127Choplifter::Game127Choplifter() {
    Init();
}

void Game127Choplifter::Init() {
    score_ = 0;
    lives_ = 3;
    mission_ = 1;
    InitMission();
}

void Game127Choplifter::Reset() {
    Init();
}

void Game127Choplifter::InitMission() {
    state_ = STATE_FLYING;
    state_timer_ = 0.0f;

    hx_ = 1.5f;
    hy_ = 13.8f;
    hvx_ = 0.0f;
    hvy_ = 0.0f;
    facing_ = FACING_RIGHT;
    is_landed_ = true;

    onboard_count_ = 0;
    rescued_count_ = 0;
    kia_count_ = 0;

    barracks_broken_ = false;
    barracks_hp_ = 3.0f;

    for (int i = 0; i < MAX_HOSTAGES; ++i) {
        hostages_[i].x = 10.5f;
        hostages_[i].y = GROUND_Y;
        hostages_[i].state = 0; // In Barracks
    }

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    for (int i = 0; i < MAX_ENEMY_JETS; ++i) {
        jets_[i].active = false;
    }
    jet_spawn_timer_ = 3.0f;

    tank_x_ = 8.0f;
    tank_vx_ = 1.2f;
    tank_alive_ = true;
}

void Game127Choplifter::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & 0x0030) && !(prev_buttons & 0x0030)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_CHOPPER_DOWN) {
        if (state_timer_ > 1.5f) {
            lives_--;
            if (lives_ == 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_FLYING;
                hx_ = 1.5f;
                hy_ = 13.8f;
                hvx_ = 0.0f;
                hvy_ = 0.0f;
                facing_ = FACING_RIGHT;
                is_landed_ = true;
                onboard_count_ = 0;
            }
        }
        return;
    }

    if (state_ == STATE_MISSION_CLEAR) {
        if (state_timer_ > 1.8f) {
            mission_++;
            score_ += 2000;
            InitMission();
        }
        return;
    }

    UpdateChopper(dt, buttons, prev_buttons);
    UpdateHostages(dt);
    UpdateBullets(dt);
    UpdateEnemies(dt);
    CheckCollisions();

    // Check mission completion
    if (rescued_count_ + kia_count_ >= MAX_HOSTAGES && onboard_count_ == 0) {
        if (rescued_count_ >= 8) {
            state_ = STATE_MISSION_CLEAR;
            state_timer_ = 0.0f;
        } else {
            state_ = STATE_GAME_OVER;
        }
    }
}

void Game127Choplifter::UpdateChopper(float dt, uint16_t buttons, uint16_t prev_buttons) {
    // Button B: Cycle orientation
    if ((buttons & 0x0020) && !(prev_buttons & 0x0020)) {
        if (facing_ == FACING_LEFT) facing_ = FACING_FORWARD;
        else if (facing_ == FACING_FORWARD) facing_ = FACING_RIGHT;
        else facing_ = FACING_LEFT;
    }

    // Button A: Fire weapon
    if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) {
        for (int i = 0; i < MAX_BULLETS; ++i) {
            if (!bullets_[i].active) {
                bullets_[i].active = true;
                bullets_[i].x = hx_;
                bullets_[i].y = hy_;
                if (facing_ == FACING_LEFT) {
                    bullets_[i].vx = -14.0f;
                    bullets_[i].vy = 0.0f;
                    bullets_[i].is_bomb = false;
                } else if (facing_ == FACING_RIGHT) {
                    bullets_[i].vx = 14.0f;
                    bullets_[i].vy = 0.0f;
                    bullets_[i].is_bomb = false;
                } else { // FACING_FORWARD -> Bomb
                    bullets_[i].vx = hvx_ * 0.4f;
                    bullets_[i].vy = 10.0f;
                    bullets_[i].is_bomb = true;
                }
                break;
            }
        }
    }

    // Flight controls
    float lift_accel = 12.0f;
    float grav = 6.0f;

    if (buttons & 0x0001) { // UP: Collective climb
        hvy_ -= lift_accel * dt;
        is_landed_ = false;
    } else {
        hvy_ += grav * dt; // Gravity
    }

    if (buttons & 0x0002) { // DOWN: Descend faster
        hvy_ += lift_accel * 0.5f * dt;
    }

    float lateral_thrust = 9.0f;
    if (buttons & 0x0004) { // LEFT
        hvx_ -= lateral_thrust * dt;
        is_landed_ = false;
    }
    if (buttons & 0x0008) { // RIGHT
        hvx_ += lateral_thrust * dt;
        is_landed_ = false;
    }

    // Air drag
    hvx_ *= 0.94f;
    hvy_ *= 0.94f;

    hx_ += hvx_ * dt;
    hy_ += hvy_ * dt;

    // Boundaries
    if (hx_ < 0.5f) { hx_ = 0.5f; hvx_ = 0.0f; }
    if (hx_ > 15.0f) { hx_ = 15.0f; hvx_ = 0.0f; }
    if (hy_ < 1.0f) { hy_ = 1.0f; hvy_ = 0.0f; }

    // Ground Touchdown
    if (hy_ >= GROUND_Y) {
        hy_ = GROUND_Y;
        if (std::abs(hvy_) > 4.5f || std::abs(hvx_) > 3.0f) {
            // Rough hard crash!
            state_ = STATE_CHOPPER_DOWN;
            state_timer_ = 0.0f;
        } else {
            hvy_ = 0.0f;
            hvx_ = 0.0f;
            is_landed_ = true;

            // If landed at base camp, unload passengers!
            if (hx_ <= BASE_MAX_X && onboard_count_ > 0) {
                rescued_count_ += onboard_count_;
                score_ += (uint32_t)onboard_count_ * 500;
                onboard_count_ = 0;
            }
        }
    }
}

void Game127Choplifter::UpdateHostages(float dt) {
    for (int i = 0; i < MAX_HOSTAGES; ++i) {
        if (hostages_[i].state == 1) { // Running
            // Run toward landed helicopter if landed, otherwise run towards base
            float target_x = is_landed_ ? hx_ : 1.5f;
            float run_spd = 2.0f;
            if (hostages_[i].x < target_x - 0.2f) hostages_[i].x += run_spd * dt;
            else if (hostages_[i].x > target_x + 0.2f) hostages_[i].x -= run_spd * dt;

            // Boarding chopper
            if (is_landed_ && std::abs(hostages_[i].x - hx_) < 0.6f && onboard_count_ < MAX_ONBOARD) {
                hostages_[i].state = 2; // Onboard
                onboard_count_++;
            }
        }
    }
}

void Game127Choplifter::UpdateBullets(float dt) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        bullets_[i].x += bullets_[i].vx * dt;
        bullets_[i].y += bullets_[i].vy * dt;

        if (bullets_[i].is_bomb) {
            bullets_[i].vy += 4.0f * dt; // Bomb gravity
        }

        if (bullets_[i].x < 0.0f || bullets_[i].x > 15.5f ||
            bullets_[i].y < 0.5f || bullets_[i].y > GROUND_Y) {
            bullets_[i].active = false;
        }
    }
}

void Game127Choplifter::UpdateEnemies(float dt) {
    // Enemy Tank
    if (tank_alive_) {
        tank_x_ += tank_vx_ * dt;
        if (tank_x_ < 5.0f) { tank_x_ = 5.0f; tank_vx_ = -tank_vx_; }
        if (tank_x_ > 14.5f) { tank_x_ = 14.5f; tank_vx_ = -tank_vx_; }
    }

    // Enemy Jet spawn
    jet_spawn_timer_ -= dt;
    if (jet_spawn_timer_ <= 0.0f) {
        jet_spawn_timer_ = 4.0f - mission_ * 0.2f;
        for (int i = 0; i < MAX_ENEMY_JETS; ++i) {
            if (!jets_[i].active) {
                jets_[i].active = true;
                jets_[i].x = 15.5f;
                jets_[i].y = 2.5f + (rand() % 3);
                jets_[i].vx = -(6.0f + mission_ * 0.5f);
                break;
            }
        }
    }

    // Jet update
    for (int i = 0; i < MAX_ENEMY_JETS; ++i) {
        if (!jets_[i].active) continue;
        jets_[i].x += jets_[i].vx * dt;
        if (jets_[i].x < -1.0f) {
            jets_[i].active = false;
        }
    }
}

void Game127Choplifter::CheckCollisions() {
    // 1. Bullets vs Barracks
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;

        // Barracks hit
        if (!barracks_broken_ && bullets_[b].x >= 9.0f && bullets_[b].x <= 12.0f && bullets_[b].y >= 12.0f) {
            bullets_[b].active = false;
            barracks_hp_ -= 1.0f;
            if (barracks_hp_ <= 0.0f) {
                barracks_broken_ = true;
                score_ += 300;
                // Free hostages
                for (int h = 0; h < MAX_HOSTAGES; ++h) {
                    if (hostages_[h].state == 0) {
                        hostages_[h].state = 1; // Start running
                        hostages_[h].x = 9.5f + (h % 3) * 0.8f;
                    }
                }
            }
            continue;
        }

        // Tank hit
        if (tank_alive_ && std::abs(bullets_[b].x - tank_x_) < 1.0f && bullets_[b].y >= 13.0f) {
            bullets_[b].active = false;
            tank_alive_ = false;
            score_ += 400;
            continue;
        }

        // Jet hit
        for (int j = 0; j < MAX_ENEMY_JETS; ++j) {
            if (!jets_[j].active) continue;
            if (std::abs(bullets_[b].x - jets_[j].x) < 0.9f && std::abs(bullets_[b].y - jets_[j].y) < 0.9f) {
                bullets_[b].active = false;
                jets_[j].active = false;
                score_ += 250;
                break;
            }
        }
    }

    // 2. Chopper vs Enemies
    // vs Tank
    if (tank_alive_ && std::abs(hx_ - tank_x_) < 0.9f && hy_ >= 13.0f) {
        state_ = STATE_CHOPPER_DOWN;
        state_timer_ = 0.0f;
    }

    // vs Jets
    for (int j = 0; j < MAX_ENEMY_JETS; ++j) {
        if (!jets_[j].active) continue;
        if (std::abs(hx_ - jets_[j].x) < 0.9f && std::abs(hy_ - jets_[j].y) < 0.9f) {
            state_ = STATE_CHOPPER_DOWN;
            state_timer_ = 0.0f;
            break;
        }
    }
}

void Game127Choplifter::Render(uint8_t* fb) {
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

    // 1. Sky & Ground
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 15, 120, 80, 30); // Dirt ground
        set_pixel(x, 14, 80, 140, 40); // Grass/sand edge
    }

    // 2. Friendly Base Camp Bunker (x in [0, 3])
    set_pixel(0, 13, 0, 180, 255);
    set_pixel(1, 13, 0, 220, 255);
    set_pixel(2, 13, 0, 180, 255);
    // Rescue flag
    set_pixel(1, 12, 255, 255, 255);
    set_pixel(1, 11, 255, 30, 20);

    // 3. Enemy Prison Barracks (x in [9, 12])
    if (!barracks_broken_) {
        for (int bx = 9; bx <= 12; ++bx) {
            set_pixel(bx, 13, 160, 50, 40); // Brick prison building
            set_pixel(bx, 12, 120, 30, 20);
        }
    } else {
        // Destroyed broken barracks
        set_pixel(9, 13, 100, 40, 20);
        set_pixel(12, 13, 100, 40, 20);
    }

    // 4. Hostages running on ground
    for (int h = 0; h < MAX_HOSTAGES; ++h) {
        if (hostages_[h].state == 1) { // Running
            int hx = (int)std::round(hostages_[h].x);
            set_pixel(hx, 14, 255, 240, 160); // Civilian avatar
            set_pixel(hx, 13, 255, 255, 255); // Waving arms
        }
    }

    // 5. Enemy Tank
    if (tank_alive_) {
        int tx = (int)std::round(tank_x_);
        set_pixel(tx, 14, 200, 40, 30);
        set_pixel(tx, 13, 160, 20, 20);
    }

    // 6. Enemy Jet
    for (int j = 0; j < MAX_ENEMY_JETS; ++j) {
        if (!jets_[j].active) continue;
        int jx = (int)std::round(jets_[j].x);
        int jy = (int)std::round(jets_[j].y);
        set_pixel(jx, jy, 255, 60, 40);
        set_pixel(jx + 1, jy, 255, 180, 0);
    }

    // 7. Bullets / Bombs
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;
        int bx = (int)std::round(bullets_[b].x);
        int by = (int)std::round(bullets_[b].y);
        if (bullets_[b].is_bomb) {
            set_pixel(bx, by, 255, 200, 30);
        } else {
            set_pixel(bx, by, 80, 255, 255);
        }
    }

    // 8. Helicopter
    int chx = (int)std::round(hx_);
    int chy = (int)std::round(hy_);

    if (state_ == STATE_FLYING || state_ == STATE_MISSION_CLEAR) {
        // Rotor blades
        bool blade_phase = ((int)(state_timer_ * 20.0f) % 2) == 0;
        if (blade_phase) {
            set_pixel(chx - 1, chy - 1, 220, 220, 240);
            set_pixel(chx + 1, chy - 1, 220, 220, 240);
        } else {
            set_pixel(chx, chy - 1, 255, 255, 255);
        }

        // Fuselage
        set_pixel(chx, chy, 40, 220, 100); // Olive / rescue green
        if (facing_ == FACING_LEFT) {
            set_pixel(chx - 1, chy, 255, 255, 255); // Cockpit nose left
            set_pixel(chx + 1, chy, 40, 160, 70);   // Tail rotor right
        } else if (facing_ == FACING_RIGHT) {
            set_pixel(chx + 1, chy, 255, 255, 255); // Cockpit nose right
            set_pixel(chx - 1, chy, 40, 160, 70);   // Tail rotor left
        } else { // Facing forward
            set_pixel(chx, chy, 255, 255, 255);     // Glass canopy
            set_pixel(chx - 1, chy, 40, 200, 80);
            set_pixel(chx + 1, chy, 40, 200, 80);
        }
    } else if (state_ == STATE_CHOPPER_DOWN) {
        set_pixel(chx, chy, 255, 200, 40);
        set_pixel(chx - 1, chy, 255, 40, 20);
        set_pixel(chx + 1, chy, 255, 40, 20);
        set_pixel(chx, chy - 1, 255, 120, 0);
    }

    // 9. HUD / Passengers Onboard & Rescued
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l * 2, 0, 40, 220, 100);
    }
    // Passengers onboard pips
    for (int ob = 0; ob < onboard_count_ && ob < 8; ++ob) {
        set_pixel(7 + ob, 0, 255, 240, 160);
    }
}

} // namespace arcade
