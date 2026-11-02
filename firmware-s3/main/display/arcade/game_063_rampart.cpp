#include "game_063_rampart.h"
#include <cmath>
#include <cstring>
#include <algorithm>
#include <queue>

namespace arcade {

Game063Rampart::Game063Rampart()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(3500),
      phase_(PHASE_BOMBARD),
      phase_timer_(8.0f),
      round_(1),
      cursor_x_(12),
      cursor_y_(7),
      castle_enclosed_(true),
      cannons_count_(2),
      ships_destroyed_(0) {
}

void Game063Rampart::Init() {
    Reset();
}

void Game063Rampart::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    round_ = 1;
    cannons_count_ = 2;
    ships_destroyed_ = 0;
    InitRound();
}

void Game063Rampart::InitRound() {
    std::memset(grid_, CELL_LAND, sizeof(grid_));

    // Ocean on east coast (x >= 10)
    for (int y = 0; y < 16; ++y) {
        for (int x = 10; x < 16; ++x) {
            grid_[y][x] = CELL_OCEAN;
        }
    }

    // Castle Keep at (4, 7) and (4, 8)
    grid_[7][4] = CELL_CASTLE;
    grid_[8][4] = CELL_CASTLE;

    // Enclosing stone walls
    for (int y = 6; y <= 9; ++y) {
        grid_[y][2] = CELL_WALL;
        grid_[y][6] = CELL_WALL;
    }
    for (int x = 2; x <= 6; ++x) {
        grid_[6][x] = CELL_WALL;
        grid_[9][x] = CELL_WALL;
    }

    // Mounted cannons
    grid_[7][6] = CELL_CANNON;
    grid_[8][6] = CELL_CANNON;

    castle_enclosed_ = true;
    phase_ = PHASE_BOMBARD;
    phase_timer_ = 8.0f;
    cursor_x_ = 12;
    cursor_y_ = 7;

    for (int i = 0; i < MAX_CANNONBALLS; ++i) cannonballs_[i].active = false;

    // Enemy armada ships in ocean
    ships_[0] = {12.0f, 2.0f, 1.2f, 1, true, 2.0f};
    ships_[1] = {14.0f, 6.0f, -1.0f, 1, true, 2.5f};
    ships_[2] = {11.0f, 11.0f, 1.5f, 1, true, 1.8f};
}

void Game063Rampart::FireCannonAtCursor() {
    for (int i = 0; i < MAX_CANNONBALLS; ++i) {
        if (!cannonballs_[i].active) {
            cannonballs_[i].active = true;
            cannonballs_[i].x = 6.0f;
            cannonballs_[i].y = 7.5f;
            cannonballs_[i].target_x = static_cast<float>(cursor_x_);
            cannonballs_[i].target_y = static_cast<float>(cursor_y_);
            cannonballs_[i].t = 0.0f;
            break;
        }
    }
}

void Game063Rampart::PlaceWallAtCursor() {
    if (cursor_x_ >= 0 && cursor_x_ < 10 && cursor_y_ >= 0 && cursor_y_ < 16) {
        if (grid_[cursor_y_][cursor_x_] == CELL_LAND) {
            grid_[cursor_y_][cursor_x_] = CELL_WALL;
            score_ += 10;
        }
    }
}

void Game063Rampart::CheckEnclosure() {
    // Flood-fill from edge of land to see if it reaches Castle Keep (4, 7)
    // If ocean/edge air can reach castle keep, it is NOT enclosed!
    bool visited[16][16];
    std::memset(visited, false, sizeof(visited));

    std::queue<std::pair<int, int>> q;

    // Push all outer border cells into queue
    for (int y = 0; y < 16; ++y) {
        q.push({0, y});
        q.push({9, y});
        visited[y][0] = true;
        visited[y][9] = true;
    }
    for (int x = 0; x < 10; ++x) {
        q.push({x, 0});
        q.push({x, 15});
        visited[0][x] = true;
        visited[15][x] = true;
    }

    bool castle_reached = false;
    const int dx[4] = {1, -1, 0, 0};
    const int dy[4] = {0, 0, 1, -1};

    while (!q.empty()) {
        auto [cx, cy] = q.front();
        q.pop();

        if (grid_[cy][cx] == CELL_CASTLE) {
            castle_reached = true;
            break;
        }

        // Walls block the flood fill!
        if (grid_[cy][cx] == CELL_WALL || grid_[cy][cx] == CELL_CANNON) {
            continue;
        }

        for (int i = 0; i < 4; ++i) {
            int nx = cx + dx[i];
            int ny = cy + dy[i];
            if (nx >= 0 && nx < 10 && ny >= 0 && ny < 16 && !visited[ny][nx]) {
                visited[ny][nx] = true;
                q.push({nx, ny});
            }
        }
    }

    castle_enclosed_ = !castle_reached;
}

