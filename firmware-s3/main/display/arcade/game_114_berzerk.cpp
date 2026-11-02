#include "game_114_berzerk.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game114Berzerk::Game114Berzerk() {
    Reset();
}

void Game114Berzerk::Init() {
    Reset();
}

void Game114Berzerk::Reset() {
    score_ = 0;
    lives_ = 3;
    rooms_cleared_ = 0;
    px_ = 8.0f;
    py_ = 8.0f;
    aim_dx_ = 1;
    aim_dy_ = 0;
    GenerateRoom();
}

void Game114Berzerk::GenerateRoom() {
    state_ = STATE_EXPLORING;
    state_timer_ = 0.0f;
    room_timer_ = 0.0f;
    otto_.active = false;

    // Reset lasers
    for (int i = 0; i < MAX_LASERS; ++i) {
        lasers_[i].active = false;
    }

    // Build Electrified Perimeter with 4 open doorways
    std::memset(maze_, 0, sizeof(maze_));

    for (int i = 0; i < 16; ++i) {
        maze_[0][i] = 1;  // Top wall
        maze_[15][i] = 1; // Bottom wall
        maze_[i][0] = 1;  // Left wall
        maze_[i][15] = 1; // Right wall
    }

    // Open Doorways
    maze_[0][7] = 0; maze_[0][8] = 0;   // North doorway
    maze_[15][7] = 0; maze_[15][8] = 0; // South doorway
    maze_[7][0] = 0; maze_[8][0] = 0;   // West doorway
    maze_[7][15] = 0; maze_[8][15] = 0; // East doorway

    // Interior electrified barriers (pattern varies by room index)
    int variant = rooms_cleared_ % 3;
    if (variant == 0) {
        for (int y = 4; y <= 7; ++y) maze_[y][4] = 1;
        for (int y = 8; y <= 11; ++y) maze_[y][11] = 1;
    } else if (variant == 1) {
        for (int x = 4; x <= 6; ++x) maze_[5][x] = 1;
        for (int x = 9; x <= 11; ++x) maze_[10][x] = 1;
    } else {
        maze_[5][5] = 1; maze_[5][10] = 1;
        maze_[10][5] = 1; maze_[10][10] = 1;
    }

    // Spawn Robots
    int count = std::min(MAX_ROBOTS, 2 + rooms_cleared_ / 2);
    float robot_spawns[4][2] = {
        {3.0f, 3.0f},
        {12.0f, 3.0f},
        {3.0f, 12.0f},
        {12.0f, 12.0f}
    };

    for (int i = 0; i < MAX_ROBOTS; ++i) {
        if (i < count) {
            robots_[i].x = robot_spawns[i][0];
            robots_[i].y = robot_spawns[i][1];
            robots_[i].shoot_timer = 1.0f + static_cast<float>(i) * 0.8f;
            robots_[i].active = true;
        } else {
            robots_[i].active = false;
        }
    }
}

bool Game114Berzerk::IsWall(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return false;
    return maze_[y][x] == 1;
}

void Game114Berzerk::ForceSpawnOtto() {
    otto_.active = true;
    otto_.x = 8.0f;
    otto_.y = 0.5f;
    otto_.bounce_timer = 0.0f;
}

void Game114Berzerk::FireLaser(float x, float y, float vx, float vy, bool is_player) {
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) {
            lasers_[i].x = x;
            lasers_[i].y = y;
            lasers_[i].vx = vx;
            lasers_[i].vy = vy;
            lasers_[i].is_player = is_player;
            lasers_[i].active = true;
            break;
        }
    }
}

void Game114Berzerk::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
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
                px_ = 8.0f;
                py_ = 8.0f;
                state_ = STATE_EXPLORING;
                otto_.active = false;
                room_timer_ = 0.0f;
            }
        }
        return;
    }

    if (state_ == STATE_ROOM_TRANSITION) {
        if (state_timer_ > 0.4f) {
            GenerateRoom();
        }
        return;
    }

    room_timer_ += dt;

    // Otto awakening threshold (7.0 seconds in room)
    if (!otto_.active && room_timer_ > 7.0f) {
        ForceSpawnOtto();
    }

    // Input Handling
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        float spd = 20.0f;
        FireLaser(px_ + static_cast<float>(aim_dx_) * 0.8f,
                  py_ + static_cast<float>(aim_dy_) * 0.8f,
                  static_cast<float>(aim_dx_) * spd,
                  static_cast<float>(aim_dy_) * spd,
                  true);
    }

    UpdatePlayer(dt, buttons);
    UpdateRobots(dt);
    UpdateLasers(dt);
    UpdateEvilOtto(dt);
    CheckCollisions();
}

