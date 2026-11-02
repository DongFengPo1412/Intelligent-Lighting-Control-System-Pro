#include "game_093_pengo.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game093Pengo::Game093Pengo() {
    Init();
}

void Game093Pengo::Init() {
    ResetMaze(true);
}

void Game093Pengo::Reset() {
    ResetMaze(true);
}

void Game093Pengo::ResetMaze(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        round_ = 1;
    }
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    snobees_crushed_ = 0;

    px_ = 7;
    py_ = 13;
    facing_x_ = 0;
    facing_y_ = -1;
    move_cooldown_ = 0.0f;

    sliding_block_.active = false;

    // Initialize Grid with Borders
    for (int y = 0; y < GRID_SIZE; ++y) {
        for (int x = 0; x < GRID_SIZE; ++x) {
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                grid_[y][x] = BLOCK_WALL;
            } else {
                grid_[y][x] = BLOCK_EMPTY;
            }
        }
    }

    // Scatter Ice Blocks symmetrically
    for (int y = 2; y <= 12; y += 2) {
        for (int x = 2; x <= 13; x += 2) {
            grid_[y][x] = BLOCK_ICE;
        }
    }

    // Place 3 Diamond Blocks
    grid_[4][4] = BLOCK_DIAMOND;
    grid_[4][10] = BLOCK_DIAMOND;
    grid_[8][7] = BLOCK_DIAMOND;

    // Clear starting spots for Pengo and Sno-Bees
    grid_[13][7] = BLOCK_EMPTY;
    grid_[12][7] = BLOCK_EMPTY;

    // Spawn Sno-Bees
    for (int i = 0; i < MAX_SNOBEES; ++i) {
        snobees_[i].active = true;
        snobees_[i].stun_timer = 0.0f;
        snobees_[i].move_timer = 0.0f;
        snobees_[i].respawn_timer = 0.0f;
        if (i == 0) { snobees_[i].x = 2; snobees_[i].y = 2; }
        else if (i == 1) { snobees_[i].x = 13; snobees_[i].y = 2; }
        else { snobees_[i].x = 7; snobees_[i].y = 2; }
        grid_[snobees_[i].y][snobees_[i].x] = BLOCK_EMPTY;
    }
}

void Game093Pengo::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_PENGO_HIT) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetMaze(false);
            }
        }
        return;
    }

    if (state_ == STATE_ROUND_CLEAR) {
        if (state_timer_ > 2.0f) {
            round_++;
            ResetMaze(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetMaze(true);
        }
        return;
    }

    // STATE_PLAYING
    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateSlidingBlock(dt);
    UpdateSnoBees(dt);

    if (snobees_crushed_ >= 4) {
        state_ = STATE_ROUND_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1000;
    }
}

void Game093Pengo::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (move_cooldown_ > 0.0f) {
        move_cooldown_ -= dt;
    }

    // D-Pad Movement
    if (move_cooldown_ <= 0.0f) {
        int dx = 0, dy = 0;
        if (buttons & BTN_LEFT) { dx = -1; dy = 0; }
        else if (buttons & BTN_RIGHT) { dx = 1; dy = 0; }
        else if (buttons & BTN_UP) { dx = 0; dy = -1; }
        else if (buttons & BTN_DOWN) { dx = 0; dy = 1; }

        if (dx != 0 || dy != 0) {
            facing_x_ = dx;
            facing_y_ = dy;

            int nx = px_ + dx;
            int ny = py_ + dy;

            if (nx >= 0 && nx < GRID_SIZE && ny >= 0 && ny < GRID_SIZE) {
                if (grid_[ny][nx] == BLOCK_EMPTY) {
                    px_ = nx;
                    py_ = ny;
                    move_cooldown_ = 0.14f;
                }
            }
        }
    }

    // Button A: Push / Shatter Ice Block
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        if (!sliding_block_.active) {
            int tx = px_ + facing_x_;
            int ty = py_ + facing_y_;

            if (tx >= 0 && tx < GRID_SIZE && ty >= 0 && ty < GRID_SIZE) {
                BlockType target = grid_[ty][tx];
                if (target == BLOCK_ICE || target == BLOCK_DIAMOND) {
                    int bx = tx + facing_x_;
                    int by = ty + facing_y_;

                    if (bx >= 0 && bx < GRID_SIZE && by >= 0 && by < GRID_SIZE && grid_[by][bx] == BLOCK_EMPTY) {
                        // Launch sliding ice block!
                        sliding_block_.active = true;
                        sliding_block_.x = (float)tx;
                        sliding_block_.y = (float)ty;
                        sliding_block_.vx = (float)facing_x_ * 12.0f;
                        sliding_block_.vy = (float)facing_y_ * 12.0f;
                        sliding_block_.is_diamond = (target == BLOCK_DIAMOND);
                        grid_[ty][tx] = BLOCK_EMPTY;
                        score_ += 20;
                    } else {
                        // Obstructed behind: Shatter ice block! (Diamonds are indestructible)
                        if (target == BLOCK_ICE) {
                            grid_[ty][tx] = BLOCK_EMPTY;
                            score_ += 100;
                        }
                    }
                }
            }
        }
    }

    // Button B: Shake Perimeter Wall
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        int tx = px_ + facing_x_;
        int ty = py_ + facing_y_;

        if (tx <= 0 || tx >= 15 || ty <= 0 || ty >= 15) {
            // Wall shake! Stun all Sno-Bees adjacent to perimeter wall
            score_ += 50;
            for (int i = 0; i < MAX_SNOBEES; ++i) {
                SnoBee& b = snobees_[i];
                if (b.active) {
                    if (b.x == 1 || b.x == 14 || b.y == 1 || b.y == 14) {
                        b.stun_timer = 3.5f;
                    }
                }
            }
        }
    }
}

