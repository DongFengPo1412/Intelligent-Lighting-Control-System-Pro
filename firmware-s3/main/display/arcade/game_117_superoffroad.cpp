#include "game_117_superoffroad.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr float PI = 3.1415926535f;

Game117SuperOffRoad::Game117SuperOffRoad() {
    Reset();
}

void Game117SuperOffRoad::Init() {
    Reset();
}

void Game117SuperOffRoad::Reset() {
    score_ = 0;
    nitro_charges_ = 3;
    nitro_timer_ = 0.0f;
    InitRace();
}

void Game117SuperOffRoad::InitRace() {
    state_ = STATE_RACING;
    state_timer_ = 0.0f;

    // Player Truck at Starting Grid
    player_.x = 3.0f;
    player_.y = 13.0f;
    player_.angle = 0.0f; // Facing East
    player_.speed = 0.0f;
    player_.jump_z = 0.0f;
    player_.jump_vz = 0.0f;
    player_.is_airborne = false;
    player_.current_waypoint = 0;
    player_.laps_completed = 0;

    // Rival Red Truck
    rival_.x = 2.0f;
    rival_.y = 12.0f;
    rival_.angle = 0.0f;
    rival_.speed = 0.0f;
    rival_.jump_z = 0.0f;
    rival_.jump_vz = 0.0f;
    rival_.is_airborne = false;
    rival_.current_waypoint = 0;
    rival_.laps_completed = 0;

    // Track Collectibles
    items_[0] = {8.0f, 2.0f, 0, true}; // Nitro canister on North straight
    items_[1] = {2.0f, 7.5f, 1, true}; // Cash bag on West straight
    items_[2] = {13.0f, 8.0f, 1, true}; // Cash bag on East turn
}

void Game117SuperOffRoad::ActivateNitro() {
    if (nitro_charges_ <= 0 || state_ != STATE_RACING) return;
    nitro_charges_--;
    player_.speed = 10.5f;
    nitro_timer_ = 1.0f;
}

void Game117SuperOffRoad::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER || state_ == STATE_RACE_FINISHED) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (nitro_timer_ > 0.0f) {
        nitro_timer_ -= dt;
    }

    UpdatePlayerTruck(dt, buttons, prev_buttons);
    UpdateRivalTruck(dt);
    UpdateJumps(player_, dt);
    UpdateJumps(rival_, dt);
    CheckRampsAndMud(player_);
    CheckRampsAndMud(rival_);
    CheckWaypoints(player_, true);
    CheckWaypoints(rival_, false);
    CheckCollisions();
}

void Game117SuperOffRoad::UpdatePlayerTruck(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float rot_speed = 3.8f;
    if (buttons & BTN_LEFT)  player_.angle -= rot_speed * dt;
    if (buttons & BTN_RIGHT) player_.angle += rot_speed * dt;

    if (buttons & BTN_UP) {
        player_.speed += 12.0f * dt;
        float max_spd = (nitro_timer_ > 0.0f) ? 10.5f : 6.2f;
        if (player_.speed > max_spd) player_.speed = max_spd;
    } else if (buttons & BTN_DOWN) {
        player_.speed -= 8.0f * dt;
        if (player_.speed < -2.0f) player_.speed = -2.0f;
    } else {
        // Friction on loose dirt
        player_.speed *= (1.0f - 0.75f * dt);
    }

    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        ActivateNitro();
    }

    // Motion
    player_.x += std::cos(player_.angle) * player_.speed * dt;
    player_.y += std::sin(player_.angle) * player_.speed * dt;

    // Track outer perimeter barrier bounce
    if (player_.x < 1.2f) { player_.x = 1.2f; player_.speed *= -0.3f; }
    if (player_.x > 13.8f) { player_.x = 13.8f; player_.speed *= -0.3f; }
    if (player_.y < 1.2f) { player_.y = 1.2f; player_.speed *= -0.3f; }
    if (player_.y > 13.8f) { player_.y = 13.8f; player_.speed *= -0.3f; }

    // Infield barrier bounce (x in 5..10, y in 5..10)
    if (player_.x >= 5.0f && player_.x <= 10.0f && player_.y >= 5.0f && player_.y <= 10.0f) {
        // Push out to closest side
        float d_left = player_.x - 5.0f;
        float d_right = 10.0f - player_.x;
        float d_top = player_.y - 5.0f;
        float d_bottom = 10.0f - player_.y;
        float min_d = std::min({d_left, d_right, d_top, d_bottom});
        if (min_d == d_left) player_.x = 4.8f;
        else if (min_d == d_right) player_.x = 10.2f;
        else if (min_d == d_top) player_.y = 4.8f;
        else player_.y = 10.2f;
        player_.speed *= -0.3f;
    }
}

