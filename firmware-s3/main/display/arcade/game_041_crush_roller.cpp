#include "game_041_crush_roller.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

static const int DX[4] = {0, 1, 0, -1};
static const int DY[4] = {-1, 0, 1, 0};

Game041CrushRoller::Game041CrushRoller()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      lives_(3),
      unpainted_tiles_(0),
      total_paint_tiles_(0),
      player_x_(1.0f),
      player_y_(1.0f),
      player_dir_(1),
      next_dir_(1) {
}

void Game041CrushRoller::Init() {
    Reset();
}

void Game041CrushRoller::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    player_x_ = 1.0f;
    player_y_ = 1.0f;
    player_dir_ = 1;
    next_dir_ = 1;

    InitMaze();

    // Rollers
    rollers_[0] = {5.0f, 5.0f, 0, true, 0.0f};
    rollers_[1] = {10.0f, 9.0f, 0, true, 0.0f};

    // Monsters
    monsters_[0] = {14.0f, 14.0f, 3, true, 0.0f};
    monsters_[1] = {14.0f, 1.0f, 2, true, 0.0f};
}

void Game041CrushRoller::InitMaze() {
    // 0: Wall, 1: Unpainted Road, 2: Painted Road
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            maze_[y][x] = 0; // Default wall
        }
    }

    // Grid of roads: Rows 1, 5, 9, 14 and Columns 1, 5, 10, 14
    const int road_rows[4] = {1, 5, 9, 14};
    const int road_cols[4] = {1, 5, 10, 14};

    for (int r = 0; r < 4; ++r) {
        int ry = road_rows[r];
        for (int x = 1; x <= 14; ++x) {
            maze_[ry][x] = 1;
        }
    }

    for (int c = 0; c < 4; ++c) {
        int cx = road_cols[c];
        for (int y = 1; y <= 14; ++y) {
            maze_[y][cx] = 1;
        }
    }

    // Count paintable tiles
    unpainted_tiles_ = 0;
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (maze_[y][x] == 1) {
                unpainted_tiles_++;
            }
        }
    }
    total_paint_tiles_ = unpainted_tiles_;

    // Starting tile painted
    PaintTile(1, 1);
}

void Game041CrushRoller::PaintTile(int x, int y) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        if (maze_[y][x] == 1) {
            maze_[y][x] = 2; // Painted!
            unpainted_tiles_--;
            score_ += 10;
            if (score_ > high_score_) high_score_ = score_;

            if (unpainted_tiles_ == 0) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                score_ += 1000;
                if (score_ > high_score_) high_score_ = score_;
            }
        }
    }
}

bool Game041CrushRoller::TriggerRoller(int idx) {
    if (idx < 0 || idx >= MAX_ROLLERS) return false;
    if (!rollers_[idx].active || rollers_[idx].dir != 0 || rollers_[idx].cooldown > 0.0f) {
        return false;
    }

    // Launch roller in player's current direction
    rollers_[idx].dir = player_dir_ + 1; // 1: Right, 2: Down, 3: Left, 4: Up
    return true;
}

