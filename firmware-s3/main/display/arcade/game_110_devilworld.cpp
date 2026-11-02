#include "game_110_devilworld.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game110DevilWorld::Game110DevilWorld() {
    Reset();
}

void Game110DevilWorld::Init() {
    Reset();
}

void Game110DevilWorld::Reset() {
    score_ = 0;
    lives_ = 3;
    round_ = 1;
    InitMaze();
}

void Game110DevilWorld::InitMaze() {
    state_ = STATE_NAVIGATING;
    state_timer_ = 0.0f;
    pearls_remaining_ = 0;
    has_cross_ = false;
    fire_breath_timer_ = 0.0f;

    px_ = 8.0f;
    py_ = 8.0f;
    facing_x_ = 1;
    facing_y_ = 0;

    devil_point_dir_ = 0;
    devil_timer_ = 2.5f;
    maze_shift_x_ = 0.0f;
    maze_shift_y_ = 0.0f;

    cross_x_ = 8.0f;
    cross_y_ = 12.0f;
    cross_spawned_ = true;

    std::memset(maze_, 0, sizeof(maze_));

    // Outer boundary walls: top y=2, bot y=15, left x=0, right x=15
    for (int x = 0; x < 16; ++x) {
        maze_[2][x] = 1;
        maze_[15][x] = 1;
    }
    for (int y = 2; y < 16; ++y) {
        maze_[y][0] = 1;
        maze_[y][15] = 1;
    }

    // Interior maze blocks (Devil World symmetrical layout)
    int blocks[6][4] = {
        {4, 5, 6, 6},   // Left top block
        {9, 5, 11, 6},  // Right top block
        {4, 9, 6, 10},  // Left bot block
        {9, 9, 11, 10}, // Right bot block
        {7, 4, 8, 5},   // Center divider top
        {7, 10, 8, 11}  // Center divider bot
    };

    for (int b = 0; b < 6; ++b) {
        for (int y = blocks[b][1]; y <= blocks[b][3]; ++y) {
            for (int x = blocks[b][0]; x <= blocks[b][2]; ++x) {
                maze_[y][x] = 1;
            }
        }
    }

    // Scatter pearl dots (type 2) in corridors
    for (int y = 3; y < 15; ++y) {
        for (int x = 1; x < 15; ++x) {
            if (maze_[y][x] == 0 && (x + y) % 2 == 0) {
                maze_[y][x] = 2;
                pearls_remaining_++;
            }
        }
    }

    // Spawn 2 Co-Devil Monsters
    monsters_[0].active = true;
    monsters_[0].x = 3.0f;
    monsters_[0].y = 4.0f;
    monsters_[0].vx = 2.2f;
    monsters_[0].vy = 0.0f;
    monsters_[0].is_fried_egg = false;

    monsters_[1].active = true;
    monsters_[1].x = 12.0f;
    monsters_[1].y = 13.0f;
    monsters_[1].vx = -2.2f;
    monsters_[1].vy = 0.0f;
    monsters_[1].is_fried_egg = false;
}

void Game110DevilWorld::SetDevilDirection(int dir) {
    devil_point_dir_ = dir;
}

