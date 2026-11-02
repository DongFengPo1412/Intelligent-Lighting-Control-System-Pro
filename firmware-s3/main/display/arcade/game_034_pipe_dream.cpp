#include "game_034_pipe_dream.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

// Directions: 0: Up, 1: Right, 2: Down, 3: Left
static const int DX[4] = {0, 1, 0, -1};
static const int DY[4] = {-1, 0, 1, 0};

Game034PipeDream::Game034PipeDream()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      pipes_filled_(0),
      required_pipes_(8),
      cursor_x_(2),
      cursor_y_(2),
      flow_start_countdown_(6.0f),
      flow_step_timer_(0.0f),
      flow_step_interval_(1.0f),
      flow_x_(1),
      flow_y_(1),
      flow_dir_(1),
      flow_started_(false) {
}

void Game034PipeDream::Init() {
    Reset();
}

void Game034PipeDream::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    pipes_filled_ = 0;
    required_pipes_ = 8;
    cursor_x_ = 2;
    cursor_y_(2);
    flow_start_countdown_ = 6.0f;
    flow_step_timer_ = 0.0f;
    flow_step_interval_ = 1.0f;
    flow_started_ = false;

    InitBoard();
}

Game034PipeDream::PipeType Game034PipeDream::GenerateRandomPipe() {
    // Random between HORIZ(1) and CROSS(7)
    int r = 1 + (rand() % 7);
    return static_cast<PipeType>(r);
}

void Game034PipeDream::PushQueue() {
    for (int i = 0; i < QUEUE_SIZE - 1; ++i) {
        pipe_queue_[i] = pipe_queue_[i + 1];
    }
    pipe_queue_[QUEUE_SIZE - 1] = GenerateRandomPipe();
}

void Game034PipeDream::InitBoard() {
    for (int y = 0; y < GRID_H; ++y) {
        for (int x = 0; x < GRID_W; ++x) {
            grid_[y][x].pipe = PIPE_EMPTY;
            grid_[y][x].filled = false;
            grid_[y][x].cross_h_filled = false;
            grid_[y][x].cross_v_filled = false;
        }
    }

    // Source tap at (1, 1), pointing Right
    flow_x_ = 1;
    flow_y_ = 1;
    flow_dir_ = 1; // Right
    grid_[flow_y_][flow_x_].pipe = PIPE_START;
    grid_[flow_y_][flow_x_].filled = true;

    // Drain tap at (6, 6)
    grid_[6][6].pipe = PIPE_END;
    grid_[6][6].filled = false;

    // Initialize pipe queue
    for (int i = 0; i < QUEUE_SIZE; ++i) {
        pipe_queue_[i] = GenerateRandomPipe();
    }
}

bool Game034PipeDream::CanConnect(PipeType pipe, int enter_dir, int& exit_dir) const {
    switch (pipe) {
        case PIPE_HORIZ:
            if (enter_dir == 1) { exit_dir = 1; return true; }
            if (enter_dir == 3) { exit_dir = 3; return true; }
            return false;

        case PIPE_VERT:
            if (enter_dir == 0) { exit_dir = 0; return true; }
            if (enter_dir == 2) { exit_dir = 2; return true; }
            return false;

        case PIPE_CORNER_UR: // Up <-> Right
            if (enter_dir == 2) { exit_dir = 1; return true; } // From Top -> Turn Right
            if (enter_dir == 3) { exit_dir = 0; return true; } // From Right -> Turn Up
            return false;

        case PIPE_CORNER_RD: // Right <-> Down
            if (enter_dir == 0) { exit_dir = 1; return true; } // From Bottom -> Turn Right
            if (enter_dir == 3) { exit_dir = 2; return true; } // From Right -> Turn Down
            return false;

        case PIPE_CORNER_DL: // Down <-> Left
            if (enter_dir == 0) { exit_dir = 3; return true; } // From Bottom -> Turn Left
            if (enter_dir == 1) { exit_dir = 2; return true; } // From Left -> Turn Down
            return false;

        case PIPE_CORNER_LU: // Left <-> Up
            if (enter_dir == 2) { exit_dir = 3; return true; } // From Top -> Turn Left
            if (enter_dir == 1) { exit_dir = 0; return true; } // From Left -> Turn Up
            return false;

        case PIPE_CROSS:
            exit_dir = enter_dir; // Passes straight through
            return true;

        case PIPE_END:
            exit_dir = enter_dir;
            return true;

        default:
            return false;
    }
}

bool Game034PipeDream::PlacePipe() {
    // Cannot replace filled pipe or start/end taps
    Cell& c = grid_[cursor_y_][cursor_x_];
    if (c.filled || c.pipe == PIPE_START || c.pipe == PIPE_END) {
        return false;
    }

    c.pipe = pipe_queue_[0];
    PushQueue();
    return true;
}

