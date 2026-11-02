#include "game_105_arkanoid.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game105Arkanoid::Game105Arkanoid() {
    Reset();
}

void Game105Arkanoid::Init() {
    Reset();
}

void Game105Arkanoid::Reset() {
    score_ = 0;
    lives_ = 3;
    round_ = 1;
    InitBricks();
    ResetBall();
}

void Game105Arkanoid::InitBricks() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    bricks_remaining_ = 0;
    active_powerup_ = CAPSULE_NONE;
    paddle_width_ = 3;
    laser_cooldown_ = 0.0f;

    for (int i = 0; i < MAX_CAPSULES; ++i) {
        capsules_[i].active = false;
    }
    for (int i = 0; i < MAX_LASERS; ++i) {
        lasers_[i].active = false;
    }

    // Standard Arkanoid brick colors:
    // Row 0: Silver (2 hits), Row 1: Red, Row 2: Yellow, Row 3: Blue, Row 4: Green
    for (int r = 0; r < BRICK_ROWS; ++r) {
        for (int c = 0; c < BRICK_COLS; ++c) {
            if (r == 0) bricks_[r][c] = 9; // Silver
            else if (r == 1) bricks_[r][c] = 1; // Red
            else if (r == 2) bricks_[r][c] = 2; // Yellow
            else if (r == 3) bricks_[r][c] = 3; // Blue
            else bricks_[r][c] = 4; // Green
            bricks_remaining_++;
        }
    }
}

void Game105Arkanoid::ResetBall() {
    paddle_x_ = 6.5f;
    ball_x_ = 7.5f;
    ball_y_ = 14.0f;
    ball_vx_ = 3.5f;
    ball_vy_ = -6.0f;
    ball_caught_ = true; // Caught on paddle at launch
    ball_catch_offset_ = 0.5f;
}

void Game105Arkanoid::SetPowerup(CapsuleType type) {
    active_powerup_ = type;
    if (type == CAPSULE_ENLARGE) {
        paddle_width_ = 5;
    } else {
        paddle_width_ = 3;
    }

    if (type == CAPSULE_SLOW) {
        ball_vx_ *= 0.6f;
        ball_vy_ *= 0.6f;
    }
}

void Game105Arkanoid::SpawnBossDoh() {
    state_ = STATE_BOSS_DOH;
    state_timer_ = 0.0f;
    doh_hp_ = 12;
    doh_x_ = 6.0f;
    doh_vx_ = 2.5f;

    for (int r = 0; r < BRICK_ROWS; ++r) {
        for (int c = 0; c < BRICK_COLS; ++c) {
            bricks_[r][c] = 0;
        }
    }
    bricks_remaining_ = 0;
}

void Game105Arkanoid::SpawnCapsule(float x, float y) {
    for (int i = 0; i < MAX_CAPSULES; ++i) {
        if (!capsules_[i].active) {
            capsules_[i].active = true;
            capsules_[i].x = x;
            capsules_[i].y = y;
            // Cycle between Laser, Enlarge, Catch, Slow, Break
            static int cap_cycle = 0;
            capsules_[i].type = static_cast<CapsuleType>((cap_cycle++ % 5) + 1);
            break;
        }
    }
}