void Game041CrushRoller::UpdatePlayer(float dt, uint32_t buttons) {
    if (buttons & KEY_UP)    next_dir_ = 0;
    else if (buttons & KEY_RIGHT) next_dir_ = 1;
    else if (buttons & KEY_DOWN)  next_dir_ = 2;
    else if (buttons & KEY_LEFT)  next_dir_ = 3;

    const float speed = 4.2f;

    // Corner turning grid alignment
    float gx = std::round(player_x_);
    float gy = std::round(player_y_);
    float dist_to_center = fabsf(player_x_ - gx) + fabsf(player_y_ - gy);

    if (dist_to_center < 0.25f && next_dir_ != player_dir_) {
        int nx = static_cast<int>(gx) + DX[next_dir_];
        int ny = static_cast<int>(gy) + DY[next_dir_];
        if (nx >= 0 && nx < 16 && ny >= 0 && ny < 16 && maze_[ny][nx] != 0) {
            player_x_ = gx;
            player_y_ = gy;
            player_dir_ = next_dir_;
        }
    }

    // Advance
    float next_x = player_x_ + DX[player_dir_] * speed * dt;
    float next_y = player_y_ + DY[player_dir_] * speed * dt;

    int check_x = static_cast<int>(std::round(next_x + DX[player_dir_] * 0.45f));
    int check_y = static_cast<int>(std::round(next_y + DY[player_dir_] * 0.45f));

    if (check_x >= 0 && check_x < 16 && check_y >= 0 && check_y < 16 && maze_[check_y][check_x] != 0) {
        player_x_ = next_x;
        player_y_ = next_y;
    } else {
        player_x_ = gx;
        player_y_ = gy;
    }

    // Paint current cell
    PaintTile(static_cast<int>(std::round(player_x_)), static_cast<int>(std::round(player_y_)));

    // Check roller trigger
    for (int r = 0; r < MAX_ROLLERS; ++r) {
        if (rollers_[r].dir == 0 && rollers_[r].cooldown <= 0.0f) {
            float dist = fabsf(player_x_ - rollers_[r].x) + fabsf(player_y_ - rollers_[r].y);
            if (dist <= 0.85f) {
                TriggerRoller(r);
            }
        }
    }
}

void Game041CrushRoller::UpdateRollers(float dt) {
    const float roller_speed = 12.0f;

    for (int r = 0; r < MAX_ROLLERS; ++r) {
        if (rollers_[r].cooldown > 0.0f) {
            rollers_[r].cooldown -= dt;
        }

        if (rollers_[r].dir == 0) continue; // Idle

        int dir_idx = rollers_[r].dir - 1;
        rollers_[r].x += DX[dir_idx] * roller_speed * dt;
        rollers_[r].y += DY[dir_idx] * roller_speed * dt;

        // Check wall hit -> stops and cooldown
        int check_x = static_cast<int>(std::round(rollers_[r].x + DX[dir_idx] * 0.5f));
        int check_y = static_cast<int>(std::round(rollers_[r].y + DY[dir_idx] * 0.5f));

        if (check_x < 0 || check_x >= 16 || check_y < 0 || check_y >= 16 || maze_[check_y][check_x] == 0) {
            rollers_[r].dir = 0; // Stop
            rollers_[r].cooldown = 4.0f;
            // Reset to original position
            if (r == 0) { rollers_[r].x = 5.0f; rollers_[r].y = 5.0f; }
            else { rollers_[r].x = 10.0f; rollers_[r].y = 9.0f; }
            continue;
        }

        // Crush Monsters
        for (int m = 0; m < MAX_ENEMIES; ++m) {
            if (monsters_[m].active) {
                float dist = fabsf(rollers_[r].x - monsters_[m].x) + fabsf(rollers_[r].y - monsters_[m].y);
                if (dist <= 1.1f) {
                    monsters_[m].active = false;
                    monsters_[m].respawn_timer = 4.0f;
                    score_ += 400; // Crushed monster bonus!
                    if (score_ > high_score_) high_score_ = score_;
                }
            }
        }
    }
}

void Game041CrushRoller::UpdateMonsters(float dt) {
    const float speed = 3.2f;

    for (int m = 0; m < MAX_ENEMIES; ++m) {
        if (!monsters_[m].active) {
            monsters_[m].respawn_timer -= dt;
            if (monsters_[m].respawn_timer <= 0.0f) {
                monsters_[m].active = true;
                monsters_[m].x = 14.0f;
                monsters_[m].y = 14.0f;
            }
            continue;
        }

        float mgx = std::round(monsters_[m].x);
        float mgy = std::round(monsters_[m].y);
        float dist_to_center = fabsf(monsters_[m].x - mgx) + fabsf(monsters_[m].y - mgy);

        if (dist_to_center < 0.22f) {
            int best_dir = monsters_[m].dir;
            float min_dist = 99999.0f;
            int opp_dir = (monsters_[m].dir + 2) % 4;

            for (int d = 0; d < 4; ++d) {
                int nx = static_cast<int>(mgx) + DX[d];
                int ny = static_cast<int>(mgy) + DY[d];

                if (nx >= 0 && nx < 16 && ny >= 0 && ny < 16 && maze_[ny][nx] != 0) {
                    float penalty = (d == opp_dir) ? 10.0f : 0.0f;
                    float d2 = (nx - player_x_) * (nx - player_x_) +
                               (ny - player_y_) * (ny - player_y_) + penalty;
                    if (d2 < min_dist) {
                        min_dist = d2;
                        best_dir = d;
                    }
                }
            }

            monsters_[m].x = mgx;
            monsters_[m].y = mgy;
            monsters_[m].dir = best_dir;
        }

        monsters_[m].x += DX[monsters_[m].dir] * speed * dt;
        monsters_[m].y += DY[monsters_[m].dir] * speed * dt;
    }
}

