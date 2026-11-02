#include "game_048_elevator_action.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

static const int FLOOR_Y[Game048ElevatorAction::NUM_FLOORS] = {3, 7, 11, 15};

Game048ElevatorAction::Game048ElevatorAction()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      lives_(3),
      docs_collected_(0),
      player_x_(2.0f),
      player_y_(3.0f),
      player_vx_(0.0f),
      player_facing_(1),
      is_crouching_(false),
      in_elevator_(false),
      elevator_y_(3.0f),
      elevator_vy_(0.0f),
      blackout_timer_(0.0f) {
}

void Game048ElevatorAction::Init() {
    Reset();
}

void Game048ElevatorAction::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    docs_collected_ = 0;
    player_x_ = 2.0f;
    player_y_ = 3.0f;
    player_vx_ = 0.0f;
    player_facing_ = 1;
    is_crouching_ = false;
    in_elevator_ = false;
    elevator_y_ = 3.0f;
    elevator_vy_ = 0.0f;
    blackout_timer_ = 0.0f;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    InitBuilding();
}

void Game048ElevatorAction::InitBuilding() {
    // 2 Red Secret Doors
    red_doors_[0] = {1, 3, false};  // Floor 1, col 3
    red_doors_[1] = {2, 12, false}; // Floor 2, col 12

    // Overhead Lights on ceilings
    for (int f = 0; f < NUM_FLOORS; ++f) {
        lights_[f] = {f, (f % 2 == 0) ? 4 : 11, true};
    }

    // 3 Enemy Spies
    enemies_[0] = {12.0f, 0, -2.5f, true, 1.2f};
    enemies_[1] = {13.0f, 1, -2.5f, true, 1.8f};
    enemies_[2] = {4.0f, 2, 2.5f, true, 1.5f};
}

int Game048ElevatorAction::GetDocumentsRemaining() const {
    return NUM_RED_DOORS - docs_collected_;
}

void Game048ElevatorAction::FirePistol(bool is_player, float x, float y, float dir) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].x = x;
            bullets_[i].y = y;
            bullets_[i].vx = dir * 14.0f;
            bullets_[i].is_player = is_player;
            bullets_[i].active = true;
            break;
        }
    }
}

void Game048ElevatorAction::UpdateElevator(float dt, uint32_t buttons) {
    const float elevator_speed = 4.2f;

    elevator_vy_ = 0.0f;
    if (in_elevator_) {
        if (buttons & KEY_UP)   elevator_vy_ = -elevator_speed;
        if (buttons & KEY_DOWN) elevator_vy_ = elevator_speed;
    }

    elevator_y_ += elevator_vy_ * dt;
    elevator_y_ = std::max(3.0f, std::min(15.0f, elevator_y_));

    if (in_elevator_) {
        player_y_ = elevator_y_;
    }
}

