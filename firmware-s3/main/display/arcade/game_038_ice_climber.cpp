#include "game_038_ice_climber.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

static const int FLOOR_Y[4] = {14, 11, 8, 5};

Game038IceClimber::Game038IceClimber()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      lives_(3),
      player_x_(7.0f),
      player_y_(13.0f),
      player_vx_(0.0f),
      player_vy_(0.0f),
      is_grounded_(true),
      hammer_timer_(0.0f) {
}

void Game038IceClimber::Init() {
    Reset();
}

void Game038IceClimber::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    player_x_ = 7.0f;
    player_y_ = 13.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;
    is_grounded_ = true;
    hammer_timer_ = 0.0f;

    InitMountain();

    // Condor
    condor_.x = -2.0f;
    condor_.y = 1.0f;
    condor_.vx = 3.5f;
    condor_.active = true;

    // 2 Topis (Seals) patrolling Floor 1 and Floor 2
    topis_[0].x = 3.0f;
    topis_[0].floor_y = 11;
    topis_[0].vx = 2.2f;
    topis_[0].active = true;

    topis_[1].x = 12.0f;
    topis_[1].floor_y = 8;
    topis_[1].vx = -2.2f;
    topis_[1].active = true;
}

void Game038IceClimber::InitMountain() {
    // Clear
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            ice_grid_[y][x] = 0;
        }
    }

    // Floor 0: Ground (Solid base 1)
    for (int x = 0; x < 16; ++x) {
        ice_grid_[14][x] = 1;
        ice_grid_[15][x] = 1;
    }

    // Floor 1, 2, 3: Breakable Ice Blocks (2)
    for (int f = 1; f < 4; ++f) {
        int fy = FLOOR_Y[f];
        for (int x = 1; x < 15; ++x) {
            ice_grid_[fy][x] = 2;
        }
    }

    // Summit platform (Solid ice at y = 2, x = 6..9)
    for (int x = 6; x <= 9; ++x) {
        ice_grid_[2][x] = 1;
    }
}

int Game038IceClimber::GetCurrentFloor() const {
    if (player_y_ <= 2.0f) return 4; // Summit
    if (player_y_ <= 5.0f) return 3;
    if (player_y_ <= 8.0f) return 2;
    if (player_y_ <= 11.0f) return 1;
    return 0; // Ground
}

bool Game038IceClimber::IsIceBlock(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return false;
    return ice_grid_[y][x] != 0;
}

void Game038IceClimber::BreakIceAt(int x, int y) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        if (ice_grid_[y][x] == 2) {
            ice_grid_[y][x] = 0; // Broken!
            score_ += 50;
            if (score_ > high_score_) high_score_ = score_;
        }
    }
}

void Game038IceClimber::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    const float gravity = 22.0f;
    const float run_speed = 5.5f;

    // 1. Horizontal Motion
    player_vx_ = 0.0f;
    if (buttons & KEY_LEFT)  player_vx_ = -run_speed;
    if (buttons & KEY_RIGHT) player_vx_ = run_speed;

    player_x_ += player_vx_ * dt;
    // Screen wrap
    if (player_x_ < 0.0f)  player_x_ += 16.0f;
    if (player_x_ >= 16.0f) player_x_ -= 16.0f;

    // 2. Jump (KEY_A)
    if ((buttons & KEY_A) && !(prev_buttons & KEY_A) && is_grounded_) {
        player_vy_ = -10.0f;
        is_grounded_ = false;
    }

    // 3. Hammer Swing (KEY_B)
    if ((buttons & KEY_B) && !(prev_buttons & KEY_B)) {
        hammer_timer_ = 0.25f;
    }
    if (hammer_timer_ > 0.0f) {
        hammer_timer_ -= dt;
    }

    // 4. Vertical Physics
    if (!is_grounded_) {
        player_vy_ += gravity * dt;
        player_y_ += player_vy_ * dt;

        // Upward Head-Butt Ice Shatter
        if (player_vy_ < 0.0f) {
            int ceil_y = static_cast<int>(std::round(player_y_ - 0.45f));
            int head_x = static_cast<int>(std::round(player_x_));
            if (ceil_y >= 0 && ceil_y < 16 && head_x >= 0 && head_x < 16) {
                if (ice_grid_[ceil_y][head_x] == 2) {
                    BreakIceAt(head_x, ceil_y);
                    player_vy_ = 0.0f; // Rebound downward
                }
            }
        }
        // Downward Landing Check
        else if (player_vy_ >= 0.0f) {
            int floor_y = static_cast<int>(std::round(player_y_ + 1.0f));
            int foot_x = static_cast<int>(std::round(player_x_));

            if (floor_y >= 0 && floor_y < 16 && foot_x >= 0 && foot_x < 16) {
                if (ice_grid_[floor_y][foot_x] != 0 && player_y_ <= static_cast<float>(floor_y - 0.8f)) {
                    // Land on solid floor
                    player_y_ = static_cast<float>(floor_y - 1.0f);
                    player_vy_ = 0.0f;
                    is_grounded_ = true;
                }
            }
        }
    } else {
        // Grounded check: if floor underneath is broken, start falling
        int floor_y = static_cast<int>(std::round(player_y_ + 1.0f));
        int foot_x = static_cast<int>(std::round(player_x_));

        if (floor_y >= 0 && floor_y < 16 && foot_x >= 0 && foot_x < 16) {
            if (ice_grid_[floor_y][foot_x] == 0) {
                is_grounded_ = false; // Fall through hole
            }
        }
    }

    // Pit death
    if (player_y_ > 15.0f) {
        lives_--;
        state_ = STATE_DEAD;
        state_timer_ = 0.0f;
    }
}