void Game063Rampart::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 2.0f) {
            state_ = STATE_START;
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f) {
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            Reset();
        }
        return;
    }

    phase_timer_ -= dt;

    if (phase_ == PHASE_BOMBARD) {
        UpdateBombard(dt, buttons, prev_buttons);
        UpdateShips(dt);
        UpdateCannonballs(dt);

        if (phase_timer_ <= 0.0f) {
            phase_ = PHASE_REBUILD;
            phase_timer_ = 7.0f;
            cursor_x_ = 4;
            cursor_y_ = 7;
        }
    } else if (phase_ == PHASE_REBUILD) {
        UpdateRebuild(dt, buttons, prev_buttons);

        if (phase_timer_ <= 0.0f) {
            CheckEnclosure();
            if (castle_enclosed_) {
                score_ += 500;
                round_++;
                if (round_ > 3) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 1000;
                    if (score_ > high_score_) high_score_ = score_;
                } else {
                    phase_ = PHASE_BOMBARD;
                    phase_timer_ = 8.0f;
                    cursor_x_ = 12;
                    cursor_y_ = 7;
                }
            } else {
                // Castle breached and lost!
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
            }
        }
    }
}

void Game063Rampart::UpdateBombard(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Crosshair movement on ocean (x in [10, 15], y in [0, 15])
    if ((buttons & BUTTON_LEFT) && !(prev_buttons & BUTTON_LEFT))   cursor_x_ = std::max(10, cursor_x_ - 1);
    if ((buttons & BUTTON_RIGHT) && !(prev_buttons & BUTTON_RIGHT)) cursor_x_ = std::min(15, cursor_x_ + 1);
    if ((buttons & BUTTON_UP) && !(prev_buttons & BUTTON_UP))       cursor_y_ = std::max(0, cursor_y_ - 1);
    if ((buttons & BUTTON_DOWN) && !(prev_buttons & BUTTON_DOWN))   cursor_y_ = std::min(15, cursor_y_ + 1);

    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        FireCannonAtCursor();
    }
}

void Game063Rampart::UpdateRebuild(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Cursor movement on land (x in [0, 9], y in [0, 15])
    if ((buttons & BUTTON_LEFT) && !(prev_buttons & BUTTON_LEFT))   cursor_x_ = std::max(0, cursor_x_ - 1);
    if ((buttons & BUTTON_RIGHT) && !(prev_buttons & BUTTON_RIGHT)) cursor_x_ = std::min(9, cursor_x_ + 1);
    if ((buttons & BUTTON_UP) && !(prev_buttons & BUTTON_UP))       cursor_y_ = std::max(0, cursor_y_ - 1);
    if ((buttons & BUTTON_DOWN) && !(prev_buttons & BUTTON_DOWN))   cursor_y_ = std::min(15, cursor_y_ + 1);

    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        PlaceWallAtCursor();
    }
}

void Game063Rampart::UpdateShips(float dt) {
    for (int i = 0; i < MAX_SHIPS; ++i) {
        if (!ships_[i].active) continue;

        ships_[i].y += ships_[i].vy * dt;
        if (ships_[i].y < 1.0f) {
            ships_[i].y = 1.0f;
            ships_[i].vy = std::abs(ships_[i].vy);
        } else if (ships_[i].y > 14.0f) {
            ships_[i].y = 14.0f;
            ships_[i].vy = -std::abs(ships_[i].vy);
        }

        // Ship firing at walls
        ships_[i].shoot_cooldown -= dt;
        if (ships_[i].shoot_cooldown <= 0.0f) {
            ships_[i].shoot_cooldown = 2.2f;
            // Breach a wall tile!
            int wall_x = 6;
            int wall_y = static_cast<int>(std::round(ships_[i].y));
            wall_y = std::max(6, std::min(9, wall_y));
            if (grid_[wall_y][wall_x] == CELL_WALL) {
                grid_[wall_y][wall_x] = CELL_LAND; // Wall breached!
            }
        }
    }
}

