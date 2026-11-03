#include "game_125_bumpingbuggies.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace arcade {

static constexpr float ARENA_MIN = 1.2f;
static constexpr float ARENA_MAX = 13.8f;
static constexpr float PI = 3.14159265f;

Game125BumpingBuggies::Game125BumpingBuggies() {
    Init();
}

void Game125BumpingBuggies::Init() {
    score_ = 0;
    lives_ = 3;
    round_ = 1;
    InitRound();
}

void Game125BumpingBuggies::Reset() {
    Init();
}

void Game125BumpingBuggies::InitRound() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;

    // Player Buggy at lower-center
    player_.x = 7.5f;
    player_.y = 11.5f;
    player_.vx = 0.0f;
    player_.vy = 0.0f;
    player_.angle = -PI * 0.5f; // Facing UP
    player_.spin_timer = 0.0f;
    player_.is_ramming = false;
    player_.active = true;

    ram_cooldown_ = 0.0f;
    drift_timer_ = 0.0f;

    // 3 Opponent Buggies at top corners and center
    float opp_init[MAX_OPPONENTS][2] = {
        {3.5f, 3.5f},
        {11.5f, 3.5f},
        {7.5f, 5.0f}
    };

    for (int i = 0; i < MAX_OPPONENTS; ++i) {
        opponents_[i].x = opp_init[i][0];
        opponents_[i].y = opp_init[i][1];
        opponents_[i].vx = 0.0f;
        opponents_[i].vy = 0.0f;
        opponents_[i].angle = PI * 0.5f; // Facing DOWN towards player
        opponents_[i].spin_timer = 0.0f;
        opponents_[i].is_ramming = false;
        opponents_[i].active = true;
    }

    // 2-3 Oil slicks scattered
    slicks_[0].x = 4.5f; slicks_[0].y = 8.0f; slicks_[0].active = true;
    slicks_[1].x = 10.5f; slicks_[1].y = 8.0f; slicks_[1].active = true;
    slicks_[2].x = 7.5f; slicks_[2].y = 3.5f; slicks_[2].active = (round_ >= 2);
}

int Game125BumpingBuggies::GetActiveOpponents() const {
    int count = 0;
    for (int i = 0; i < MAX_OPPONENTS; ++i) {
        if (opponents_[i].active) count++;
    }
    return count;
}

