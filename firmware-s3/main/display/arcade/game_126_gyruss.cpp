#include "game_126_gyruss.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace arcade {

static constexpr float PI = 3.14159265f;
static constexpr float CENTER_X = 7.5f;
static constexpr float CENTER_Y = 7.5f;
static constexpr float ORBIT_RADIUS = 6.8f;

Game126Gyruss::Game126Gyruss() {
    Init();
}

void Game126Gyruss::Init() {
    score_ = 0;
    lives_ = 3;
    warp_stage_ = 0; // Neptune
    InitStage();
}

void Game126Gyruss::Reset() {
    Init();
}

void Game126Gyruss::InitStage() {
    state_ = STATE_FLYING;
    state_timer_ = 0.0f;
    remaining_dist_ = 20;

    player_angle_ = -PI * 0.5f; // Top of circle
    roll_timer_ = 0.0f;
    roll_cooldown_ = 0.0f;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
        bullets_[i].radius = 0.0f;
        bullets_[i].angle = 0.0f;
    }

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = false;
    }

    wave_timer_ = 0.5f;
}

void Game126Gyruss::SpawnWave() {
    // Spawn 2 to 4 enemies from central vortex
    int count = 2 + (warp_stage_ % 3);
    float base_angle = (float)(rand() % 628) / 100.0f;

    for (int i = 0; i < MAX_ENEMIES && count > 0; ++i) {
        if (!enemies_[i].active) {
            enemies_[i].radius = 0.5f;
            enemies_[i].angle = base_angle + (float)count * 0.7f;
            enemies_[i].speed_r = 2.8f + warp_stage_ * 0.3f;
            enemies_[i].speed_a = ((count % 2 == 0) ? 1.8f : -1.8f);
            enemies_[i].is_asteroid = (rand() % 4 == 0);
            enemies_[i].active = true;
            count--;
        }
    }
}

void Game126Gyruss::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & 0x0030) && !(prev_buttons & 0x0030)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PLAYER_EXPLODING) {
        if (state_timer_ > 1.3f) {
            lives_--;
            if (lives_ == 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_FLYING;
                player_angle_ = -PI * 0.5f;
                roll_timer_ = 0.0f;
            }
        }
        return;
    }

    if (state_ == STATE_WARPING) {
        if (state_timer_ > 1.6f) {
            warp_stage_++;
            score_ += 1500;
            InitStage();
        }
        return;
    }

    // Fire dual plasma bullets (Button A)
    if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) {
        for (int i = 0; i < MAX_BULLETS; ++i) {
            if (!bullets_[i].active) {
                bullets_[i].active = true;
                bullets_[i].radius = ORBIT_RADIUS - 0.4f;
                bullets_[i].angle = player_angle_;
                break;
            }
        }
    }

    // Barrel roll / evasive corkscrew (Button B)
    if (roll_cooldown_ > 0.0f) roll_cooldown_ -= dt;
    if ((buttons & 0x0020) && !(prev_buttons & 0x0020)) {
        if (roll_cooldown_ <= 0.0f) {
            roll_timer_ = 0.4f;
            roll_cooldown_ = 1.8f;
        }
    }
    if (roll_timer_ > 0.0f) roll_timer_ -= dt;

    UpdateShip(dt, buttons);
    UpdateBullets(dt);
    UpdateEnemies(dt);
    CheckCollisions();

    // Check Warp Arrival
    if (remaining_dist_ <= 0) {
        bool enemies_active = false;
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (enemies_[i].active) {
                enemies_active = true;
                break;
            }
        }
        if (!enemies_active) {
            state_ = STATE_WARPING;
            state_timer_ = 0.0f;
        }
    }
}

void Game126Gyruss::UpdateShip(float dt, uint16_t buttons) {
    float rot_speed = (roll_timer_ > 0.0f) ? 10.0f : 4.8f;

    if (buttons & 0x0004) player_angle_ -= rot_speed * dt; // Counter-clockwise
    if (buttons & 0x0008) player_angle_ += rot_speed * dt; // Clockwise

    while (player_angle_ < 0.0f) player_angle_ += 2.0f * PI;
    while (player_angle_ >= 2.0f * PI) player_angle_ -= 2.0f * PI;
}

void Game126Gyruss::UpdateBullets(float dt) {
    float bullet_speed = 16.0f;
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        bullets_[i].radius -= bullet_speed * dt;
        if (bullets_[i].radius <= 0.4f) {
            bullets_[i].active = false;
        }
    }
}