void Game114Berzerk::UpdatePlayer(float dt, uint32_t buttons) {
    float move_spd = 5.5f;
    float dx = 0.0f;
    float dy = 0.0f;

    if (buttons & BTN_LEFT)  { dx -= 1.0f; aim_dx_ = -1; aim_dy_ = 0; }
    if (buttons & BTN_RIGHT) { dx += 1.0f; aim_dx_ = 1;  aim_dy_ = 0; }
    if (buttons & BTN_UP)    { dy -= 1.0f; aim_dx_ = 0;  aim_dy_ = -1; }
    if (buttons & BTN_DOWN)  { dy += 1.0f; aim_dx_ = 0;  aim_dy_ = 1; }

    px_ += dx * move_spd * dt;
    py_ += dy * move_spd * dt;

    // Doorway Sector Exit checks
    if (px_ < 0.2f && (py_ >= 6.5f && py_ <= 8.5f)) {
        // Exit West -> Enter next room East
        rooms_cleared_++;
        score_ += 100;
        px_ = 14.2f;
        state_ = STATE_ROOM_TRANSITION;
        state_timer_ = 0.0f;
        return;
    }
    if (px_ > 14.8f && (py_ >= 6.5f && py_ <= 8.5f)) {
        // Exit East -> Enter next room West
        rooms_cleared_++;
        score_ += 100;
        px_ = 0.8f;
        state_ = STATE_ROOM_TRANSITION;
        state_timer_ = 0.0f;
        return;
    }
    if (py_ < 0.2f && (px_ >= 6.5f && px_ <= 8.5f)) {
        // Exit North -> Enter next room South
        rooms_cleared_++;
        score_ += 100;
        py_ = 14.2f;
        state_ = STATE_ROOM_TRANSITION;
        state_timer_ = 0.0f;
        return;
    }
    if (py_ > 14.8f && (px_ >= 6.5f && px_ <= 8.5f)) {
        // Exit South -> Enter next room North
        rooms_cleared_++;
        score_ += 100;
        py_ = 0.8f;
        state_ = STATE_ROOM_TRANSITION;
        state_timer_ = 0.0f;
        return;
    }

    // Touch Electrified Wall Check
    int ix = static_cast<int>(std::round(px_));
    int iy = static_cast<int>(std::round(py_));
    if (IsWall(ix, iy)) {
        state_ = STATE_PLAYER_DYING;
        state_timer_ = 0.0f;
    }
}

void Game114Berzerk::UpdateRobots(float dt) {
    for (int i = 0; i < MAX_ROBOTS; ++i) {
        if (!robots_[i].active) continue;

        // Robots slowly stalk player
        float dx = px_ - robots_[i].x;
        float dy = py_ - robots_[i].y;
        float dist = std::sqrt(dx * dx + dy * dy);

        if (dist > 0.1f) {
            float step = 1.6f * dt;
            robots_[i].x += (dx / dist) * step;
            robots_[i].y += (dy / dist) * step;
        }

        // Robot walks into electric wall -> destroyed!
        int rx = static_cast<int>(std::round(robots_[i].x));
        int ry = static_cast<int>(std::round(robots_[i].y));
        if (IsWall(rx, ry)) {
            robots_[i].active = false;
            score_ += 50;
            continue;
        }

        // Robot weapon firing
        robots_[i].shoot_timer -= dt;
        if (robots_[i].shoot_timer <= 0.0f) {
            robots_[i].shoot_timer = 2.2f - std::min(1.0f, static_cast<float>(rooms_cleared_) * 0.15f);
            float lvx = 0.0f;
            float lvy = 0.0f;
            if (std::abs(dx) > std::abs(dy)) {
                lvx = (dx > 0) ? 12.0f : -12.0f;
            } else {
                lvy = (dy > 0) ? 12.0f : -12.0f;
            }
            FireLaser(robots_[i].x, robots_[i].y, lvx, lvy, false);
        }
    }
}

void Game114Berzerk::UpdateLasers(float dt) {
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) continue;

        lasers_[i].x += lasers_[i].vx * dt;
        lasers_[i].y += lasers_[i].vy * dt;

        int lx = static_cast<int>(std::round(lasers_[i].x));
        int ly = static_cast<int>(std::round(lasers_[i].y));

        // Offscreen or electric wall impact
        if (lx < 0 || lx >= 16 || ly < 0 || ly >= 16 || IsWall(lx, ly)) {
            lasers_[i].active = false;
        }
    }
}

void Game114Berzerk::UpdateEvilOtto(float dt) {
    if (!otto_.active) return;

    otto_.bounce_timer += dt * 4.0f;
    float otto_speed = 2.2f + static_cast<float>(rooms_cleared_) * 0.2f;

    float dx = px_ - otto_.x;
    float dy = py_ - otto_.y;
    float dist = std::sqrt(dx * dx + dy * dy);

    if (dist > 0.1f) {
        otto_.x += (dx / dist) * otto_speed * dt;
        otto_.y += (dy / dist) * otto_speed * dt;
    }
}