void Game038IceClimber::UpdateTopis(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!topis_[i].active) continue;

        topis_[i].x += topis_[i].vx * dt;
        int fy = topis_[i].floor_y;

        // Bounce on boundary
        if (topis_[i].x <= 1.0f) {
            topis_[i].x = 1.0f;
            topis_[i].vx = -topis_[i].vx;
        } else if (topis_[i].x >= 14.0f) {
            topis_[i].x = 14.0f;
            topis_[i].vx = -topis_[i].vx;
        }

        // Check if there is a hole under Topi's feet to patch
        int tx = static_cast<int>(std::round(topis_[i].x));
        if (tx >= 1 && tx <= 14) {
            if (ice_grid_[fy][tx] == 0) {
                // Topi patches hole with fresh ice block!
                ice_grid_[fy][tx] = 2;
            }
        }
    }
}

void Game038IceClimber::UpdateCondor(float dt) {
    if (!condor_.active) return;

    condor_.x += condor_.vx * dt;
    if (condor_.vx > 0.0f && condor_.x > 18.0f) {
        condor_.x = 18.0f;
        condor_.vx = -condor_.vx;
    } else if (condor_.vx < 0.0f && condor_.x < -3.0f) {
        condor_.x = -3.0f;
        condor_.vx = -condor_.vx;
    }

    // Condor grab victory
    if (player_y_ <= 2.5f) {
        float dx = player_x_ - condor_.x;
        float dy = player_y_ - condor_.y;
        if (dx * dx + dy * dy <= 1.8f) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            score_ += 1000;
            if (score_ > high_score_) high_score_ = score_;
        }
    }
}

void Game038IceClimber::CheckCollisions() {
    // Check Topi touch
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!topis_[i].active) continue;

        int fy = topis_[i].floor_y;
        if (fabsf(player_y_ - (fy - 1.0f)) < 0.5f) {
            if (fabsf(player_x_ - topis_[i].x) < 0.8f) {
                if (hammer_timer_ > 0.0f) {
                    // Knock Topi off screen!
                    topis_[i].active = false;
                    score_ += 200;
                    if (score_ > high_score_) high_score_ = score_;
                } else {
                    // Hurt
                    lives_--;
                    state_ = STATE_DEAD;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }
    }
}

void Game038IceClimber::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

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
                player_x_ = 7.0f;
                player_y_ = 13.0f;
                player_vx_ = 0.0f;
                player_vy_ = 0.0f;
                is_grounded_ = true;
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
    UpdateTopis(dt);
    UpdateCondor(dt);
    CheckCollisions();
}

void Game038IceClimber::Render(uint8_t* fb) {
    // Sky: Polar Arctic Blue (#1A365D / #0F172A)
    for (int i = 0; i < 256; ++i) {
        fb[i * 3 + 0] = 15;
        fb[i * 3 + 1] = 23;
        fb[i * 3 + 2] = 42;
    }

    // 1. Draw Mountain Floors & Ice Blocks
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (ice_grid_[y][x] == 1) {
                // Solid rock/ice base
                fb[idx + 0] = 52; fb[idx + 1] = 73; fb[idx + 2] = 94; // Dark mountain granite
            } else if (ice_grid_[y][x] == 2) {
                // Breakable Cyan Ice Block
                fb[idx + 0] = 0; fb[idx + 1] = 210; fb[idx + 2] = 255; // Brilliant ice cyan
            }
        }
    }

    // 2. Draw Condor (Golden Pterodactyl at summit)
    if (condor_.active) {
        int cx = static_cast<int>(std::round(condor_.x));
        int cy = static_cast<int>(std::round(condor_.y));
        if (cx >= 0 && cx < 16 && cy >= 0 && cy < 16) {
            int idx = (cy * 16 + cx) * 3;
            fb[idx + 0] = 255; fb[idx + 1] = 215; fb[idx + 2] = 0; // Golden Bird
            if (cx > 0) {
                fb[(cy * 16 + (cx - 1)) * 3 + 0] = 241;
                fb[(cy * 16 + (cx - 1)) * 3 + 1] = 196;
                fb[(cy * 16 + (cx - 1)) * 3 + 2] = 15;
            }
        }
    }

    // 3. Draw Topis (Arctic Seals / Yetis: Snow White & Pink)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!topis_[i].active) continue;

        int tx = static_cast<int>(std::round(topis_[i].x));
        int ty = topis_[i].floor_y - 1;

        if (tx >= 0 && tx < 16 && ty >= 0 && ty < 16) {
            int idx = (ty * 16 + tx) * 3;
            fb[idx + 0] = 255; fb[idx + 1] = 182; fb[idx + 2] = 193; // Soft Pink Topi
        }
    }

    // 4. Draw Player Climber (Popo: Blue Parka & Wooden Mallet)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));

    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx + 0] = 52; fb[idx + 1] = 152; fb[idx + 2] = 219; // Blue Parka

        // Hammer swing flash
        if (hammer_timer_ > 0.0f) {
            if (px < 15) {
                int h_idx = (py * 16 + (px + 1)) * 3;
                fb[h_idx + 0] = 230; fb[h_idx + 1] = 126; fb[h_idx + 2] = 34; // Wood mallet
            }
        }
    }

    // 5. HUD: Lives on top row
    for (int l = 0; l < lives_ && l < 3; ++l) {
        int idx = (0 * 16 + l) * 3;
        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Red heart
    }
}

} // namespace arcade