void Game110DevilWorld::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_CRUSHED) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                state_ = STATE_NAVIGATING;
                state_timer_ = 0.0f;
                px_ = 8.0f;
                py_ = 8.0f;
                devil_point_dir_ = 0;
            }
        }
        return;
    }

    if (state_ == STATE_ROUND_CLEAR) {
        if (state_timer_ > 2.5f) {
            round_++;
            InitMaze();
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    UpdateDevil(dt);
    UpdateTamagon(dt, buttons, prev_buttons);
    UpdateMonsters(dt);
    CheckCollisions();
    CheckWallCrush();

    if (pearls_remaining_ <= 0 && state_ != STATE_ROUND_CLEAR) {
        state_ = STATE_ROUND_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1500;
    }
}

void Game110DevilWorld::UpdateDevil(float dt) {
    devil_timer_ -= dt;
    if (devil_timer_ <= 0.0f) {
        devil_timer_ = 2.5f;
        // The Devil points in a new direction (1=Left, 2=Right, 3=Up, 4=Down)
        static int dir_cycle = 0;
        devil_point_dir_ = (dir_cycle++ % 4) + 1;
    }

    // Apply continuous maze shift velocity depending on devil's point
    float shift_spd = 1.4f;
    if (devil_point_dir_ == 1) { // Left
        px_ -= shift_spd * dt;
        for (int m = 0; m < MAX_MONSTERS; ++m) monsters_[m].x -= shift_spd * dt;
    } else if (devil_point_dir_ == 2) { // Right
        px_ += shift_spd * dt;
        for (int m = 0; m < MAX_MONSTERS; ++m) monsters_[m].x += shift_spd * dt;
    } else if (devil_point_dir_ == 3) { // Up
        py_ -= shift_spd * dt;
        for (int m = 0; m < MAX_MONSTERS; ++m) monsters_[m].y -= shift_spd * dt;
    } else if (devil_point_dir_ == 4) { // Down
        py_ += shift_spd * dt;
        for (int m = 0; m < MAX_MONSTERS; ++m) monsters_[m].y += shift_spd * dt;
    }
}

void Game110DevilWorld::UpdateTamagon(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_spd = 5.0f;
    float next_x = px_;
    float next_y = py_;

    if (buttons & BTN_LEFT) {
        next_x -= move_spd * dt;
        facing_x_ = -1; facing_y_ = 0;
    } else if (buttons & BTN_RIGHT) {
        next_x += move_spd * dt;
        facing_x_ = 1; facing_y_ = 0;
    } else if (buttons & BTN_UP) {
        next_y -= move_spd * dt;
        facing_x_ = 0; facing_y_ = -1;
    } else if (buttons & BTN_DOWN) {
        next_y += move_spd * dt;
        facing_x_ = 0; facing_y_ = 1;
    }

    // Corridor movement collision with interior maze walls
    int cx = static_cast<int>(std::round(next_x));
    int cy = static_cast<int>(std::round(next_y));
    if (cx >= 0 && cx < 16 && cy >= 0 && cy < 16) {
        if (maze_[cy][cx] != 1) {
            px_ = next_x;
            py_ = next_y;
        }
    }

    // Pick up Holy Cross
    if (cross_spawned_) {
        if (std::abs(px_ - cross_x_) < 1.0f && std::abs(py_ - cross_y_) < 1.0f) {
            has_cross_ = true;
            cross_spawned_ = false;
            score_ += 300;
        }
    }

    // Eat pearls
    int grid_x = static_cast<int>(std::round(px_));
    int grid_y = static_cast<int>(std::round(py_));
    if (grid_x >= 1 && grid_x < 15 && grid_y >= 3 && grid_y < 15) {
        if (maze_[grid_y][grid_x] == 2) {
            maze_[grid_y][grid_x] = 0;
            pearls_remaining_--;
            score_ += 10;
        }
    }

    // Button A: Fire breath when carrying cross
    if (fire_breath_timer_ > 0.0f) fire_breath_timer_ -= dt;
    if ((buttons & BTN_A) && has_cross_ && fire_breath_timer_ <= 0.0f) {
        fire_breath_timer_ = 0.4f;
        float fire_x = px_ + static_cast<float>(facing_x_) * 1.5f;
        float fire_y = py_ + static_cast<float>(facing_y_) * 1.5f;

        // Fry monsters into fried eggs!
        for (int m = 0; m < MAX_MONSTERS; ++m) {
            if (!monsters_[m].active) continue;
            if (std::abs(monsters_[m].x - fire_x) < 1.3f &&
                std::abs(monsters_[m].y - fire_y) < 1.3f) {
                monsters_[m].is_fried_egg = true;
                monsters_[m].egg_timer = 5.0f;
                score_ += 100;
            }
        }
    }
}

void Game110DevilWorld::UpdateMonsters(float dt) {
    for (int m = 0; m < MAX_MONSTERS; ++m) {
        if (!monsters_[m].active) continue;

        if (monsters_[m].is_fried_egg) {
            monsters_[m].egg_timer -= dt;
            if (monsters_[m].egg_timer <= 0.0f) {
                // Hatches back into monster!
                monsters_[m].is_fried_egg = false;
            }
            continue;
        }

        // Patrol corridor movement
        monsters_[m].x += monsters_[m].vx * dt;
        int mx = static_cast<int>(std::round(monsters_[m].x));
        int my = static_cast<int>(std::round(monsters_[m].y));

        if (mx <= 1 || mx >= 14 || (my >= 0 && my < 16 && maze_[my][mx] == 1)) {
            monsters_[m].vx = -monsters_[m].vx;
        }
    }
}

void Game110DevilWorld::CheckCollisions() {
    for (int m = 0; m < MAX_MONSTERS; ++m) {
        if (!monsters_[m].active) continue;

        float dx = std::abs(px_ - monsters_[m].x);
        float dy = std::abs(py_ - monsters_[m].y);

        if (dx < 0.9f && dy < 0.9f) {
            if (monsters_[m].is_fried_egg) {
                // Tamagon devours the fried egg!
                monsters_[m].active = false;
                score_ += 400;
            } else {
                // Monster touches Tamagon
                state_ = STATE_CRUSHED;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game110DevilWorld::CheckWallCrush() {
    // If Tamagon is pushed out of valid playable corridor bounds into solid outer walls:
    // Screen perimeter boundaries: left x <= 0.6, right x >= 14.4, top y <= 2.2, bot y >= 14.4
    if (px_ <= 0.6f || px_ >= 14.4f || py_ <= 2.2f || py_ >= 14.4f) {
        state_ = STATE_CRUSHED;
        state_timer_ = 0.0f;
    }
}

void Game110DevilWorld::Render(uint8_t* fb) {
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

    // The Devil's Lair at top rows (y=0..1)
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 1, 80, 20, 20); // Dark red altar ledge
    }
    // Giant Devil in center (x=7..8, y=0)
    set_pixel(7, 0, 220, 30, 20); // Devil red body
    set_pixel(8, 0, 255, 60, 40);
    // Devil's Horns
    set_pixel(6, 0, 255, 220, 0);
    set_pixel(9, 0, 255, 220, 0);

    // Devil's Pointing Direction indicator
    if (devil_point_dir_ == 1) set_pixel(5, 0, 255, 255, 255);      // Pointing Left
    else if (devil_point_dir_ == 2) set_pixel(10, 0, 255, 255, 255); // Pointing Right
    else if (devil_point_dir_ == 3) set_pixel(7, 0, 255, 255, 255);  // Pointing Up
    else if (devil_point_dir_ == 4) set_pixel(8, 1, 255, 255, 255);  // Pointing Down

    // Maze Blocks & Pearls
    for (int y = 2; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            uint8_t cell = maze_[y][x];
            if (cell == 1) {
                // Solid purple maze wall
                set_pixel(x, y, 120, 40, 160);
            } else if (cell == 2) {
                // Gold pearl dot
                set_pixel(x, y, 255, 220, 40);
            }
        }
    }

    // Holy Cross (Golden crucifix)
    if (cross_spawned_) {
        int cx = static_cast<int>(std::round(cross_x_));
        int cy = static_cast<int>(std::round(cross_y_));
        set_pixel(cx, cy, 255, 255, 255);
        set_pixel(cx, cy - 1, 255, 220, 0);
        set_pixel(cx - 1, cy, 255, 220, 0);
        set_pixel(cx + 1, cy, 255, 220, 0);
    }

    // Monsters (Co-Devils / Fried Eggs)
    for (int m = 0; m < MAX_MONSTERS; ++m) {
        if (!monsters_[m].active) continue;
        int mx = static_cast<int>(std::round(monsters_[m].x));
        int my = static_cast<int>(std::round(monsters_[m].y));

        if (monsters_[m].is_fried_egg) {
            // Sunny-side up fried egg
            set_pixel(mx, my, 255, 200, 20);     // Yolk
            set_pixel(mx - 1, my, 240, 240, 250); // White
            set_pixel(mx + 1, my, 240, 240, 250);
        } else {
            // Blue bat-winged Co-Devil
            set_pixel(mx, my, 40, 100, 240);
            set_pixel(mx - 1, my, 60, 140, 255);
            set_pixel(mx + 1, my, 60, 140, 255);
        }
    }

    // Tamagon Dragon
    int tx = static_cast<int>(std::round(px_));
    int ty = static_cast<int>(std::round(py_));

    if (state_ == STATE_CRUSHED) {
        // Flattened dragon pancake
        set_pixel(tx - 1, ty, 60, 200, 60);
        set_pixel(tx, ty, 255, 50, 40);
        set_pixel(tx + 1, ty, 60, 200, 60);
    } else {
        // Green dragon Tamagon
        set_pixel(tx, ty, 40, 220, 50);       // Green belly
        set_pixel(tx, ty - 1, 50, 240, 70);   // Snout
        if (has_cross_) {
            set_pixel(tx + facing_x_, ty, 255, 220, 0); // Holding golden cross
        }
        // Fire breath burst
        if (fire_breath_timer_ > 0.0f) {
            set_pixel(tx + facing_x_ * 2, ty + facing_y_ * 2, 255, 80, 20);
        }
    }

    // Lives
    for (int l = 0; l < std::min(lives_, 3); ++l) {
        set_pixel(l * 2, 0, 40, 220, 50);
    }
}

} // namespace arcade