void Game105Arkanoid::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_BALL_LOST) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                active_powerup_ = CAPSULE_NONE;
                paddle_width_ = 3;
                ResetBall();
            }
        }
        return;
    }

    if (state_ == STATE_ROUND_CLEAR) {
        if (state_timer_ > 2.2f) {
            round_++;
            if (round_ >= 2) {
                SpawnBossDoh();
            } else {
                InitBricks();
                ResetBall();
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    UpdatePaddle(dt, buttons, prev_buttons);
    UpdateBall(dt);
    UpdateCapsules(dt);
    UpdateLasers(dt);

    if (state_ == STATE_BOSS_DOH) {
        UpdateBossDoh(dt);
    } else {
        CheckBallBrickCollision();
        CheckLaserBrickCollision();

        if (bricks_remaining_ <= 0 && state_ != STATE_ROUND_CLEAR) {
            state_ = STATE_ROUND_CLEAR;
            state_timer_ = 0.0f;
            score_ += 1000;
        }
    }
}

void Game105Arkanoid::UpdatePaddle(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_spd = 12.0f;
    if (buttons & BTN_LEFT) {
        paddle_x_ = std::max(1.0f, paddle_x_ - move_spd * dt);
    }
    if (buttons & BTN_RIGHT) {
        float max_x = 15.0f - static_cast<float>(paddle_width_);
        paddle_x_ = std::min(max_x, paddle_x_ + move_spd * dt);
    }

    // Button A: Release caught ball or fire laser
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        if (ball_caught_) {
            ball_caught_ = false;
            ball_vy_ = -6.5f;
            ball_vx_ = (ball_catch_offset_ / (static_cast<float>(paddle_width_) * 0.5f)) * 4.5f;
        } else if (active_powerup_ == CAPSULE_LASER && laser_cooldown_ <= 0.0f) {
            laser_cooldown_ = 0.25f;
            // Spawn 2 laser bolts from paddle wings
            for (int i = 0; i < MAX_LASERS - 1; i += 2) {
                if (!lasers_[i].active && !lasers_[i + 1].active) {
                    lasers_[i].active = true;
                    lasers_[i].x = paddle_x_;
                    lasers_[i].y = 14.0f;
                    lasers_[i + 1].active = true;
                    lasers_[i + 1].x = paddle_x_ + static_cast<float>(paddle_width_ - 1);
                    lasers_[i + 1].y = 14.0f;
                    break;
                }
            }
        }
    }
    laser_cooldown_ -= dt;
}

void Game105Arkanoid::UpdateBall(float dt) {
    if (ball_caught_) {
        ball_x_ = paddle_x_ + ball_catch_offset_;
        ball_y_ = 14.0f;
        return;
    }

    ball_x_ += ball_vx_ * dt;
    ball_y_ += ball_vy_ * dt;

    // Side wall bounce (left=1.0, right=14.0)
    if (ball_x_ <= 1.0f) {
        ball_x_ = 1.0f;
        ball_vx_ = std::abs(ball_vx_);
    } else if (ball_x_ >= 14.0f) {
        ball_x_ = 14.0f;
        ball_vx_ = -std::abs(ball_vx_);
    }

    // Ceiling bounce (top=1.0)
    if (ball_y_ <= 1.0f) {
        ball_y_ = 1.0f;
        ball_vy_ = std::abs(ball_vy_);
    }

    // Bottom loss
    if (ball_y_ >= 15.5f) {
        state_ = STATE_BALL_LOST;
        state_timer_ = 0.0f;
        return;
    }

    CheckBallPaddleCollision();
}

void Game105Arkanoid::CheckBallPaddleCollision() {
    if (ball_vy_ > 0.0f && ball_y_ >= 14.2f && ball_y_ <= 15.2f) {
        float rel_x = ball_x_ - paddle_x_;
        if (rel_x >= -0.4f && rel_x <= static_cast<float>(paddle_width_) + 0.4f) {
            // Hit paddle!
            if (active_powerup_ == CAPSULE_CATCH) {
                ball_caught_ = true;
                ball_catch_offset_ = std::max(0.0f, std::min(static_cast<float>(paddle_width_ - 1), rel_x));
                return;
            }

            // Normal reflection
            ball_vy_ = -std::abs(ball_vy_);
            float center_diff = rel_x - (static_cast<float>(paddle_width_) * 0.5f);
            ball_vx_ = center_diff * 4.0f;
            if (std::abs(ball_vx_) < 1.0f) {
                ball_vx_ = (ball_vx_ >= 0.0f) ? 1.5f : -1.5f;
            }
        }
    }
}

void Game105Arkanoid::CheckBallBrickCollision() {
    // Brick dimensions: Each column is 2 pixels wide (cols 0..6 -> x in [1, 14])
    // Rows 0..4 -> y in [2, 6]
    int r = static_cast<int>(ball_y_) - 2;
    int c = (static_cast<int>(ball_x_) - 1) / 2;

    if (r >= 0 && r < BRICK_ROWS && c >= 0 && c < BRICK_COLS) {
        if (bricks_[r][c] != 0) {
            // Hit brick!
            ball_vy_ = -ball_vy_;

            if (bricks_[r][c] == 9) {
                // Silver brick takes 2 hits
                bricks_[r][c] = 1;
                score_ += 50;
            } else {
                bricks_[r][c] = 0;
                bricks_remaining_--;
                score_ += 100;

                // Chance to drop capsule
                if ((r + c) % 3 == 0) {
                    SpawnCapsule(static_cast<float>(c * 2 + 2), static_cast<float>(r + 2));
                }
            }
        }
    }
}

void Game105Arkanoid::CheckLaserBrickCollision() {
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) continue;
        int r = static_cast<int>(lasers_[i].y) - 2;
        int c = (static_cast<int>(lasers_[i].x) - 1) / 2;

        if (r >= 0 && r < BRICK_ROWS && c >= 0 && c < BRICK_COLS) {
            if (bricks_[r][c] != 0) {
                lasers_[i].active = false;
                if (bricks_[r][c] == 9) {
                    bricks_[r][c] = 1;
                } else {
                    bricks_[r][c] = 0;
                    bricks_remaining_--;
                }
                score_ += 80;
            }
        }
    }
}