void Game048ElevatorAction::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    const float walk_speed = 5.5f;

    // Check if in elevator shaft
    if (player_x_ >= 6.5f && player_x_ <= 8.5f && fabsf(player_y_ - elevator_y_) <= 0.85f) {
        in_elevator_ = true;
    } else {
        in_elevator_ = false;
    }

    // Crouch (KEY_DOWN when on solid floor outside elevator)
    if (!in_elevator_ && (buttons & KEY_DOWN)) {
        is_crouching_ = true;
        player_vx_ = 0.0f;
    } else {
        is_crouching_ = false;
        // Horizontal walk
        player_vx_ = 0.0f;
        if (buttons & KEY_LEFT) {
            player_vx_ = -walk_speed;
            player_facing_ = -1;
        }
        if (buttons & KEY_RIGHT) {
            player_vx_ = walk_speed;
            player_facing_ = 1;
        }
    }

    player_x_ += player_vx_ * dt;
    player_x_ = std::max(0.5f, std::min(15.0f, player_x_));

    // Solid floor snapping when outside elevator
    if (!in_elevator_) {
        // Find nearest floor
        int nearest_f = 0;
        float min_dist = 999.0f;
        for (int f = 0; f < NUM_FLOORS; ++f) {
            float d = fabsf(player_y_ - static_cast<float>(FLOOR_Y[f]));
            if (d < min_dist) {
                min_dist = d;
                nearest_f = f;
            }
        }
        player_y_ = static_cast<float>(FLOOR_Y[nearest_f]);
    }

    // Shoot Pistol (KEY_B)
    if ((buttons & KEY_B) && !(prev_buttons & KEY_B)) {
        float shoot_y = is_crouching_ ? (player_y_ + 0.3f) : (player_y_ - 0.2f);
        FirePistol(true, player_x_ + player_facing_ * 0.8f, shoot_y, static_cast<float>(player_facing_));
    }

    // Red Secret Door Collection
    for (int r = 0; r < NUM_RED_DOORS; ++r) {
        if (!red_doors_[r].collected) {
            float door_y = static_cast<float>(FLOOR_Y[red_doors_[r].floor]);
            if (fabsf(player_y_ - door_y) <= 0.5f && fabsf(player_x_ - static_cast<float>(red_doors_[r].col)) <= 0.8f) {
                red_doors_[r].collected = true;
                docs_collected_++;
                score_ += 200;
                if (score_ > high_score_) high_score_ = score_;
            }
        }
    }

    // Victory Check: All docs collected and reached getaway car on Floor 3 (y=15, x <= 3.0)
    if (docs_collected_ >= NUM_RED_DOORS && player_y_ >= 14.5f && player_x_ <= 3.0f) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 1000;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game048ElevatorAction::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (blackout_timer_ > 0.0f) {
            continue; // Enemies stunned in dark
        }

        enemies_[i].x += enemies_[i].vx * dt;

        // Bounce horizontally outside elevator shaft
        if (enemies_[i].x < 1.0f) {
            enemies_[i].x = 1.0f;
            enemies_[i].vx = -enemies_[i].vx;
        } else if (enemies_[i].x > 15.0f) {
            enemies_[i].x = 15.0f;
            enemies_[i].vx = -enemies_[i].vx;
        }

        // Enemy shooting
        enemies_[i].shoot_timer -= dt;
        if (enemies_[i].shoot_timer <= 0.0f) {
            enemies_[i].shoot_timer = 2.2f;
            float ey = static_cast<float>(FLOOR_Y[enemies_[i].floor]);
            float dir = (player_x_ > enemies_[i].x) ? 1.0f : -1.0f;
            FirePistol(false, enemies_[i].x + dir * 0.8f, ey - 0.2f, dir);
        }
    }
}

void Game048ElevatorAction::UpdateBullets(float dt) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        bullets_[i].x += bullets_[i].vx * dt;
        if (bullets_[i].x < 0.0f || bullets_[i].x > 16.0f) {
            bullets_[i].active = false;
        }
    }
}

void Game048ElevatorAction::CheckCollisions() {
    // 1. Bullets vs Lights (Ceiling blackout)
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active || !bullets_[b].is_player) continue;

        for (int f = 0; f < NUM_FLOORS; ++f) {
            if (!lights_[f].active) continue;

            float ly = static_cast<float>(FLOOR_Y[f] - 2);
            if (fabsf(bullets_[b].x - static_cast<float>(lights_[f].col)) <= 0.85f &&
                fabsf(bullets_[b].y - ly) <= 1.0f) {
                bullets_[b].active = false;
                lights_[f].active = false;
                blackout_timer_ = 3.5f;
                score_ += 100;
                if (score_ > high_score_) high_score_ = score_;
                break;
            }
        }
    }

    // 2. Player Bullets vs Enemies
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active || !bullets_[b].is_player) continue;

        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;

            float ey = static_cast<float>(FLOOR_Y[enemies_[e].floor]);
            if (fabsf(bullets_[b].x - enemies_[e].x) <= 0.82f &&
                fabsf(bullets_[b].y - ey) <= 0.7f) {
                bullets_[b].active = false;
                enemies_[e].active = false;
                score_ += 100;
                if (score_ > high_score_) high_score_ = score_;
                break;
            }
        }
    }

    // 3. Enemy Bullets vs Player (Can duck under high bullets)
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active || bullets_[b].is_player) continue;

        if (fabsf(bullets_[b].x - player_x_) <= 0.75f &&
            fabsf(bullets_[b].y - player_y_) <= 0.65f) {
            // If crouching, bullets pass over head!
            if (!is_crouching_) {
                bullets_[b].active = false;
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }

    // 4. Elevator Crush Mechanic!
    if (elevator_vy_ > 0.0f) { // Moving down
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;

            // In shaft and directly below descending elevator
            if (enemies_[e].x >= 6.5f && enemies_[e].x <= 8.5f) {
                float ey = static_cast<float>(FLOOR_Y[enemies_[e].floor]);
                if (ey > elevator_y_ && ey <= elevator_y_ + 1.2f) {
                    enemies_[e].active = false;
                    score_ += 150; // Elevator crush bonus!
                    if (score_ > high_score_) high_score_ = score_;
                }
            }
        }
    }
}

