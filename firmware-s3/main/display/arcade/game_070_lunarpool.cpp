#include "game_070_lunarpool.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game070LunarPool::Game070LunarPool()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(8000),
      lives_(3),
      aim_angle_(0.0f),
      shot_power_(0.0f),
      is_charging_power_(false),
      combo_multiplier_(1),
      friction_(1.4f) {
}

void Game070LunarPool::Init() {
    Reset();
}

void Game070LunarPool::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitTable();
}

void Game070LunarPool::InitTable() {
    aim_angle_ = 0.0f;
    shot_power_ = 0.0f;
    is_charging_power_ = false;
    combo_multiplier_ = 1;
    friction_ = 1.4f;

    // 4 Corner Pockets
    pockets_[0] = {1.5f, 1.5f, 1.3f};
    pockets_[1] = {14.5f, 1.5f, 1.3f};
    pockets_[2] = {1.5f, 14.5f, 1.3f};
    pockets_[3] = {14.5f, 14.5f, 1.3f};

    // Balls: 0 is Cue ball
    balls_[0] = {4.0f, 8.0f, 0.0f, 0.0f, true, 0, false};

    // Target diamond arrangement
    balls_[1] = {10.0f, 8.0f, 0.0f, 0.0f, false, 1, false}; // Yellow
    balls_[2] = {11.5f, 7.0f, 0.0f, 0.0f, false, 2, false}; // Blue
    balls_[3] = {11.5f, 9.0f, 0.0f, 0.0f, false, 3, false}; // Red
    balls_[4] = {13.0f, 8.0f, 0.0f, 0.0f, false, 4, false}; // Green
}

int Game070LunarPool::GetBallsRemaining() const {
    int count = 0;
    for (int i = 1; i < MAX_BALLS; ++i) {
        if (!balls_[i].in_pocket) count++;
    }
    return count;
}

void Game070LunarPool::ShootCueBall(float power) {
    if (balls_[0].in_pocket) return;

    balls_[0].vx = std::cos(aim_angle_) * power;
    balls_[0].vy = std::sin(aim_angle_) * power;
    state_ = STATE_BALLS_MOVING;
    shot_power_ = 0.0f;
    is_charging_power_ = false;
}

void Game070LunarPool::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.8f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                balls_[0].x = 4.0f;
                balls_[0].y = 8.0f;
                balls_[0].vx = 0.0f;
                balls_[0].vy = 0.0f;
                balls_[0].in_pocket = false;
            } else {
                state_ = STATE_START;
            }
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f) {
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            InitTable();
        }
        return;
    }

    if (state_ == STATE_PLAYING) {
        UpdateAiming(dt, buttons, prev_buttons);
    } else if (state_ == STATE_BALLS_MOVING) {
        UpdatePhysics(dt);
        CheckBallCollisions();
        CheckPocketCollisions();

        // Check if all balls stopped moving
        bool moving = false;
        for (int i = 0; i < MAX_BALLS; ++i) {
            if (!balls_[i].in_pocket && (std::abs(balls_[i].vx) > 0.1f || std::abs(balls_[i].vy) > 0.1f)) {
                moving = true;
                break;
            }
        }

        if (!moving) {
            state_ = STATE_PLAYING;
            combo_multiplier_ = 1; // Reset multiplier after turn ends
        }
    }
}

void Game070LunarPool::UpdateAiming(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float rot_speed = 3.0f;
    if (buttons & BUTTON_LEFT)  aim_angle_ -= rot_speed * dt;
    if (buttons & BUTTON_RIGHT) aim_angle_ += rot_speed * dt;

    // Normalize angle to [-PI, PI]
    while (aim_angle_ > 3.14159f)  aim_angle_ -= 6.28318f;
    while (aim_angle_ < -3.14159f) aim_angle_ += 6.28318f;

    // Button A: Charge and shoot
    if (buttons & BUTTON_A) {
        is_charging_power_ = true;
        shot_power_ = std::min(18.0f, shot_power_ + 14.0f * dt);
    } else if (is_charging_power_) {
        // Released A: Strike ball!
        ShootCueBall(std::max(3.0f, shot_power_));
    }
}

void Game070LunarPool::UpdatePhysics(float dt) {
    for (int i = 0; i < MAX_BALLS; ++i) {
        if (balls_[i].in_pocket) continue;

        balls_[i].x += balls_[i].vx * dt;
        balls_[i].y += balls_[i].vy * dt;

        // Friction deceleration
        float decel = friction_ * dt;
        float speed = std::sqrt(balls_[i].vx * balls_[i].vx + balls_[i].vy * balls_[i].vy);
        if (speed > 0.05f) {
            float new_speed = std::max(0.0f, speed - speed * decel);
            balls_[i].vx = (balls_[i].vx / speed) * new_speed;
            balls_[i].vy = (balls_[i].vy / speed) * new_speed;
        } else {
            balls_[i].vx = 0.0f;
            balls_[i].vy = 0.0f;
        }

        // Cushion bounce
        if (balls_[i].x <= 1.8f) {
            balls_[i].x = 1.8f;
            balls_[i].vx = -balls_[i].vx * 0.85f;
        } else if (balls_[i].x >= 14.2f) {
            balls_[i].x = 14.2f;
            balls_[i].vx = -balls_[i].vx * 0.85f;
        }

        if (balls_[i].y <= 1.8f) {
            balls_[i].y = 1.8f;
            balls_[i].vy = -balls_[i].vy * 0.85f;
        } else if (balls_[i].y >= 14.2f) {
            balls_[i].y = 14.2f;
            balls_[i].vy = -balls_[i].vy * 0.85f;
        }
    }
}