void Game105Arkanoid::UpdateCapsules(float dt) {
    for (int i = 0; i < MAX_CAPSULES; ++i) {
        if (!capsules_[i].active) continue;
        capsules_[i].y += 4.0f * dt;

        // Catch capsule on paddle
        if (capsules_[i].y >= 14.5f && capsules_[i].y <= 15.5f) {
            if (capsules_[i].x >= paddle_x_ - 0.5f &&
                capsules_[i].x <= paddle_x_ + static_cast<float>(paddle_width_) + 0.5f) {
                capsules_[i].active = false;
                score_ += 500;
                if (capsules_[i].type == CAPSULE_BREAK) {
                    // Warp to next round / Boss Doh
                    state_ = STATE_ROUND_CLEAR;
                    state_timer_ = 0.0f;
                } else {
                    SetPowerup(capsules_[i].type);
                }
                continue;
            }
        }

        if (capsules_[i].y > 16.0f) {
            capsules_[i].active = false;
        }
    }
}

void Game105Arkanoid::UpdateLasers(float dt) {
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) continue;
        lasers_[i].y -= 20.0f * dt;
        if (lasers_[i].y < 1.0f) {
            lasers_[i].active = false;
        }
    }
}

void Game105Arkanoid::UpdateBossDoh(float dt) {
    doh_x_ += doh_vx_ * dt;
    if (doh_x_ <= 3.0f) {
        doh_x_ = 3.0f;
        doh_vx_ = std::abs(doh_vx_);
    } else if (doh_x_ >= 9.0f) {
        doh_x_ = 9.0f;
        doh_vx_ = -std::abs(doh_vx_);
    }

    // Ball vs Doh Moai head (size 5x4 at doh_x, y=2..5)
    if (ball_y_ >= 2.0f && ball_y_ <= 5.5f) {
        if (ball_x_ >= doh_x_ - 0.5f && ball_x_ <= doh_x_ + 5.0f) {
            ball_vy_ = std::abs(ball_vy_);
            doh_hp_--;
            score_ += 200;
            if (doh_hp_ <= 0) {
                state_ = STATE_ROUND_CLEAR;
                state_timer_ = 0.0f;
                score_ += 5000; // Defeated Doh!
            }
        }
    }

    // Laser vs Doh
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) continue;
        if (lasers_[i].y >= 2.0f && lasers_[i].y <= 5.5f) {
            if (lasers_[i].x >= doh_x_ && lasers_[i].x <= doh_x_ + 5.0f) {
                lasers_[i].active = false;
                doh_hp_--;
                score_ += 100;
                if (doh_hp_ <= 0) {
                    state_ = STATE_ROUND_CLEAR;
                    state_timer_ = 0.0f;
                    score_ += 5000;
                }
            }
        }
    }
}