void Game117SuperOffRoad::UpdateRivalTruck(float dt) {
    float tx = waypoints_[rival_.current_waypoint][0];
    float ty = waypoints_[rival_.current_waypoint][1];

    float dx = tx - rival_.x;
    float dy = ty - rival_.y;
    float target_angle = std::atan2(dy, dx);

    // Turn towards waypoint
    float angle_diff = target_angle - rival_.angle;
    while (angle_diff > PI) angle_diff -= 2.0f * PI;
    while (angle_diff < -PI) angle_diff += 2.0f * PI;

    rival_.angle += angle_diff * 4.0f * dt;
    rival_.speed = 4.6f;

    rival_.x += std::cos(rival_.angle) * rival_.speed * dt;
    rival_.y += std::sin(rival_.angle) * rival_.speed * dt;
}

void Game117SuperOffRoad::UpdateJumps(Truck& t, float dt) {
    if (t.is_airborne) {
        t.jump_vz -= 14.0f * dt; // Gravity
        t.jump_z += t.jump_vz * dt;
        if (t.jump_z <= 0.0f) {
            t.jump_z = 0.0f;
            t.jump_vz = 0.0f;
            t.is_airborne = false;
        }
    }
}

void Game117SuperOffRoad::CheckRampsAndMud(Truck& t) {
    if (t.is_airborne) return;

    // Ramp 1 on South straight at (8.0, 13.0)
    if (std::abs(t.x - 8.0f) < 0.9f && std::abs(t.y - 13.0f) < 0.9f && t.speed > 2.0f) {
        t.is_airborne = true;
        t.jump_vz = 5.0f;
        t.jump_z = 0.2f;
    }

    // Ramp 2 on East turn at (13.0, 7.5)
    if (std::abs(t.x - 13.0f) < 0.9f && std::abs(t.y - 7.5f) < 0.9f && t.speed > 2.0f) {
        t.is_airborne = true;
        t.jump_vz = 5.0f;
        t.jump_z = 0.2f;
    }
}

void Game117SuperOffRoad::CheckWaypoints(Truck& t, bool is_player) {
    float wx = waypoints_[t.current_waypoint][0];
    float wy = waypoints_[t.current_waypoint][1];

    float dx = t.x - wx;
    float dy = t.y - wy;
    float dist = std::sqrt(dx * dx + dy * dy);

    if (dist < 2.5f) {
        if (t.current_waypoint == NUM_WAYPOINTS - 1) {
            // Crossed finish line!
            t.laps_completed++;
            t.current_waypoint = 0;
            if (is_player) {
                score_ += 300;
                if (t.laps_completed >= TOTAL_LAPS) {
                    state_ = STATE_RACE_FINISHED;
                    score_ += 1000; // 1st Place Trophy Bonus
                }
            }
        } else {
            t.current_waypoint++;
        }
    }
}