void Game041CrushRoller::CheckCollisions() {
    for (int m = 0; m < MAX_ENEMIES; ++m) {
        if (monsters_[m].active) {
            float dist = fabsf(player_x_ - monsters_[m].x) + fabsf(player_y_ - monsters_[m].y);
            if (dist <= 0.72f) {
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game041CrushRoller::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DEAD) {
        if (state_timer_ >= 1.5f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                player_x_ = 1.0f;
                player_y_ = 1.0f;
                player_dir_ = 1;
                next_dir_ = 1;
            }
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ >= 2.5f && (buttons & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT))) {
            Reset();
        }
        return;
    }

    UpdatePlayer(dt, buttons);
    UpdateRollers(dt);
    UpdateMonsters(dt);
    CheckCollisions();
}

void Game041CrushRoller::Render(uint8_t* fb) {
    // 1. Draw Maze & Painted Surfaces
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            uint8_t tile = maze_[y][x];

            if (tile == 0) {
                // Wall: Midnight Blue City Block (#1E3799)
                fb[idx + 0] = 30; fb[idx + 1] = 55; fb[idx + 2] = 153;
            } else if (tile == 1) {
                // Unpainted Road: Dark Asphalt Grey (#4A5568)
                fb[idx + 0] = 74; fb[idx + 1] = 85; fb[idx + 2] = 104;
            } else if (tile == 2) {
                // Painted Road: Vibrant Golden Yellow (#F1C40F)
                fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15;
            }
        }
    }

    // 2. Draw Steamrollers (Heavy Industrial Silver/Amber Roller)
    for (int r = 0; r < MAX_ROLLERS; ++r) {
        if (!rollers_[r].active) continue;
        int rx = static_cast<int>(std::round(rollers_[r].x));
        int ry = static_cast<int>(std::round(rollers_[r].y));
        if (rx >= 0 && rx < 16 && ry >= 0 && ry < 16) {
            int idx = (ry * 16 + rx) * 3;
            if (rollers_[r].dir != 0) {
                // Active charging roller: Fiery Orange
                fb[idx + 0] = 230; fb[idx + 1] = 126; fb[idx + 2] = 34;
            } else {
                // Parked roller: Steel Cyan
                fb[idx + 0] = 0; fb[idx + 1] = 206; fb[idx + 2] = 209;
            }
        }
    }

    // 3. Draw Monsters (Chasing Sea Critters: Crimson Red #E74C3C)
    for (int m = 0; m < MAX_ENEMIES; ++m) {
        if (!monsters_[m].active) continue;
        int mx = static_cast<int>(std::round(monsters_[m].x));
        int my = static_cast<int>(std::round(monsters_[m].y));
        if (mx >= 0 && mx < 16 && my >= 0 && my < 16) {
            int idx = (my * 16 + mx) * 3;
            fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
        }
    }

    // 4. Draw Player Paintbrush (Pure White Roller with Bristles)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255; // White brush
    }

    // 5. HUD: Lives on top row
    for (int l = 0; l < lives_ && l < 3; ++l) {
        int idx = (0 * 16 + l) * 3;
        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
    }
}

} // namespace arcade