void Game048ElevatorAction::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;
    if (blackout_timer_ > 0.0f) blackout_timer_ -= dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DEAD) {
        if (state_timer_ >= 1.5f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                player_x_ = 2.0f;
                player_y_ = 3.0f;
                elevator_y_ = 3.0f;
                in_elevator_ = false;
            }
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ >= 2.5f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateElevator(dt, buttons);
    UpdateEnemies(dt);
    UpdateBullets(dt);
    CheckCollisions();
}

void Game048ElevatorAction::Render(uint8_t* fb) {
    // 1. Skyscraper Interior (#1C2833)
    uint8_t bg_val = (blackout_timer_ > 0.0f) ? 2 : 15;
    for (int i = 0; i < 256 * 3; ++i) {
        fb[i] = bg_val;
    }

    // 2. Render 4 Floors
    for (int f = 0; f < NUM_FLOORS; ++f) {
        int y = FLOOR_Y[f];
        for (int x = 0; x < 16; ++x) {
            // Leave opening for elevator shaft at cols 7..8
            if (x == 7 || x == 8) continue;

            int idx = (y * 16 + x) * 3;
            fb[idx + 0] = 86;  fb[idx + 1] = 101; fb[idx + 2] = 115; // Steel Floor
        }
    }

    // 3. Render Red Secret Doors
    for (int r = 0; r < NUM_RED_DOORS; ++r) {
        if (!red_doors_[r].collected) {
            int rx = red_doors_[r].col;
            int ry = FLOOR_Y[red_doors_[r].floor] - 1;
            int idx = (ry * 16 + rx) * 3;
            fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Crimson Door
        }
    }

    // 4. Render Overhead Lights
    for (int f = 0; f < NUM_FLOORS; ++f) {
        if (lights_[f].active) {
            int lx = lights_[f].col;
            int ly = FLOOR_Y[f] - 2;
            if (ly >= 0) {
                int idx = (ly * 16 + lx) * 3;
                fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15; // Golden Lamp
            }
        }
    }

    // 5. Render Elevator Cabin in Shaft (cols 7..8)
    int ey = static_cast<int>(std::round(elevator_y_));
    for (int x = 7; x <= 8; ++x) {
        if (ey >= 0 && ey < 16) {
            int idx = (ey * 16 + x) * 3;
            fb[idx + 0] = 52; fb[idx + 1] = 152; fb[idx + 2] = 219; // Cyan Elevator
        }
    }

    // 6. Render Enemies (Enemy Spies in Fedora Purple)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = FLOOR_Y[enemies_[i].floor] - 1;
        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            fb[idx + 0] = 142; fb[idx + 1] = 68; fb[idx + 2] = 173;
        }
    }

    // 7. Render Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        int bx = static_cast<int>(std::round(bullets_[i].x));
        int by = static_cast<int>(std::round(bullets_[i].y));
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255;
        }
    }

    // 8. Render Player Agent Otto (Emerald Green Trenchcoat)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_)) - 1;
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx + 0] = 39; fb[idx + 1] = 174; fb[idx + 2] = 96;
    }

    // 9. Getaway Car on Floor 3 (cols 1..2)
    int car_idx1 = (14 * 16 + 1) * 3;
    int car_idx2 = (14 * 16 + 2) * 3;
    fb[car_idx1 + 0] = 230; fb[car_idx1 + 1] = 126; fb[car_idx1 + 2] = 34; // Orange Car
    fb[car_idx2 + 0] = 230; fb[car_idx2 + 1] = 126; fb[car_idx2 + 2] = 34;
}

} // namespace arcade
