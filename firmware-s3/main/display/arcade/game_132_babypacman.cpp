#include "game_132_babypacman.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace arcade {

Game132BabyPacman::Game132BabyPacman() {
    Init();
}

void Game132BabyPacman::Init() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitMaze();
}

void Game132BabyPacman::Reset() {
    Init();
}

void Game132BabyPacman::InitMaze() {
    mode_ = MODE_MAZE;
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;

    px_ = 7.5f;
    py_ = 11.0f;
    p_dir_x_ = 0;
    p_dir_y_ = -1;
    next_dir_x_ = 0;
    next_dir_y_ = -1;

    frightened_timer_ = 0.0f;
    energizers_earned_ = 0;
    energizer_active_[0] = false;
    energizer_active_[1] = false;

    // Dots setup in simple maze corridors
    remaining_dots_ = 0;
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            // Corridors at y=2, y=6, y=11, and x=2, x=7, x=13
            bool is_corridor = (y == 2 || y == 6 || y == 11 || x == 2 || x == 7 || x == 13);
            if (is_corridor && (y >= 1 && y <= 13) && (x >= 1 && x <= 14)) {
                dots_[y][x] = true;
                remaining_dots_++;
            } else {
                dots_[y][x] = false;
            }
        }
    }
    // Remove center ghost house dots
    dots_[11][7] = false;
    remaining_dots_--;

    // 3 Ghosts
    ghosts_[0] = {7.5f, 5.0f, 1, 0, false, true};
    ghosts_[1] = {3.0f, 6.0f, 0, -1, false, true};
    ghosts_[2] = {12.0f, 6.0f, 0, 1, false, true};

    // Pinball targets
    for (int i = 0; i < NUM_TARGETS; ++i) {
        pinball_targets_[i] = false;
    }
}

void Game132BabyPacman::StartPinball() {
    mode_ = MODE_PINBALL;
    ball_.in_play = true;
    ball_.x = 14.0f;
    ball_.y = 12.0f;
    ball_.vx = -4.0f;
    ball_.vy = -14.0f; // Plunger launch
    left_flipper_angle_ = 0.0f;
    right_flipper_angle_ = 0.0f;
}

void Game132BabyPacman::ReturnToMaze() {
    mode_ = MODE_MAZE;
    px_ = 7.5f;
    py_ = 13.0f;
    p_dir_x_ = 0;
    p_dir_y_ = -1;

    // Apply unlocked energizers to maze!
    if (energizers_earned_ >= 1) energizer_active_[0] = true; // Top-left (2, 2)
    if (energizers_earned_ >= 2) energizer_active_[1] = true; // Top-right (13, 2)
}

void Game132BabyPacman::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & 0x0030) && !(prev_buttons & 0x0030)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DEATH) {
        if (state_timer_ > 1.3f) {
            lives_--;
            if (lives_ == 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                py_ = 11.0f;
                p_dir_x_ = 0;
                p_dir_y_ = -1;
                ghosts_[0] = {7.5f, 5.0f, 1, 0, false, true};
                ghosts_[1] = {3.0f, 6.0f, 0, -1, false, true};
                ghosts_[2] = {12.0f, 6.0f, 0, 1, false, true};
            }
        }
        return;
    }

    if (state_ == STATE_MAZE_CLEAR) {
        if (state_timer_ > 1.6f) {
            level_++;
            score_ += 1500;
            InitMaze();
        }
        return;
    }

    if (mode_ == MODE_MAZE) {
        UpdateMaze(dt, buttons);
    } else {
        UpdatePinball(dt, buttons);
    }
}