void Game114Berzerk::CheckCollisions() {
    // 1. Lasers
    for (int l = 0; l < MAX_LASERS; ++l) {
        if (!lasers_[l].active) continue;

        if (lasers_[l].is_player) {
            // Player laser vs Robots
            for (int r = 0; r < MAX_ROBOTS; ++r) {
                if (!robots_[r].active) continue;
                float dx = std::abs(lasers_[l].x - robots_[r].x);
                float dy = std::abs(lasers_[l].y - robots_[r].y);
                if (dx < 0.9f && dy < 0.9f) {
                    lasers_[l].active = false;
                    robots_[r].active = false;
                    score_ += 100;
                    break;
                }
            }
        } else {
            // Enemy laser vs Player
            float dx = std::abs(lasers_[l].x - px_);
            float dy = std::abs(lasers_[l].y - py_);
            if (dx < 0.8f && dy < 0.8f) {
                lasers_[l].active = false;
                state_ = STATE_PLAYER_DYING;
                state_timer_ = 0.0f;
                break;
            }
        }
    }

    // 2. Robot vs Player Body Collision
    for (int r = 0; r < MAX_ROBOTS; ++r) {
        if (!robots_[r].active) continue;
        float dx = std::abs(robots_[r].x - px_);
        float dy = std::abs(robots_[r].y - py_);
        if (dx < 0.8f && dy < 0.8f) {
            state_ = STATE_PLAYER_DYING;
            state_timer_ = 0.0f;
            break;
        }
    }

    // 3. Evil Otto vs Player Body Collision
    if (otto_.active) {
        float dx = std::abs(otto_.x - px_);
        float dy = std::abs(otto_.y - py_);
        if (dx < 0.9f && dy < 0.9f) {
            state_ = STATE_PLAYER_DYING;
            state_timer_ = 0.0f;
        }
    }
}

void Game114Berzerk::Render(uint8_t* fb) {
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

    // 1. Electrified High-Voltage Walls (Neon Electric Blue / Cyan)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (maze_[y][x] == 1) {
                set_pixel(x, y, 40, 140, 255);
            }
        }
    }

    // 2. Robots (Crimson torso & yellow eye)
    for (int r = 0; r < MAX_ROBOTS; ++r) {
        if (!robots_[r].active) continue;
        int rx = static_cast<int>(std::round(robots_[r].x));
        int ry = static_cast<int>(std::round(robots_[r].y));
        set_pixel(rx, ry, 230, 40, 30);
        set_pixel(rx, ry - 1, 255, 230, 40); // Eye visor
    }

    // 3. Lasers
    for (int l = 0; l < MAX_LASERS; ++l) {
        if (!lasers_[l].active) continue;
        int lx = static_cast<int>(std::round(lasers_[l].x));
        int ly = static_cast<int>(std::round(lasers_[l].y));
        if (lasers_[l].is_player) {
            set_pixel(lx, ly, 0, 255, 255); // Cyan plasma bolt
        } else {
            set_pixel(lx, ly, 255, 220, 0); // Yellow robot beam
        }
    }

    // 4. Evil Otto (Bouncing Smiling Ball)
    if (otto_.active) {
        int ox = static_cast<int>(std::round(otto_.x));
        int oy = static_cast<int>(std::round(otto_.y + std::abs(std::sin(otto_.bounce_timer)) * -0.6f));
        set_pixel(ox, oy, 255, 220, 0); // Yellow smiley
        set_pixel(ox, oy - 1, 255, 60, 40); // Smiling red eyes
    }

    // 5. Player Stickman
    if (state_ == STATE_EXPLORING) {
        int px = static_cast<int>(std::round(px_));
        int py = static_cast<int>(std::round(py_));
        set_pixel(px, py, 60, 240, 80); // Green humanoid body
        set_pixel(px, py - 1, 255, 220, 160); // Head
        // Gun aiming arm
        set_pixel(px + aim_dx_, py + aim_dy_, 220, 255, 100);
    } else if (state_ == STATE_PLAYER_DYING) {
        int px = static_cast<int>(std::round(px_));
        int py = static_cast<int>(std::round(py_));
        set_pixel(px, py, 255, 255, 255); // Electrocution white flash
        set_pixel(px - 1, py, 40, 140, 255);
        set_pixel(px + 1, py, 40, 140, 255);
        set_pixel(px, py - 1, 40, 140, 255);
        set_pixel(px, py + 1, 40, 140, 255);
    }

    // 6. Lives Indicator (Top-left doorway corner)
    for (int l = 0; l < lives_; ++l) {
        set_pixel(1 + l, 0, 60, 240, 80);
    }
}

} // namespace arcade