void Game105Arkanoid::Render(uint8_t* fb) {
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

    // Steel Barrier Walls (left=0, right=15, top=0)
    for (int y = 0; y < 16; ++y) {
        set_pixel(0, y, 160, 160, 180);
        set_pixel(15, y, 160, 160, 180);
    }
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 0, 160, 160, 180);
    }

    // Bricks
    for (int r = 0; r < BRICK_ROWS; ++r) {
        for (int c = 0; c < BRICK_COLS; ++c) {
            uint8_t b = bricks_[r][c];
            if (b != 0) {
                int bx = 1 + c * 2;
                int by = 2 + r;
                uint8_t br = 200, bg = 40, bb = 40;
                if (b == 9) { br = 210; bg = 210; bb = 220; } // Silver
                else if (b == 2) { br = 240; bg = 200; bb = 20; } // Yellow
                else if (b == 3) { br = 40;  bg = 100; bb = 240; } // Blue
                else if (b == 4) { br = 30;  bg = 200; bb = 50; } // Green

                set_pixel(bx, by, br, bg, bb);
                set_pixel(bx + 1, by, br, bg, bb);
            }
        }
    }

    // Boss Doh (Moai Idol)
    if (state_ == STATE_BOSS_DOH) {
        int dx = static_cast<int>(std::round(doh_x_));
        for (int y = 2; y <= 5; ++y) {
            for (int x = dx; x < dx + 4; ++x) {
                set_pixel(x, y, 180, 140, 100);
            }
        }
        // Glowing red eyes
        set_pixel(dx + 1, 3, 255, 30, 20);
        set_pixel(dx + 2, 3, 255, 30, 20);
    }

    // Falling Energy Capsules
    for (int i = 0; i < MAX_CAPSULES; ++i) {
        if (!capsules_[i].active) continue;
        int cx = static_cast<int>(std::round(capsules_[i].x));
        int cy = static_cast<int>(std::round(capsules_[i].y));
        uint8_t cr = 255, cg = 255, cb = 255;
        if (capsules_[i].type == CAPSULE_LASER) { cr = 255; cg = 40; cb = 40; }
        else if (capsules_[i].type == CAPSULE_ENLARGE) { cr = 40; cg = 120; cb = 255; }
        else if (capsules_[i].type == CAPSULE_CATCH) { cr = 40; cg = 220; cb = 60; }
        else if (capsules_[i].type == CAPSULE_SLOW) { cr = 255; cg = 160; cb = 20; }
        else if (capsules_[i].type == CAPSULE_BREAK) { cr = 220; cg = 40; cb = 220; }

        set_pixel(cx, cy, cr, cg, cb);
        set_pixel(cx + 1, cy, cr, cg, cb);
    }

    // Lasers
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) continue;
        int lx = static_cast<int>(std::round(lasers_[i].x));
        int ly = static_cast<int>(std::round(lasers_[i].y));
        set_pixel(lx, ly, 255, 40, 40);
        set_pixel(lx, ly + 1, 255, 180, 40);
    }

    // Energy Ball
    int bx = static_cast<int>(std::round(ball_x_));
    int by = static_cast<int>(std::round(ball_y_));
    set_pixel(bx, by, 255, 255, 255);

    // Vaus Paddle at y=15
    int px = static_cast<int>(std::round(paddle_x_));
    for (int i = 0; i < paddle_width_; ++i) {
        if (active_powerup_ == CAPSULE_LASER) {
            set_pixel(px + i, 15, 255, 40, 40); // Red laser cannon Vaus
        } else if (active_powerup_ == CAPSULE_ENLARGE) {
            set_pixel(px + i, 15, 60, 140, 255); // Blue enlarged Vaus
        } else {
            set_pixel(px + i, 15, 220, 220, 230); // Silver Vaus
        }
    }
    // Red core in center of Vaus
    set_pixel(px + paddle_width_ / 2, 15, 255, 0, 0);

    // Lives on top row
    for (int l = 0; l < std::min(lives_, 3); ++l) {
        set_pixel(2 + l * 2, 0, 255, 200, 0);
    }
}

} // namespace arcade
