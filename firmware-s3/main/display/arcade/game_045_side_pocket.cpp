#include "game_045_side_pocket.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

static constexpr float PI = 3.14159265358979323846f;

Game045SidePocket::Game045SidePocket()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      balls_potted_(0),
      aim_angle_(0.0f),
      charge_power_(0.5f),
      charge_dir_(1.0f) {
}

void Game045SidePocket::Init() {
    Reset();
}

void Game045SidePocket::Reset() {
    state_ = STATE_AIMING;
    state_timer_ = 0.0f;
    score_ = 0;
    balls_potted_ = 0;
    aim_angle_ = 0.0f;
    charge_power_ = 0.5f;
    charge_dir_ = 1.0f;

    InitTable();
}

void Game045SidePocket::InitTable() {
    // Ball 0: White Cue Ball
    balls_[0] = {4.0f, 7.5f, 0.0f, 0.0f, true, true, 255, 255, 255};

    // 5 Colored Object Balls in triangular rack
    // Ball 1: Solid Red
    balls_[1] = {9.5f, 7.5f, 0.0f, 0.0f, true, false, 231, 76, 60};
    // Ball 2: Solid Yellow
    balls_[2] = {10.5f, 7.0f, 0.0f, 0.0f, true, false, 241, 196, 15};
    // Ball 3: Solid Blue
    balls_[3] = {10.5f, 8.0f, 0.0f, 0.0f, true, false, 52, 152, 219};
    // Ball 4: Solid Orange
    balls_[4] = {11.5f, 6.5f, 0.0f, 0.0f, true, false, 230, 126, 34};
    // Ball 5: Solid Purple
    balls_[5] = {11.5f, 8.5f, 0.0f, 0.0f, true, false, 155, 89, 182};
}

int Game045SidePocket::GetRemainingBalls() const {
    int count = 0;
    for (int i = 1; i < TOTAL_BALLS; ++i) {
        if (balls_[i].active) count++;
    }
    return count;
}

void Game045SidePocket::StrikeCueBall(float angle_rad, float power) {
    float impulse = 6.0f + power * 14.0f; // 6 to 20 units/s
    balls_[0].vx = cosf(angle_rad) * impulse;
    balls_[0].vy = sinf(angle_rad) * impulse;
    state_ = STATE_ROLLING;
}

bool Game045SidePocket::AreBallsMoving() const {
    for (int i = 0; i < TOTAL_BALLS; ++i) {
        if (!balls_[i].active) continue;
        if (fabsf(balls_[i].vx) > 0.08f || fabsf(balls_[i].vy) > 0.08f) {
            return true;
        }
    }
    return false;
}

void Game045SidePocket::CheckPocketCollisions() {
    static const struct {
        float x;
        float y;
    } pockets[6] = {
        {2.0f, 2.0f},   // Top-Left
        {13.0f, 2.0f},  // Top-Right
        {2.0f, 13.0f},  // Bottom-Left
        {13.0f, 13.0f}, // Bottom-Right
        {2.0f, 7.5f},   // Mid-Left
        {13.0f, 7.5f}   // Mid-Right
    };

    for (int i = 0; i < TOTAL_BALLS; ++i) {
        if (!balls_[i].active) continue;

        for (int p = 0; p < 6; ++p) {
            float dx = balls_[i].x - pockets[p].x;
            float dy = balls_[i].y - pockets[p].y;
            float dist_sq = dx * dx + dy * dy;

            if (dist_sq <= 0.85f * 0.85f) {
                // Ball Potted!
                if (balls_[i].is_cue) {
                    // Scratch! Cue ball potted penalty
                    score_ = std::max(0, static_cast<int>(score_ - 50));
                    state_ = STATE_SCRATCH;
                    state_timer_ = 0.0f;
                    balls_[i].vx = 0.0f;
                    balls_[i].vy = 0.0f;
                    balls_[i].x = 4.0f;
                    balls_[i].y = 7.5f;
                } else {
                    // Object ball potted
                    balls_[i].active = false;
                    balls_[i].vx = 0.0f;
                    balls_[i].vy = 0.0f;
                    balls_potted_++;
                    score_ += 150;
                    if (score_ > high_score_) high_score_ = score_;
                }
                break;
            }
        }
    }
}