void Game132BabyPacman::UpdateMaze(float dt, uint16_t buttons) {
    if (buttons & 0x0001) { next_dir_x_ = 0; next_dir_y_ = -1; }
    if (buttons & 0x0002) { next_dir_x_ = 0; next_dir_y_ = 1; }
    if (buttons & 0x0004) { next_dir_x_ = -1; next_dir_y_ = 0; }
    if (buttons & 0x0008) { next_dir_x_ = 1; next_dir_y_ = 0; }

    if (next_dir_x_ != 0 || next_dir_y_ != 0) {
        p_dir_x_ = next_dir_x_;
        p_dir_y_ = next_dir_y_;
    }

    float speed = (frightened_timer_ > 0.0f) ? 5.8f : 5.0f;
    px_ += p_dir_x_ * speed * dt;
    py_ += p_dir_y_ * speed * dt;

    // Check Escape Tunnel to Pinball Mode:
    if (py_ >= 14.5f && std::abs(px_ - 7.5f) < 1.5f) {
        StartPinball();
        return;
    }

    // Boundary wrap
    if (px_ < 1.0f) px_ = 1.0f;
    if (px_ > 14.0f) px_ = 14.0f;
    if (py_ < 1.0f) py_ = 1.0f;
    if (py_ > 14.0f) py_ = 14.0f;

    // Eat dots
    int ix = (int)std::round(px_);
    int iy = (int)std::round(py_);
    if (ix >= 0 && ix < 16 && iy >= 0 && iy < 16) {
        if (dots_[iy][ix]) {
            dots_[iy][ix] = false;
            score_ += 10;
            remaining_dots_--;
        }
    }

    // Eat Energizers if unlocked
    if (energizer_active_[0] && std::abs(px_ - 2.0f) < 0.8f && std::abs(py_ - 2.0f) < 0.8f) {
        energizer_active_[0] = false;
        frightened_timer_ = 6.0f;
        score_ += 50;
    }
    if (energizer_active_[1] && std::abs(px_ - 13.0f) < 0.8f && std::abs(py_ - 2.0f) < 0.8f) {
        energizer_active_[1] = false;
        frightened_timer_ = 6.0f;
        score_ += 50;
    }

    if (frightened_timer_ > 0.0f) frightened_timer_ -= dt;

    // Update ghosts
    for (int g = 0; g < NUM_GHOSTS; ++g) {
        ghosts_[g].frightened = (frightened_timer_ > 0.0f);
        float g_speed = ghosts_[g].frightened ? 2.5f : (4.0f + level_ * 0.2f);
        ghosts_[g].x += ghosts_[g].dir_x * g_speed * dt;
        ghosts_[g].y += ghosts_[g].dir_y * g_speed * dt;

        // Bounce walls
        if (ghosts_[g].x < 2.0f) { ghosts_[g].x = 2.0f; ghosts_[g].dir_x = 1; }
        if (ghosts_[g].x > 13.0f) { ghosts_[g].x = 13.0f; ghosts_[g].dir_x = -1; }
        if (ghosts_[g].y < 2.0f) { ghosts_[g].y = 2.0f; ghosts_[g].dir_y = 1; }
        if (ghosts_[g].y > 11.0f) { ghosts_[g].y = 11.0f; ghosts_[g].dir_y = -1; }
    }

    CheckMazeCollisions();

    if (remaining_dots_ <= 0) {
        state_ = STATE_MAZE_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game132BabyPacman::CheckMazeCollisions() {
    for (int g = 0; g < NUM_GHOSTS; ++g) {
        float dx = std::abs(px_ - ghosts_[g].x);
        float dy = std::abs(py_ - ghosts_[g].y);
        if (dx < 0.8f && dy < 0.8f) {
            if (ghosts_[g].frightened) {
                // Eat ghost!
                ghosts_[g].x = 7.5f;
                ghosts_[g].y = 6.0f;
                ghosts_[g].frightened = false;
                score_ += 200;
            } else {
                // Caught by ghost!
                state_ = STATE_DEATH;
                state_timer_ = 0.0f;
                break;
            }
        }
    }
}

void Game132BabyPacman::UpdatePinball(float dt, uint16_t buttons) {
    // Gravity & Velocity
    ball_.vy += 16.0f * dt;
    ball_.vx *= 0.99f;
    ball_.x += ball_.vx * dt;
    ball_.y += ball_.vy * dt;

    // Left Flipper (KEY_LEFT or KEY_A)
    bool left_flip = (buttons & 0x0014) != 0;
    // Right Flipper (KEY_RIGHT or KEY_B)
    bool right_flip = (buttons & 0x0028) != 0;

    // Flipper collisions at y in [13.0, 14.5]
    if (ball_.y >= 13.0f && ball_.y <= 14.5f) {
        if (left_flip && ball_.x >= 2.0f && ball_.x <= 6.5f) {
            ball_.vy = -13.0f;
            ball_.vx += 3.5f;
            score_ += 20;
        }
        if (right_flip && ball_.x >= 8.5f && ball_.x <= 13.0f) {
            ball_.vy = -13.0f;
            ball_.vx -= 3.5f;
            score_ += 20;
        }
    }

    // Side walls bounce
    if (ball_.x <= 1.5f) { ball_.x = 1.5f; ball_.vx = -ball_.vx * 0.85f; }
    if (ball_.x >= 14.5f) { ball_.x = 14.5f; ball_.vx = -ball_.vx * 0.85f; }
    if (ball_.y <= 1.5f) { ball_.y = 1.5f; ball_.vy = -ball_.vy * 0.85f; }

    // Bumpers at (5.0, 7.0) and (10.0, 7.0)
    float b1_dx = ball_.x - 5.0f;
    float b1_dy = ball_.y - 7.0f;
    if (std::sqrt(b1_dx * b1_dx + b1_dy * b1_dy) < 1.3f) {
        ball_.vx += (b1_dx > 0 ? 5.0f : -5.0f);
        ball_.vy = -8.0f;
        score_ += 50;
    }
    float b2_dx = ball_.x - 10.0f;
    float b2_dy = ball_.y - 7.0f;
    if (std::sqrt(b2_dx * b2_dx + b2_dy * b2_dy) < 1.3f) {
        ball_.vx += (b2_dx > 0 ? 5.0f : -5.0f);
        ball_.vy = -8.0f;
        score_ += 50;
    }

    // Drop targets at y=3.0: x=4.0, x=7.5, x=11.0
    float target_x[3] = {4.0f, 7.5f, 11.0f};
    for (int t = 0; t < 3; ++t) {
        if (!pinball_targets_[t]) {
            if (std::abs(ball_.y - 3.0f) < 0.8f && std::abs(ball_.x - target_x[t]) < 0.9f) {
                pinball_targets_[t] = true;
                ball_.vy = 4.0f; // Bounce down
                score_ += 100;
                energizers_earned_++;
            }
        }
    }

    // Ball drain at bottom -> Return to maze!
    if (ball_.y >= 15.5f) {
        ReturnToMaze();
    }
}

void Game132BabyPacman::Render(uint8_t* fb) {
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

    if (mode_ == MODE_MAZE) {
        // 1. Maze blue walls & dots
        for (int y = 0; y < 16; ++y) {
            for (int x = 0; x < 16; ++x) {
                if (dots_[y][x]) {
                    set_pixel(x, y, 255, 180, 160); // Dots
                }
            }
        }

        // 2. Unlocked Energizers
        if (energizer_active_[0]) {
            set_pixel(2, 2, 255, 255, 255); // Flashing power pellet
            set_pixel(2, 3, 255, 220, 50);
        }
        if (energizer_active_[1]) {
            set_pixel(13, 2, 255, 255, 255);
            set_pixel(13, 3, 255, 220, 50);
        }

        // 3. Escape tunnel to pinball marker at (7, 14)-(8, 14)
        set_pixel(7, 14, 0, 255, 200);
        set_pixel(8, 14, 0, 255, 200);

        // 4. Ghosts
        for (int g = 0; g < NUM_GHOSTS; ++g) {
            int gx = (int)std::round(ghosts_[g].x);
            int gy = (int)std::round(ghosts_[g].y);
            if (ghosts_[g].frightened) {
                set_pixel(gx, gy, 40, 60, 255); // Frightened dark blue
                set_pixel(gx, gy - 1, 255, 255, 255);
            } else {
                if (g == 0) set_pixel(gx, gy, 255, 40, 40);      // Blinky Red
                else if (g == 1) set_pixel(gx, gy, 255, 120, 200); // Pinky
                else set_pixel(gx, gy, 40, 220, 255);             // Inky Cyan
            }
        }

        // 5. Baby Pac-Man (Yellow body with pink bow)
        int px_s = (int)std::round(px_);
        int py_s = (int)std::round(py_);
        set_pixel(px_s, py_s, 255, 255, 0);     // Pac-Man yellow
        set_pixel(px_s, py_s - 1, 255, 100, 180); // Baby bow pink
    } else {
        // MODE_PINBALL
        // 1. Table boundaries
        for (int p = 0; p < 16; ++p) {
            set_pixel(1, p, 100, 40, 20);
            set_pixel(14, p, 100, 40, 20);
            set_pixel(p, 1, 100, 40, 20);
        }

        // 2. Drop targets
        float target_x[3] = {4.0f, 7.5f, 11.0f};
        for (int t = 0; t < 3; ++t) {
            int tx = (int)std::round(target_x[t]);
            if (!pinball_targets_[t]) {
                set_pixel(tx, 3, 255, 220, 0); // Energizer Target Yellow
            } else {
                set_pixel(tx, 3, 60, 60, 60);  // Knocked down
            }
        }

        // 3. Bumpers
        set_pixel(5, 7, 255, 40, 60);
        set_pixel(10, 7, 255, 40, 60);

        // 4. Flippers
        for (int x = 3; x <= 6; ++x) set_pixel(x, 14, 0, 220, 255);
        for (int x = 9; x <= 12; ++x) set_pixel(x, 14, 0, 220, 255);

        // 5. Silver Steel Ball
        int bx = (int)std::round(ball_.x);
        int by = (int)std::round(ball_.y);
        set_pixel(bx, by, 255, 255, 255);
    }

    // Lives
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l * 2, 0, 255, 255, 0);
    }
}

} // namespace arcade