void Game093Pengo::UpdateSlidingBlock(float dt) {
    if (!sliding_block_.active) return;

    sliding_block_.x += sliding_block_.vx * dt;
    sliding_block_.y += sliding_block_.vy * dt;

    int cx = (int)std::round(sliding_block_.x);
    int cy = (int)std::round(sliding_block_.y);

    // 1. Check if sliding block crushes Sno-Bees
    for (int i = 0; i < MAX_SNOBEES; ++i) {
        SnoBee& b = snobees_[i];
        if (b.active) {
            float dist = std::fabs(sliding_block_.x - (float)b.x) + std::fabs(sliding_block_.y - (float)b.y);
            if (dist < 1.0f) {
                b.active = false;
                b.respawn_timer = 2.0f;
                score_ += 400; // Crushed with ice block!
                snobees_crushed_++;
            }
        }
    }

    // 2. Check collision with grid walls / other blocks ahead
    int next_x = cx + (sliding_block_.vx > 0.0f ? 1 : (sliding_block_.vx < 0.0f ? -1 : 0));
    int next_y = cy + (sliding_block_.vy > 0.0f ? 1 : (sliding_block_.vy < 0.0f ? -1 : 0));

    bool hit = false;
    if (next_x <= 0 || next_x >= 15 || next_y <= 0 || next_y >= 15) {
        hit = true;
    } else if (grid_[next_y][next_x] != BLOCK_EMPTY) {
        hit = true;
    }

    if (hit) {
        // Snap sliding block to current integer grid cell
        cx = std::clamp(cx, 1, 14);
        cy = std::clamp(cy, 1, 14);

        grid_[cy][cx] = sliding_block_.is_diamond ? BLOCK_DIAMOND : BLOCK_ICE;
        sliding_block_.active = false;

        if (sliding_block_.is_diamond) {
            CheckDiamondAlignment();
        }
    }
}

void Game093Pengo::CheckDiamondAlignment() {
    // Collect positions of the 3 diamond blocks
    int dxs[3], dys[3];
    int count = 0;

    for (int y = 1; y < 15; ++y) {
        for (int x = 1; x < 15; ++x) {
            if (grid_[y][x] == BLOCK_DIAMOND && count < 3) {
                dxs[count] = x;
                dys[count] = y;
                count++;
            }
        }
    }

    if (count == 3) {
        // Check horizontal alignment: all 3 share same y, with adjacent x
        bool horiz = (dys[0] == dys[1] && dys[1] == dys[2]) &&
                     (std::abs(dxs[0] - dxs[1]) <= 2 && std::abs(dxs[1] - dxs[2]) <= 2);

        // Check vertical alignment: all 3 share same x, with adjacent y
        bool vert = (dxs[0] == dxs[1] && dxs[1] == dxs[2]) &&
                    (std::abs(dys[0] - dys[1]) <= 2 && std::abs(dys[1] - dys[2]) <= 2);

        if (horiz || vert) {
            // Diamond Alignment Flash Bonus!
            score_ += 5000;
            for (int i = 0; i < MAX_SNOBEES; ++i) {
                if (snobees_[i].active) {
                    snobees_[i].stun_timer = 5.0f;
                }
            }
        }
    }
}