void Game034PipeDream::FastForwardFlow() {
    if (flow_started_) {
        flow_step_interval_ = 0.2f; // Fast forward
    } else {
        flow_start_countdown_ = 0.0f; // Start immediately
    }
}

void Game034PipeDream::AdvanceFlow() {
    int nx = flow_x_ + DX[flow_dir_];
    int ny = flow_y_ + DY[flow_dir_];

    // Check bounds
    if (nx < 0 || nx >= GRID_W || ny < 0 || ny >= GRID_H) {
        // Spill out of bounds!
        state_ = STATE_DEAD;
        state_timer_ = 0.0f;
        return;
    }

    Cell& target = grid_[ny][nx];
    int next_dir = 0;

    if (!CanConnect(target.pipe, flow_dir_, next_dir)) {
        // Spill / Leak!
        state_ = STATE_DEAD;
        state_timer_ = 0.0f;
        return;
    }

    // Check if re-entering an already filled pipe (unless cross intersection on perpendicular path)
    if (target.filled) {
        if (target.pipe == PIPE_CROSS) {
            bool is_horiz = (flow_dir_ == 1 || flow_dir_ == 3);
            if ((is_horiz && target.cross_h_filled) || (!is_horiz && target.cross_v_filled)) {
                // Re-filled same axis: collision!
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        } else {
            // Already filled pipe: loop crash!
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }

    // Flow enters successfully
    flow_x_ = nx;
    flow_y_ = ny;
    flow_dir_ = next_dir;
    pipes_filled_++;

    if (target.pipe == PIPE_CROSS) {
        bool is_horiz = (flow_dir_ == 1 || flow_dir_ == 3);
        if (is_horiz) target.cross_h_filled = true;
        else target.cross_v_filled = true;

        if (target.cross_h_filled && target.cross_v_filled) {
            score_ += 400; // Double cross bonus!
        } else {
            score_ += 100;
        }
        target.filled = true;
    } else if (target.pipe == PIPE_END) {
        target.filled = true;
        // Reach drain!
        if (pipes_filled_ >= required_pipes_) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            score_ += 1000 + pipes_filled_ * 100;
        } else {
            // Reached drain too early
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
        }
        if (score_ > high_score_) high_score_ = score_;
        return;
    } else {
        target.filled = true;
        score_ += 100;
    }

    if (score_ > high_score_) high_score_ = score_;
}

void Game034PipeDream::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DEAD || state_ == STATE_VICTORY) {
        if (state_timer_ >= 2.0f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    // 1. Cursor controls
    if ((buttons & KEY_LEFT) && !(prev_buttons & KEY_LEFT)) {
        if (cursor_x_ > 0) cursor_x_--;
    } else if ((buttons & KEY_RIGHT) && !(prev_buttons & KEY_RIGHT)) {
        if (cursor_x_ < GRID_W - 1) cursor_x_++;
    } else if ((buttons & KEY_UP) && !(prev_buttons & KEY_UP)) {
        if (cursor_y_ > 0) cursor_y_--;
    } else if ((buttons & KEY_DOWN) && !(prev_buttons & KEY_DOWN)) {
        if (cursor_y_ < GRID_H - 1) cursor_y_++;
    }

    // 2. Button A: Place Pipe
    if ((buttons & KEY_A) && !(prev_buttons & KEY_A)) {
        PlacePipe();
    }

    // 3. Button B: Fast forward
    if ((buttons & KEY_B) && !(prev_buttons & KEY_B)) {
        FastForwardFlow();
    }

    // 4. Fluid flow countdown and advance
    if (!flow_started_) {
        flow_start_countdown_ = std::max(0.0f, flow_start_countdown_ - dt);
        if (flow_start_countdown_ <= 0.0f) {
            flow_started_ = true;
            flow_step_timer_ = 0.0f;
        }
    } else {
        flow_step_timer_ += dt;
        if (flow_step_timer_ >= flow_step_interval_) {
            flow_step_timer_ = 0.0f;
            AdvanceFlow();
        }
    }
}

void Game034PipeDream::Render(uint8_t* fb) {
    // Clear background to Dark Slate Industrial (#1E272C)
    for (int i = 0; i < 256; ++i) {
        fb[i * 3 + 0] = 30;
        fb[i * 3 + 1] = 39;
        fb[i * 3 + 2] = 46;
    }

    // 1. Render 8x8 Grid (each cell is 2x2 pixels)
    for (int cy = 0; cy < GRID_H; ++cy) {
        for (int cx = 0; cx < GRID_W; ++cx) {
            const Cell& c = grid_[cy][cx];
            int px0 = cx * 2;
            int py0 = cy * 2;

            if (c.pipe == PIPE_EMPTY) continue;

            // Default Pipe Color: Metallic Silver #95A5A6
            uint8_t pr = 149, pg = 165, pb = 166;
            if (c.filled) {
                // Neon Glowing Green Flooz #2ECC71
                pr = 46; pg = 204; pb = 113;
            }

            if (c.pipe == PIPE_START) {
                // Green Source Tap
                pr = 0; pg = 255; pb = 128;
            } else if (c.pipe == PIPE_END) {
                // Amber Drain Tap
                pr = 243; pg = 156; pb = 18;
            }

            // Draw 2x2 pattern according to pipe type
            switch (c.pipe) {
                case PIPE_HORIZ:
                case PIPE_START:
                    // Horizontal 2x2: top row filled
                    for (int dx = 0; dx < 2; ++dx) {
                        int idx = ((py0) * 16 + (px0 + dx)) * 3;
                        fb[idx + 0] = pr; fb[idx + 1] = pg; fb[idx + 2] = pb;
                    }
                    break;

                case PIPE_VERT:
                    // Vertical 2x2: left column filled
                    for (int dy = 0; dy < 2; ++dy) {
                        int idx = ((py0 + dy) * 16 + (px0)) * 3;
                        fb[idx + 0] = pr; fb[idx + 1] = pg; fb[idx + 2] = pb;
                    }
                    break;

                case PIPE_CORNER_UR:
                    fb[((py0) * 16 + px0) * 3 + 0] = pr; fb[((py0) * 16 + px0) * 3 + 1] = pg; fb[((py0) * 16 + px0) * 3 + 2] = pb;
                    fb[((py0) * 16 + px0 + 1) * 3 + 0] = pr; fb[((py0) * 16 + px0 + 1) * 3 + 1] = pg; fb[((py0) * 16 + px0 + 1) * 3 + 2] = pb;
                    break;

                case PIPE_CORNER_RD:
                    fb[((py0) * 16 + px0 + 1) * 3 + 0] = pr; fb[((py0) * 16 + px0 + 1) * 3 + 1] = pg; fb[((py0) * 16 + px0 + 1) * 3 + 2] = pb;
                    fb[((py0 + 1) * 16 + px0 + 1) * 3 + 0] = pr; fb[((py0 + 1) * 16 + px0 + 1) * 3 + 1] = pg; fb[((py0 + 1) * 16 + px0 + 1) * 3 + 2] = pb;
                    break;

                case PIPE_CORNER_DL:
                    fb[((py0 + 1) * 16 + px0) * 3 + 0] = pr; fb[((py0 + 1) * 16 + px0) * 3 + 1] = pg; fb[((py0 + 1) * 16 + px0) * 3 + 2] = pb;
                    fb[((py0 + 1) * 16 + px0 + 1) * 3 + 0] = pr; fb[((py0 + 1) * 16 + px0 + 1) * 3 + 1] = pg; fb[((py0 + 1) * 16 + px0 + 1) * 3 + 2] = pb;
                    break;

                case PIPE_CORNER_LU:
                    fb[((py0) * 16 + px0) * 3 + 0] = pr; fb[((py0) * 16 + px0) * 3 + 1] = pg; fb[((py0) * 16 + px0) * 3 + 2] = pb;
                    fb[((py0 + 1) * 16 + px0) * 3 + 0] = pr; fb[((py0 + 1) * 16 + px0) * 3 + 1] = pg; fb[((py0 + 1) * 16 + px0) * 3 + 2] = pb;
                    break;

                case PIPE_CROSS:
                case PIPE_END:
                default:
                    for (int dy = 0; dy < 2; ++dy) {
                        for (int dx = 0; dx < 2; ++dx) {
                            int idx = ((py0 + dy) * 16 + (px0 + dx)) * 3;
                            fb[idx + 0] = pr; fb[idx + 1] = pg; fb[idx + 2] = pb;
                        }
                    }
                    break;
            }
        }
    }

    // 2. Render Selection Cursor (Blinking Cyan Frame)
    bool blink = (static_cast<int>(state_timer_ * 6.0f) % 2 == 0);
    if (blink) {
        int cur_px = cursor_x_ * 2;
        int cur_py = cursor_y_ * 2;
        for (int dy = 0; dy < 2; ++dy) {
            for (int dx = 0; dx < 2; ++dx) {
                int idx = ((cur_py + dy) * 16 + (cur_px + dx)) * 3;
                fb[idx + 0] = 52; fb[idx + 1] = 152; fb[idx + 2] = 219;
            }
        }
    }

    // 3. Render Next Queued Pipe Preview on bottom-right corner or HUD indicator
    int q_px = 14;
    int q_py = 14;
    int q_idx = (q_py * 16 + q_px) * 3;
    fb[q_idx + 0] = 241; fb[q_idx + 1] = 196; fb[q_idx + 2] = 15; // Yellow preview dot
}

} // namespace arcade