void Game117SuperOffRoad::CheckCollisions() {
    // Collectibles collection by player
    for (int i = 0; i < MAX_ITEMS; ++i) {
        if (!items_[i].active) continue;
        float dx = std::abs(player_.x - items_[i].x);
        float dy = std::abs(player_.y - items_[i].y);
        if (dx < 1.0f && dy < 1.0f) {
            items_[i].active = false;
            if (items_[i].type == 0) {
                nitro_charges_++;
                score_ += 50;
            } else {
                score_ += 200; // Cash bag
            }
        }
    }
}

void Game117SuperOffRoad::Render(uint8_t* fb) {
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

    // 1. Stadium Mud Circuit Track (Earthy clay orange & mud brown)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            // Concrete outer perimeter barrier
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                set_pixel(x, y, 100, 100, 110);
            }
            // Infield Lake/Grass Barrier
            else if (x >= 5 && x <= 10 && y >= 5 && y <= 10) {
                set_pixel(x, y, 40, 120, 50); // Infield green
            }
            // Dirt race track
            else {
                uint8_t dirt = ((x + y) % 2 == 0) ? 180 : 160;
                set_pixel(x, y, dirt, dirt - 50, 40);
            }
        }
    }

    // Finish line checkers on South straight at x=2..4, y=13
    set_pixel(3, 12, 255, 255, 255);
    set_pixel(3, 13, 30, 30, 30);
    set_pixel(3, 14, 255, 255, 255);

    // Mud Jump Ramps (Highlighted mounds in golden clay)
    set_pixel(8, 13, 230, 140, 20);
    set_pixel(8, 12, 210, 120, 20);
    set_pixel(13, 7, 230, 140, 20);
    set_pixel(14, 7, 210, 120, 20);

    // 2. Collectibles (Nitro canisters & Cash bags)
    for (int i = 0; i < MAX_ITEMS; ++i) {
        if (!items_[i].active) continue;
        int ix = static_cast<int>(std::round(items_[i].x));
        int iy = static_cast<int>(std::round(items_[i].y));
        if (items_[i].type == 0) {
            set_pixel(ix, iy, 40, 200, 255); // Cyan Nitro can
        } else {
            set_pixel(ix, iy, 255, 220, 0); // Yellow Cash bag
        }
    }

    // 3. Rival Red Truck
    int rx = static_cast<int>(std::round(rival_.x));
    int ry = static_cast<int>(std::round(rival_.y));
    set_pixel(rx, ry, 255, 40, 30); // Red truck cabin

    // 4. Player Truck (White & Blue monster truck)
    int px = static_cast<int>(std::round(player_.x));
    int py = static_cast<int>(std::round(player_.y));

    if (player_.is_airborne) {
        // Shadow on ground
        set_pixel(px, py, 60, 40, 20);
        // Elevated truck
        int elevated_y = std::max(1, py - static_cast<int>(player_.jump_z * 2.0f));
        set_pixel(px, elevated_y, 255, 255, 255); // White roof
        set_pixel(px, elevated_y + 1, 40, 120, 255); // Blue chassis
    } else {
        set_pixel(px, py, 255, 255, 255); // White roof
        int nose_x = px + static_cast<int>(std::round(std::cos(player_.angle)));
        int nose_y = py + static_cast<int>(std::round(std::sin(player_.angle)));
        set_pixel(nose_x, nose_y, 40, 140, 255); // Blue hood

        // Nitro turbo booster trail
        if (nitro_timer_ > 0.0f) {
            int tail_x = px - static_cast<int>(std::round(std::cos(player_.angle)));
            int tail_y = py - static_cast<int>(std::round(std::sin(player_.angle)));
            set_pixel(tail_x, tail_y, 255, 140, 0); // Flaming nitro boost
        }
    }

    // 5. HUD: Nitro Charges (cyan dots top-left) and Laps (green dots top-right)
    for (int n = 0; n < std::min(nitro_charges_, 5); ++n) {
        set_pixel(1 + n, 0, 0, 240, 255);
    }
    for (int l = 0; l < player_.laps_completed; ++l) {
        set_pixel(14 - l, 0, 40, 255, 80);
    }
}

} // namespace arcade