void Game045SidePocket::CheckCushionCollisions() {
    const float min_x = 2.0f;
    const float max_x = 13.0f;
    const float min_y = 2.0f;
    const float max_y = 13.0f;
    const float restitution = 0.82f;

    for (int i = 0; i < TOTAL_BALLS; ++i) {
        if (!balls_[i].active) continue;

        // Left / Right cushions
        if (balls_[i].x < min_x) {
            balls_[i].x = min_x;
            balls_[i].vx = -balls_[i].vx * restitution;
        } else if (balls_[i].x > max_x) {
            balls_[i].x = max_x;
            balls_[i].vx = -balls_[i].vx * restitution;
        }

        // Top / Bottom cushions
        if (balls_[i].y < min_y) {
            balls_[i].y = min_y;
            balls_[i].vy = -balls_[i].vy * restitution;
        } else if (balls_[i].y > max_y) {
            balls_[i].y = max_y;
            balls_[i].vy = -balls_[i].vy * restitution;
        }
    }
}

void Game045SidePocket::CheckBallBallCollisions() {
    const float ball_diam = 0.95f;
    const float restitution = 0.88f;

    for (int i = 0; i < TOTAL_BALLS; ++i) {
        if (!balls_[i].active) continue;

        for (int j = i + 1; j < TOTAL_BALLS; ++j) {
            if (!balls_[j].active) continue;

            float dx = balls_[j].x - balls_[i].x;
            float dy = balls_[j].y - balls_[i].y;
            float dist = sqrtf(dx * dx + dy * dy);

            if (dist < ball_diam && dist > 0.001f) {
                // Normal vector
                float nx = dx / dist;
                float ny = dy / dist;

                // Push out of penetration
                float overlap = 0.5f * (ball_diam - dist);
                balls_[i].x -= nx * overlap;
                balls_[i].y -= ny * overlap;
                balls_[j].x += nx * overlap;
                balls_[j].y += ny * overlap;

                // Relative velocity
                float kx = balls_[i].vx - balls_[j].vx;
                float ky = balls_[i].vy - balls_[j].vy;
                float p = 2.0f * (nx * kx + ny * ky) / 2.0f; // Equal masses

                if (p > 0.0f) {
                    balls_[i].vx -= p * nx * restitution;
                    balls_[i].vy -= p * ny * restitution;
                    balls_[j].vx += p * nx * restitution;
                    balls_[j].vy += p * ny * restitution;
                }
            }
        }
    }
}

void Game045SidePocket::UpdatePhysics(float dt) {
    const float friction = 1.35f;

    for (int i = 0; i < TOTAL_BALLS; ++i) {
        if (!balls_[i].active) continue;

        balls_[i].x += balls_[i].vx * dt;
        balls_[i].y += balls_[i].vy * dt;

        // Felt rolling friction drag
        float drag = std::max(0.0f, 1.0f - friction * dt);
        balls_[i].vx *= drag;
        balls_[i].vy *= drag;

        if (fabsf(balls_[i].vx) < 0.08f) balls_[i].vx = 0.0f;
        if (fabsf(balls_[i].vy) < 0.08f) balls_[i].vy = 0.0f;
    }

    CheckCushionCollisions();
    CheckBallBallCollisions();
    CheckPocketCollisions();
}

void Game045SidePocket::UpdateAiming(float dt, uint32_t buttons, uint32_t prev_buttons) {
    const float rotate_speed = 2.4f;

    if (buttons & KEY_LEFT)  aim_angle_ -= rotate_speed * dt;
    if (buttons & KEY_RIGHT) aim_angle_ += rotate_speed * dt;

    // Keep angle in [0, 2*PI]
    while (aim_angle_ < 0.0f) aim_angle_ += 2.0f * PI;
    while (aim_angle_ >= 2.0f * PI) aim_angle_ -= 2.0f * PI;

    // Press KEY_A to begin charging shot
    if ((buttons & KEY_A) && !(prev_buttons & KEY_A)) {
        state_ = STATE_CHARGING;
        charge_power_ = 0.2f;
        charge_dir_ = 1.0f;
    }
}