void Game126Gyruss::UpdateEnemies(float dt) {
    wave_timer_ -= dt;
    if (wave_timer_ <= 0.0f && remaining_dist_ > 0) {
        wave_timer_ = 2.2f - (warp_stage_ % 4) * 0.2f;
        SpawnWave();
        remaining_dist_ -= 2;
    }

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        enemies_[i].radius += enemies_[i].speed_r * dt;
        enemies_[i].angle += enemies_[i].speed_a * dt;
        while (enemies_[i].angle < 0.0f) enemies_[i].angle += 2.0f * PI;
        while (enemies_[i].angle >= 2.0f * PI) enemies_[i].angle -= 2.0f * PI;

        if (enemies_[i].radius > 7.5f) {
            // Escaped past perimeter
            enemies_[i].active = false;
        }
    }
}

void Game126Gyruss::CheckCollisions() {
    // 1. Bullets vs Enemies
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;

        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;

            float r_diff = std::abs(bullets_[b].radius - enemies_[e].radius);
            float a_diff = std::abs(bullets_[b].angle - enemies_[e].angle);
            while (a_diff > PI) a_diff = std::abs(a_diff - 2.0f * PI);

            if (r_diff < 0.85f && a_diff < 0.38f) {
                bullets_[b].active = false;
                enemies_[e].active = false;
                score_ += enemies_[e].is_asteroid ? 200 : 100;
                break;
            }
        }
    }

    // 2. Enemies vs Player
    if (roll_timer_ <= 0.0f) { // Invulnerable during roll
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;

            if (enemies_[e].radius >= ORBIT_RADIUS - 0.7f && enemies_[e].radius <= ORBIT_RADIUS + 0.7f) {
                float a_diff = std::abs(player_angle_ - enemies_[e].angle);
                while (a_diff > PI) a_diff = std::abs(a_diff - 2.0f * PI);

                if (a_diff < 0.38f) {
                    enemies_[e].active = false;
                    state_ = STATE_PLAYER_EXPLODING;
                    state_timer_ = 0.0f;
                    break;
                }
            }
        }
    }
}

void Game126Gyruss::Render(uint8_t* fb) {
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

    // 1. Central galaxy / vanishing star vortex
    set_pixel(7, 7, 60, 60, 140);
    set_pixel(8, 7, 60, 60, 140);
    set_pixel(7, 8, 60, 60, 140);
    set_pixel(8, 8, 120, 120, 255);

    // 2. Distant planetary destination pip
    set_pixel(8, 8, 255, 200, 50);

    // 3. Enemies expanding outward
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = (int)std::round(CENTER_X + enemies_[i].radius * std::cos(enemies_[i].angle));
        int ey = (int)std::round(CENTER_Y + enemies_[i].radius * std::sin(enemies_[i].angle));

        if (enemies_[i].is_asteroid) {
            set_pixel(ex, ey, 200, 140, 60); // Asteroid brown
        } else {
            // Alien starfighter (cyan/magenta)
            if (enemies_[i].radius < 3.5f) {
                set_pixel(ex, ey, 180, 40, 255);
            } else {
                set_pixel(ex, ey, 255, 40, 120);
            }
        }
    }

    // 4. Inward plasma bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        int bx = (int)std::round(CENTER_X + bullets_[i].radius * std::cos(bullets_[i].angle));
        int by = (int)std::round(CENTER_Y + bullets_[i].radius * std::sin(bullets_[i].angle));
        set_pixel(bx, by, 80, 255, 120);
    }

    // 5. Player Starfighter on 360-degree perimeter
    int px = (int)std::round(CENTER_X + ORBIT_RADIUS * std::cos(player_angle_));
    int py = (int)std::round(CENTER_Y + ORBIT_RADIUS * std::sin(player_angle_));

    if (state_ == STATE_FLYING || state_ == STATE_WARPING) {
        if (roll_timer_ > 0.0f) {
            set_pixel(px, py, 255, 255, 255); // Rolling bright glow
        } else {
            set_pixel(px, py, 0, 230, 255); // Cyan fighter
        }
        // Nose pointing inward towards center (7.5, 7.5)
        float in_ang = player_angle_ + PI;
        int nx = px + (int)std::round(std::cos(in_ang));
        int ny = py + (int)std::round(std::sin(in_ang));
        set_pixel(nx, ny, 255, 220, 0); // Yellow targeting nose
    } else if (state_ == STATE_PLAYER_EXPLODING) {
        set_pixel(px, py, 255, 220, 40);
        set_pixel(px - 1, py, 255, 50, 20);
        set_pixel(px + 1, py, 255, 50, 20);
        set_pixel(px, py - 1, 255, 50, 20);
        set_pixel(px, py + 1, 255, 50, 20);
    }

    // 6. Lives and warp distance
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l * 2, 0, 0, 230, 255);
    }
}

} // namespace arcade