void Game093Pengo::UpdateSnoBees(float dt) {
    for (int i = 0; i < MAX_SNOBEES; ++i) {
        SnoBee& b = snobees_[i];
        if (!b.active) {
            if (b.respawn_timer > 0.0f) {
                b.respawn_timer -= dt;
            } else {
                b.active = true;
                b.stun_timer = 0.0f;
                b.x = 2 + (i * 5) % 12;
                b.y = 2;
                grid_[b.y][b.x] = BLOCK_EMPTY;
            }
            continue;
        }

        if (b.stun_timer > 0.0f) {
            b.stun_timer -= dt;
            // Stunned bees cannot move, and player can squish them directly
            if (b.x == px_ && b.y == py_) {
                b.active = false;
                b.respawn_timer = 2.0f;
                score_ += 100;
                snobees_crushed_++;
            }
            continue;
        }

        // Active Sno-Bee AI
        b.move_timer += dt;
        if (b.move_timer >= 0.28f) {
            b.move_timer = 0.0f;

            int dx = (px_ > b.x) ? 1 : ((px_ < b.x) ? -1 : 0);
            int dy = (py_ > b.y) ? 1 : ((py_ < b.y) ? -1 : 0);

            // Try primary axis
            int nx = b.x + dx;
            int ny = b.y;

            if (dx != 0 && nx >= 1 && nx <= 14 && grid_[ny][nx] == BLOCK_EMPTY) {
                b.x = nx;
            } else {
                ny = b.y + dy;
                nx = b.x;
                if (dy != 0 && ny >= 1 && ny <= 14 && grid_[ny][nx] == BLOCK_EMPTY) {
                    b.y = ny;
                }
            }

            // Check contact with Pengo
            if (b.x == px_ && b.y == py_) {
                state_ = STATE_PENGO_HIT;
                state_timer_ = 0.0f;
                break;
            }
        }
    }
}

void Game093Pengo::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Render Grid Elements
    for (int y = 0; y < GRID_SIZE; ++y) {
        for (int x = 0; x < GRID_SIZE; ++x) {
            BlockType cell = grid_[y][x];
            if (cell == BLOCK_WALL) {
                // Perimeter wall: electric blue / teal
                set_pixel(x, y, 0, 130, 240);
            } else if (cell == BLOCK_ICE) {
                // Ice cube: light cyan / crystalline white
                set_pixel(x, y, 160, 230, 255);
            } else if (cell == BLOCK_DIAMOND) {
                // Diamond block: shimmering gold / magenta
                set_pixel(x, y, 255, 215, 0);
            }
        }
    }

    // Render Sliding Block
    if (sliding_block_.active) {
        int sx = (int)std::round(sliding_block_.x);
        int sy = (int)std::round(sliding_block_.y);
        if (sliding_block_.is_diamond) {
            set_pixel(sx, sy, 255, 230, 60);
        } else {
            set_pixel(sx, sy, 220, 250, 255);
        }
    }

    // Render Sno-Bees
    for (int i = 0; i < MAX_SNOBEES; ++i) {
        const SnoBee& b = snobees_[i];
        if (!b.active) continue;

        if (b.stun_timer > 0.0f) {
            // Stunned: flashing cyan
            set_pixel(b.x, b.y, 40, 180, 255);
        } else {
            // Yellow / green bee
            set_pixel(b.x, b.y, 220, 200, 30);
        }
    }

    // Render Pengo (Red Penguin)
    if (state_ == STATE_PENGO_HIT) {
        set_pixel(px_, py_, 255, 60, 60);
        set_pixel(px_, py_ - 1, 255, 220, 0);
    } else {
        set_pixel(px_, py_, 230, 30, 30); // Red body
        // Facing beak indicator
        set_pixel(px_ + facing_x_, py_ + facing_y_, 255, 200, 0); // Yellow beak
    }

    // Top HUD
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 255, 80, 80);
    }
}

} // namespace arcade