void Game045SidePocket::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_SCRATCH) {
        if (state_timer_ >= 1.2f) {
            state_ = STATE_AIMING;
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ >= 2.5f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_AIMING) {
        UpdateAiming(dt, buttons, prev_buttons);
    } else if (state_ == STATE_CHARGING) {
        // Oscillate power meter
        charge_power_ += charge_dir_ * 1.8f * dt;
        if (charge_power_ >= 1.0f) {
            charge_power_ = 1.0f;
            charge_dir_ = -1.0f;
        } else if (charge_power_ <= 0.1f) {
            charge_power_ = 0.1f;
            charge_dir_ = 1.0f;
        }

        // Release or press KEY_A to strike!
        if (!(buttons & KEY_A) && (prev_buttons & KEY_A)) {
            StrikeCueBall(aim_angle_, charge_power_);
        }
    } else if (state_ == STATE_ROLLING) {
        UpdatePhysics(dt);

        if (!AreBallsMoving()) {
            if (GetRemainingBalls() == 0) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                score_ += 1000;
                if (score_ > high_score_) high_score_ = score_;
            } else {
                state_ = STATE_AIMING;
            }
        }
    }
}

void Game045SidePocket::Render(uint8_t* fb) {
    // 1. Table Border & Cushion Cushions (Mahogany Wood #5B2C6F / #6E2C00)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (x >= 2 && x <= 13 && y >= 2 && y <= 13) {
                // Green Baize Felt (#1E8449 / #196F3D)
                fb[idx + 0] = 25;
                fb[idx + 1] = 111;
                fb[idx + 2] = 61;
            } else {
                // Mahogany Table Border
                fb[idx + 0] = 110;
                fb[idx + 1] = 44;
                fb[idx + 2] = 0;
            }
        }
    }

    // 2. Six Pockets (Pitch Black)
    static const int pocket_coords[6][2] = {
        {2, 2}, {13, 2}, {2, 13}, {13, 13}, {2, 7}, {13, 7}
    };
    for (int p = 0; p < 6; ++p) {
        int px = pocket_coords[p][0];
        int py = pocket_coords[p][1];
        int idx = (py * 16 + px) * 3;
        fb[idx + 0] = 0; fb[idx + 1] = 0; fb[idx + 2] = 0;
    }

    // 3. Aiming Guide Laser (in Aiming / Charging state)
    if (state_ == STATE_AIMING || state_ == STATE_CHARGING) {
        float cx = balls_[0].x;
        float cy = balls_[0].y;
        for (float r = 1.2f; r <= 3.5f; r += 1.0f) {
            int ax = static_cast<int>(std::round(cx + cosf(aim_angle_) * r));
            int ay = static_cast<int>(std::round(cy + sinf(aim_angle_) * r));
            if (ax >= 2 && ax <= 13 && ay >= 2 && ay <= 13) {
                int a_idx = (ay * 16 + ax) * 3;
                fb[a_idx + 0] = 174; fb[a_idx + 1] = 214; fb[a_idx + 2] = 241; // Light Cyan Dot
            }
        }
    }

    // 4. Balls Rendering
    for (int i = 0; i < TOTAL_BALLS; ++i) {
        if (!balls_[i].active) continue;

        int bx = static_cast<int>(std::round(balls_[i].x));
        int by = static_cast<int>(std::round(balls_[i].y));

        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            fb[idx + 0] = balls_[i].r;
            fb[idx + 1] = balls_[i].g;
            fb[idx + 2] = balls_[i].b;
        }
    }

    // 5. Power Meter Bar on Row 0 during Charging
    if (state_ == STATE_CHARGING) {
        int bars = static_cast<int>(std::round(charge_power_ * 14.0f));
        for (int x = 1; x <= 14; ++x) {
            int idx = (0 * 16 + x) * 3;
            if (x <= bars) {
                fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15; // Golden Power Bar
            }
        }
    }
}

} // namespace arcade