void Game070LunarPool::CheckBallCollisions() {
    for (int i = 0; i < MAX_BALLS; ++i) {
        if (balls_[i].in_pocket) continue;
        for (int j = i + 1; j < MAX_BALLS; ++j) {
            if (balls_[j].in_pocket) continue;

            float dx = balls_[j].x - balls_[i].x;
            float dy = balls_[j].y - balls_[i].y;
            float dist = std::sqrt(dx * dx + dy * dy);

            if (dist < 1.1f && dist > 0.001f) {
                // Separate overlap
                float overlap = 0.5f * (1.1f - dist);
                float nx = dx / dist;
                float ny = dy / dist;

                balls_[i].x -= nx * overlap;
                balls_[i].y -= ny * overlap;
                balls_[j].x += nx * overlap;
                balls_[j].y += ny * overlap;

                // Elastic momentum transfer along normal
                float kx = balls_[i].vx - balls_[j].vx;
                float ky = balls_[i].vy - balls_[j].vy;
                float p = 2.0f * (nx * kx + ny * ky) / 2.0f;

                balls_[i].vx -= p * nx * 0.95f;
                balls_[i].vy -= p * ny * 0.95f;
                balls_[j].vx += p * nx * 0.95f;
                balls_[j].vy += p * ny * 0.95f;
            }
        }
    }
}

void Game070LunarPool::CheckPocketCollisions() {
    for (int i = 0; i < MAX_BALLS; ++i) {
        if (balls_[i].in_pocket) continue;

        for (int p = 0; p < MAX_POCKETS; ++p) {
            float dx = balls_[i].x - pockets_[p].x;
            float dy = balls_[i].y - pockets_[p].y;
            float dist = std::sqrt(dx * dx + dy * dy);

            if (dist < pockets_[p].radius) {
                // Ball entered pocket!
                balls_[i].in_pocket = true;
                balls_[i].vx = 0.0f;
                balls_[i].vy = 0.0f;

                if (balls_[i].is_cue) {
                    // Scratch foul!
                    lives_--;
                    state_ = STATE_DEAD;
                    state_timer_ = 0.0f;
                    return;
                } else {
                    // Target ball pocketed!
                    score_ += 250 * combo_multiplier_;
                    combo_multiplier_ *= 2;

                    if (GetBallsRemaining() == 0) {
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        score_ += 3000;
                        if (score_ > high_score_) high_score_ = score_;
                        return;
                    }
                }
                break;
            }
        }
    }
}

void Game070LunarPool::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Lunar Table Cushions & Felt
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                // Wooden rail cushion
                set_pixel(x, y, 90, 50, 20);
            } else {
                // Lunar deep purple felt
                set_pixel(x, y, 35, 20, 65);
            }
        }
    }

    // 2. Corner Pockets (black holes)
    set_pixel(1, 1, 0, 0, 0);
    set_pixel(2, 1, 0, 0, 0);
    set_pixel(1, 2, 0, 0, 0);

    set_pixel(14, 1, 0, 0, 0);
    set_pixel(13, 1, 0, 0, 0);
    set_pixel(14, 2, 0, 0, 0);

    set_pixel(1, 14, 0, 0, 0);
    set_pixel(2, 14, 0, 0, 0);
    set_pixel(1, 13, 0, 0, 0);

    set_pixel(14, 14, 0, 0, 0);
    set_pixel(13, 14, 0, 0, 0);
    set_pixel(14, 13, 0, 0, 0);

    // 3. Aiming cue line (when player is aiming)
    if (state_ == STATE_PLAYING && !balls_[0].in_pocket) {
        for (float step = 1.2f; step < 5.0f; step += 1.0f) {
            int ax = int(std::round(balls_[0].x + std::cos(aim_angle_) * step));
            int ay = int(std::round(balls_[0].y + std::sin(aim_angle_) * step));
            set_pixel(ax, ay, 200, 200, 200);
        }
    }

    // 4. Balls
    for (int i = 0; i < MAX_BALLS; ++i) {
        if (balls_[i].in_pocket) continue;
        int bx = int(std::round(balls_[i].x));
        int by = int(std::round(balls_[i].y));

        if (balls_[i].is_cue) {
            // White Cue Ball
            set_pixel(bx, by, 255, 255, 255);
        } else if (balls_[i].number == 1) {
            // Yellow 1-Ball
            set_pixel(bx, by, 255, 220, 30);
        } else if (balls_[i].number == 2) {
            // Blue 2-Ball
            set_pixel(bx, by, 40, 100, 255);
        } else if (balls_[i].number == 3) {
            // Red 3-Ball
            set_pixel(bx, by, 255, 40, 40);
        } else {
            // Green 4-Ball
            set_pixel(bx, by, 40, 220, 50);
        }
    }

    // 5. Power Meter HUD (Top cushion)
    if (is_charging_power_) {
        int power_bars = int((shot_power_ / 18.0f) * 10.0f);
        for (int p = 0; p < power_bars; ++p) {
            set_pixel(3 + p, 0, 255, 120, 0);
        }
    }
}

} // namespace arcade