void Game063Rampart::UpdateCannonballs(float dt) {
    for (int i = 0; i < MAX_CANNONBALLS; ++i) {
        if (!cannonballs_[i].active) continue;

        cannonballs_[i].t += dt * 3.0f;
        cannonballs_[i].x = (1.0f - cannonballs_[i].t) * 6.0f + cannonballs_[i].t * cannonballs_[i].target_x;
        cannonballs_[i].y = (1.0f - cannonballs_[i].t) * 7.5f + cannonballs_[i].t * cannonballs_[i].target_y;

        if (cannonballs_[i].t >= 1.0f) {
            cannonballs_[i].active = false;
            // Explosion hit check on ships
            for (int s = 0; s < MAX_SHIPS; ++s) {
                if (!ships_[s].active) continue;
                if (std::abs(cannonballs_[i].target_x - ships_[s].x) < 1.4f &&
                    std::abs(cannonballs_[i].target_y - ships_[s].y) < 1.4f) {
                    ships_[s].active = false;
                    ships_destroyed_++;
                    score_ += 200;
                    break;
                }
            }
        }
    }
}

void Game063Rampart::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Map tiles
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            uint8_t cell = grid_[y][x];

            if (cell == CELL_OCEAN) {
                fb[idx] = 20;  fb[idx + 1] = 60;  fb[idx + 2] = 160; // Sea blue
            } else if (cell == CELL_LAND) {
                fb[idx] = 60;  fb[idx + 1] = 140; fb[idx + 2] = 40;  // Green field
            } else if (cell == CELL_CASTLE) {
                fb[idx] = 255; fb[idx + 1] = 215; fb[idx + 2] = 0;   // Gold castle keep
            } else if (cell == CELL_WALL) {
                fb[idx] = 180; fb[idx + 1] = 180; fb[idx + 2] = 190; // Stone wall
            } else if (cell == CELL_CANNON) {
                fb[idx] = 50;  fb[idx + 1] = 50;  fb[idx + 2] = 50;   // Iron cannon
            }
        }
    }

    // Armada ships (Dark wood & white sail)
    for (int s = 0; s < MAX_SHIPS; ++s) {
        if (!ships_[s].active) continue;
        int sx = static_cast<int>(std::round(ships_[s].x));
        int sy = static_cast<int>(std::round(ships_[s].y));
        if (sx >= 0 && sx < 16 && sy >= 0 && sy < 16) {
            int idx = (sy * 16 + sx) * 3;
            fb[idx] = 140; fb[idx + 1] = 80; fb[idx + 2] = 30; // Wood hull
            if (sx < 15) {
                int sail_idx = (sy * 16 + (sx + 1)) * 3;
                fb[sail_idx] = 255; fb[sail_idx + 1] = 255; fb[sail_idx + 2] = 255; // White sail
            }
        }
    }

    // Cannonballs
    for (int i = 0; i < MAX_CANNONBALLS; ++i) {
        if (!cannonballs_[i].active) continue;
        int bx = static_cast<int>(std::round(cannonballs_[i].x));
        int by = static_cast<int>(std::round(cannonballs_[i].y));
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            fb[idx] = 255; fb[idx + 1] = 100; fb[idx + 2] = 0; // Fire bomb
        }
    }

    // Cursor (Crosshair or placement cursor)
    if (cursor_x_ >= 0 && cursor_x_ < 16 && cursor_y_ >= 0 && cursor_y_ < 16) {
        int idx = (cursor_y_ * 16 + cursor_x_) * 3;
        if (phase_ == PHASE_BOMBARD) {
            fb[idx] = 255; fb[idx + 1] = 0; fb[idx + 2] = 0; // Red crosshair
        } else {
            fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255; // White wall brick cursor
        }
    }

    // HUD: Timer & Round indicator on row 0
    int time_bars = static_cast<int>((phase_timer_ / 8.0f) * 10.0f);
    for (int t = 0; t < time_bars && t < 10; ++t) {
        int idx = t * 3;
        fb[idx] = (phase_ == PHASE_BOMBARD) ? 255 : 0;
        fb[idx + 1] = (phase_ == PHASE_BOMBARD) ? 100 : 255;
        fb[idx + 2] = (phase_ == PHASE_BOMBARD) ? 0 : 255;
    }

    for (int r = 0; r < round_ && r < 3; ++r) {
        int idx = (15 - r) * 3;
        fb[idx] = 255; fb[idx + 1] = 215; fb[idx + 2] = 0; // Gold round crest
    }
}

} // namespace arcade