void Game125BumpingBuggies::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & 0x0030) && !(prev_buttons & 0x0030)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PLAYER_CRASHED) {
        if (state_timer_ > 1.4f) {
            lives_--;
            if (lives_ == 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_PLAYING;
                player_.x = 7.5f;
                player_.y = 11.5f;
                player_.vx = 0.0f;
                player_.vy = 0.0f;
                player_.angle = -PI * 0.5f;
                player_.spin_timer = 0.0f;
                player_.is_ramming = false;
            }
        }
        return;
    }

    if (state_ == STATE_ROUND_CLEAR) {
        if (state_timer_ > 1.6f) {
            round_++;
            score_ += 1000;
            InitRound();
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateOpponents(dt);

    // Buggy-to-Buggy collisions (Player vs Opponents)
    for (int i = 0; i < MAX_OPPONENTS; ++i) {
        if (opponents_[i].active) {
            HandleBuggyCollision(player_, opponents_[i]);
        }
    }

    // Opponent vs Opponent collisions
    for (int i = 0; i < MAX_OPPONENTS; ++i) {
        for (int j = i + 1; j < MAX_OPPONENTS; ++j) {
            if (opponents_[i].active && opponents_[j].active) {
                HandleBuggyCollision(opponents_[i], opponents_[j]);
            }
        }
    }

    CheckWallAndHazardCollisions();

    // Check round victory
    if (GetActiveOpponents() == 0) {
        state_ = STATE_ROUND_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game125BumpingBuggies::UpdatePlayer(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (ram_cooldown_ > 0.0f) ram_cooldown_ -= dt;
    if (drift_timer_ > 0.0f) drift_timer_ -= dt;

    if (player_.spin_timer > 0.0f) {
        // Spinning out of control on oil slick!
        player_.spin_timer -= dt;
        player_.angle += 14.0f * dt;
        player_.vx *= 0.96f;
        player_.vy *= 0.96f;
        player_.x += player_.vx * dt;
        player_.y += player_.vy * dt;
        return;
    }

    // Controls
    // Turn
    float turn_speed = (drift_timer_ > 0.0f) ? 8.0f : 4.5f;
    if (buttons & 0x0004) player_.angle -= turn_speed * dt; // LEFT
    if (buttons & 0x0008) player_.angle += turn_speed * dt; // RIGHT

    // Throttle / Reverse
    float accel = 8.5f;
    if (buttons & 0x0001) { // UP
        player_.vx += std::cos(player_.angle) * accel * dt;
        player_.vy += std::sin(player_.angle) * accel * dt;
    }
    if (buttons & 0x0002) { // DOWN (Reverse)
        player_.vx -= std::cos(player_.angle) * (accel * 0.5f) * dt;
        player_.vy -= std::sin(player_.angle) * (accel * 0.5f) * dt;
    }

    // Button A: Ramming surge
    if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) {
        if (ram_cooldown_ <= 0.0f) {
            player_.is_ramming = true;
            ram_cooldown_ = 1.6f;
            player_.vx += std::cos(player_.angle) * 11.0f;
            player_.vy += std::sin(player_.angle) * 11.0f;
        }
    }
    if (ram_cooldown_ < 1.1f) {
        player_.is_ramming = false;
    }

    // Button B: Handbrake Drift
    if ((buttons & 0x0020) && !(prev_buttons & 0x0020)) {
        drift_timer_ = 0.5f;
    }

    // Friction
    float friction = (drift_timer_ > 0.0f) ? 0.97f : 0.92f;
    player_.vx *= friction;
    player_.vy *= friction;

    player_.x += player_.vx * dt;
    player_.y += player_.vy * dt;
}

void Game125BumpingBuggies::UpdateOpponents(float dt) {
    for (int i = 0; i < MAX_OPPONENTS; ++i) {
        if (!opponents_[i].active) continue;

        if (opponents_[i].spin_timer > 0.0f) {
            opponents_[i].spin_timer -= dt;
            opponents_[i].angle += 12.0f * dt;
            opponents_[i].vx *= 0.96f;
            opponents_[i].vy *= 0.96f;
            opponents_[i].x += opponents_[i].vx * dt;
            opponents_[i].y += opponents_[i].vy * dt;
            continue;
        }

        // AI steering towards player
        float dx = player_.x - opponents_[i].x;
        float dy = player_.y - opponents_[i].y;
        float target_angle = std::atan2(dy, dx);

        float angle_diff = target_angle - opponents_[i].angle;
        while (angle_diff > PI) angle_diff -= 2.0f * PI;
        while (angle_diff < -PI) angle_diff += 2.0f * PI;

        float opp_turn = 3.2f + round_ * 0.3f;
        if (angle_diff > 0.1f) opponents_[i].angle += opp_turn * dt;
        else if (angle_diff < -0.1f) opponents_[i].angle -= opp_turn * dt;

        // Drive forward
        float opp_speed = 5.5f + round_ * 0.4f;
        opponents_[i].vx += std::cos(opponents_[i].angle) * opp_speed * dt;
        opponents_[i].vy += std::sin(opponents_[i].angle) * opp_speed * dt;

        opponents_[i].vx *= 0.92f;
        opponents_[i].vy *= 0.92f;

        opponents_[i].x += opponents_[i].vx * dt;
        opponents_[i].y += opponents_[i].vy * dt;
    }
}

void Game125BumpingBuggies::HandleBuggyCollision(Buggy& a, Buggy& b) {
    float dx = b.x - a.x;
    float dy = b.y - a.y;
    float dist = std::sqrt(dx * dx + dy * dy);
    float min_dist = 1.35f;

    if (dist < min_dist && dist > 0.001f) {
        // Normal vector
        float nx = dx / dist;
        float ny = dy / dist;

        // Relative velocity
        float rvx = b.vx - a.vx;
        float rvy = b.vy - a.vy;
        float vel_along_normal = rvx * nx + rvy * ny;

        if (vel_along_normal < 0.0f) {
            float restitution = 1.4f; // Very bouncy rubber bumpers!
            if (a.is_ramming) restitution = 2.4f;
            if (b.is_ramming) restitution = 2.4f;

            float impulse = -(1.0f + restitution) * vel_along_normal * 0.5f;

            a.vx -= impulse * nx;
            a.vy -= impulse * ny;
            b.vx += impulse * nx;
            b.vy += impulse * ny;

            // Separate overlapping cars
            float overlap = (min_dist - dist) * 0.5f;
            a.x -= nx * overlap;
            a.y -= ny * overlap;
            b.x += nx * overlap;
            b.y += ny * overlap;
        }
    }
}

void Game125BumpingBuggies::CheckWallAndHazardCollisions() {
    // 1. Oil slicks
    for (int s = 0; s < MAX_OIL_SLICKS; ++s) {
        if (!slicks_[s].active) continue;

        // Player
        if (std::abs(player_.x - slicks_[s].x) < 0.9f && std::abs(player_.y - slicks_[s].y) < 0.9f) {
            player_.spin_timer = 0.8f;
        }

        // Opponents
        for (int i = 0; i < MAX_OPPONENTS; ++i) {
            if (!opponents_[i].active) continue;
            if (std::abs(opponents_[i].x - slicks_[s].x) < 0.9f && std::abs(opponents_[i].y - slicks_[s].y) < 0.9f) {
                opponents_[i].spin_timer = 0.8f;
            }
        }
    }

    // 2. Electrified Perimeter Wire (x in [ARENA_MIN, ARENA_MAX], y in [ARENA_MIN, ARENA_MAX])
    // Opponents pushed into perimeter get electrocuted/eliminated
    for (int i = 0; i < MAX_OPPONENTS; ++i) {
        if (!opponents_[i].active) continue;
        float speed = std::sqrt(opponents_[i].vx * opponents_[i].vx + opponents_[i].vy * opponents_[i].vy);
        if (opponents_[i].x <= ARENA_MIN || opponents_[i].x >= ARENA_MAX ||
            opponents_[i].y <= ARENA_MIN || opponents_[i].y >= ARENA_MAX) {
            if (speed > 2.5f) {
                // Slammed into electric fence!
                opponents_[i].active = false;
                score_ += 500;
            } else {
                // Soft bounce off fence
                if (opponents_[i].x <= ARENA_MIN) { opponents_[i].x = ARENA_MIN; opponents_[i].vx = -opponents_[i].vx * 0.8f; }
                if (opponents_[i].x >= ARENA_MAX) { opponents_[i].x = ARENA_MAX; opponents_[i].vx = -opponents_[i].vx * 0.8f; }
                if (opponents_[i].y <= ARENA_MIN) { opponents_[i].y = ARENA_MIN; opponents_[i].vy = -opponents_[i].vy * 0.8f; }
                if (opponents_[i].y >= ARENA_MAX) { opponents_[i].y = ARENA_MAX; opponents_[i].vy = -opponents_[i].vy * 0.8f; }
            }
        }
    }

    // Player vs Perimeter
    float p_speed = std::sqrt(player_.vx * player_.vx + player_.vy * player_.vy);
    if (player_.x <= ARENA_MIN || player_.x >= ARENA_MAX ||
        player_.y <= ARENA_MIN || player_.y >= ARENA_MAX) {
        if (p_speed > 5.5f) {
            // Fatal electric arc crash!
            state_ = STATE_PLAYER_CRASHED;
            state_timer_ = 0.0f;
        } else {
            // Safe bumper deflection
            if (player_.x <= ARENA_MIN) { player_.x = ARENA_MIN; player_.vx = -player_.vx * 0.8f; }
            if (player_.x >= ARENA_MAX) { player_.x = ARENA_MAX; player_.vx = -player_.vx * 0.8f; }
            if (player_.y <= ARENA_MIN) { player_.y = ARENA_MIN; player_.vy = -player_.vy * 0.8f; }
            if (player_.y >= ARENA_MAX) { player_.y = ARENA_MAX; player_.vy = -player_.vy * 0.8f; }
        }
    }
}

void Game125BumpingBuggies::Render(uint8_t* fb) {
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

    // 1. Electrified Fence Wire (Border sparking cyan/yellow)
    bool spark = ((int)(state_timer_ * 8.0f) % 2) == 0;
    for (int p = 0; p < 16; ++p) {
        uint8_t fr = spark ? 255 : 40;
        uint8_t fg = spark ? 220 : 160;
        uint8_t fb_val = spark ? 50 : 255;
        set_pixel(p, 0, fr, fg, fb_val);
        set_pixel(p, 15, fr, fg, fb_val);
        set_pixel(0, p, fr, fg, fb_val);
        set_pixel(15, p, fr, fg, fb_val);
    }

    // 2. Oil slicks (Dark slick sheen)
    for (int s = 0; s < MAX_OIL_SLICKS; ++s) {
        if (!slicks_[s].active) continue;
        int sx = (int)std::round(slicks_[s].x);
        int sy = (int)std::round(slicks_[s].y);
        set_pixel(sx, sy, 30, 20, 50);
        set_pixel(sx + 1, sy, 40, 10, 60);
        set_pixel(sx, sy + 1, 20, 30, 45);
    }

    // 3. Opponent Buggies (Green, Magenta, Orange)
    uint8_t opp_colors[3][3] = {
        {40, 255, 60},   // Green
        {220, 40, 255},  // Purple
        {255, 120, 20}   // Orange
    };
    for (int i = 0; i < MAX_OPPONENTS; ++i) {
        if (!opponents_[i].active) continue;
        int ox = (int)std::round(opponents_[i].x);
        int oy = (int)std::round(opponents_[i].y);
        set_pixel(ox, oy, opp_colors[i][0], opp_colors[i][1], opp_colors[i][2]);
        // Front bumper direction
        int hx = ox + (int)std::round(std::cos(opponents_[i].angle));
        int hy = oy + (int)std::round(std::sin(opponents_[i].angle));
        set_pixel(hx, hy, 255, 255, 255);
    }

    // 4. Player Buggy (Bright Cyan with White Front Bumper)
    int px_s = (int)std::round(player_.x);
    int py_s = (int)std::round(player_.y);
    if (state_ == STATE_PLAYING || state_ == STATE_ROUND_CLEAR) {
        if (player_.is_ramming) {
            set_pixel(px_s, py_s, 255, 255, 255); // Supercharge white glow
        } else {
            set_pixel(px_s, py_s, 0, 230, 255); // Cyan body
        }
        int hx = px_s + (int)std::round(std::cos(player_.angle));
        int hy = py_s + (int)std::round(std::sin(player_.angle));
        set_pixel(hx, hy, 255, 220, 40); // Yellow bumper nose
    } else if (state_ == STATE_PLAYER_CRASHED) {
        // High voltage electric discharge
        set_pixel(px_s, py_s, 255, 255, 255);
        set_pixel(px_s - 1, py_s, 0, 200, 255);
        set_pixel(px_s + 1, py_s, 255, 100, 0);
        set_pixel(px_s, py_s - 1, 255, 220, 0);
        set_pixel(px_s, py_s + 1, 0, 200, 255);
    }

    // 5. Lives indicators
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(1 + l * 2, 1, 0, 230, 255);
    }
}

} // namespace arcade
