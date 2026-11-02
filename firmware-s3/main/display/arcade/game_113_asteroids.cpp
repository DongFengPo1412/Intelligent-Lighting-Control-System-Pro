#include "game_113_asteroids.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static float WrapCoord(float val, float max_val = 16.0f) {
    while (val < 0.0f) val += max_val;
    while (val >= max_val) val -= max_val;
    return val;
}

static float WrapDiff(float a, float b, float max_val = 16.0f) {
    float diff = std::abs(a - b);
    if (diff > max_val * 0.5f) diff = max_val - diff;
    return diff;
}

Game113Asteroids::Game113Asteroids() {
    Reset();
}

void Game113Asteroids::Init() {
    Reset();
}

void Game113Asteroids::Reset() {
    score_ = 0;
    lives_ = 3;
    wave_ = 1;
    InitWave();
}

void Game113Asteroids::InitWave() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 8.0f;
    py_ = 8.0f;
    vx_ = 0.0f;
    vy_ = 0.0f;
    angle_ = -1.57079f; // Facing UP
    thrusting_ = false;

    for (int i = 0; i < MAX_ASTEROIDS; ++i) {
        asteroids_[i].active = false;
    }
    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    saucer_.active = false;
    saucer_spawn_timer_ = 8.0f;

    // Spawn Initial Wave of Large Asteroids (tier 3)
    int count = std::min(4, 2 + wave_);
    float positions[4][2] = {
        {2.0f, 2.0f},
        {14.0f, 2.0f},
        {2.0f, 14.0f},
        {14.0f, 14.0f}
    };

    for (int i = 0; i < count; ++i) {
        float dir_angle = static_cast<float>(i) * 1.57f + 0.4f;
        float speed = 2.0f + static_cast<float>(wave_) * 0.3f;
        SpawnAsteroid(positions[i][0], positions[i][1],
                      std::cos(dir_angle) * speed,
                      std::sin(dir_angle) * speed,
                      3);
    }
}

void Game113Asteroids::SpawnAsteroid(float x, float y, float vx, float vy, int tier) {
    for (int i = 0; i < MAX_ASTEROIDS; ++i) {
        if (!asteroids_[i].active) {
            asteroids_[i].x = WrapCoord(x);
            asteroids_[i].y = WrapCoord(y);
            asteroids_[i].vx = vx;
            asteroids_[i].vy = vy;
            asteroids_[i].tier = tier;
            asteroids_[i].active = true;
            break;
        }
    }
}

void Game113Asteroids::SplitAsteroid(int idx) {
    if (idx < 0 || idx >= MAX_ASTEROIDS || !asteroids_[idx].active) return;

    int old_tier = asteroids_[idx].tier;
    float ox = asteroids_[idx].x;
    float oy = asteroids_[idx].y;
    float ovx = asteroids_[idx].vx;
    float ovy = asteroids_[idx].vy;

    asteroids_[idx].active = false;

    if (old_tier == 3) {
        score_ += 20;
        // Split into two Tier 2 (Medium)
        float spd = std::sqrt(ovx * ovx + ovy * ovy) * 1.3f;
        float ang = std::atan2(ovy, ovx);
        SpawnAsteroid(ox, oy, std::cos(ang + 0.7f) * spd, std::sin(ang + 0.7f) * spd, 2);
        SpawnAsteroid(ox, oy, std::cos(ang - 0.7f) * spd, std::sin(ang - 0.7f) * spd, 2);
    } else if (old_tier == 2) {
        score_ += 50;
        // Split into two Tier 1 (Small)
        float spd = std::sqrt(ovx * ovx + ovy * ovy) * 1.4f;
        float ang = std::atan2(ovy, ovx);
        SpawnAsteroid(ox, oy, std::cos(ang + 0.9f) * spd, std::sin(ang + 0.9f) * spd, 1);
        SpawnAsteroid(ox, oy, std::cos(ang - 0.9f) * spd, std::sin(ang - 0.9f) * spd, 1);
    } else if (old_tier == 1) {
        score_ += 100;
        // Small asteroid vaporized!
    }
}

void Game113Asteroids::FireBullet() {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].x = WrapCoord(px_ + std::cos(angle_) * 1.2f);
            bullets_[i].y = WrapCoord(py_ + std::sin(angle_) * 1.2f);
            bullets_[i].vx = vx_ + std::cos(angle_) * 22.0f;
            bullets_[i].vy = vy_ + std::sin(angle_) * 22.0f;
            bullets_[i].life = 0.75f;
            bullets_[i].active = true;
            break;
        }
    }
}

void Game113Asteroids::HyperspaceJump() {
    // Quantum teleportation jump
    px_ = static_cast<float>((static_cast<int>(px_ * 7.0f + 5.0f)) % 14 + 1);
    py_ = static_cast<float>((static_cast<int>(py_ * 11.0f + 3.0f)) % 14 + 1);
    vx_ = 0.0f;
    vy_ = 0.0f;
}

void Game113Asteroids::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PLAYER_EXPLODING) {
        if (state_timer_ > 1.2f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_PLAYING;
                px_ = 8.0f;
                py_ = 8.0f;
                vx_ = 0.0f;
                vy_ = 0.0f;
                angle_ = -1.57079f;
            }
        }
        return;
    }

    if (state_ == STATE_WAVE_CLEAR) {
        if (state_timer_ > 1.5f) {
            wave_++;
            InitWave();
        }
        return;
    }

    // Input Handling
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        FireBullet();
    }
    if ((buttons & BTN_DOWN) && !(prev_buttons & BTN_DOWN)) {
        HyperspaceJump();
    }

    UpdateShip(dt, buttons);
    UpdateAsteroids(dt);
    UpdateBullets(dt);
    UpdateSaucer(dt);
    CheckCollisions();
    CheckWaveClear();
}

void Game113Asteroids::UpdateShip(float dt, uint32_t buttons) {
    float rot_speed = 4.2f;
    if (buttons & BTN_LEFT) {
        angle_ -= rot_speed * dt;
    }
    if (buttons & BTN_RIGHT) {
        angle_ += rot_speed * dt;
    }

    thrusting_ = (buttons & (BTN_UP | BTN_B));
    if (thrusting_) {
        float thrust = 14.0f;
        vx_ += std::cos(angle_) * thrust * dt;
        vy_ += std::sin(angle_) * thrust * dt;
    }

    // Vacuum friction
    vx_ *= (1.0f - 0.25f * dt);
    vy_ *= (1.0f - 0.25f * dt);

    px_ = WrapCoord(px_ + vx_ * dt);
    py_ = WrapCoord(py_ + vy_ * dt);
}

void Game113Asteroids::UpdateAsteroids(float dt) {
    for (int i = 0; i < MAX_ASTEROIDS; ++i) {
        if (!asteroids_[i].active) continue;
        asteroids_[i].x = WrapCoord(asteroids_[i].x + asteroids_[i].vx * dt);
        asteroids_[i].y = WrapCoord(asteroids_[i].y + asteroids_[i].vy * dt);
    }
}

void Game113Asteroids::UpdateBullets(float dt) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        bullets_[i].life -= dt;
        if (bullets_[i].life <= 0.0f) {
            bullets_[i].active = false;
            continue;
        }
        bullets_[i].x = WrapCoord(bullets_[i].x + bullets_[i].vx * dt);
        bullets_[i].y = WrapCoord(bullets_[i].y + bullets_[i].vy * dt);
    }
}

void Game113Asteroids::UpdateSaucer(float dt) {
    if (!saucer_.active) {
        saucer_spawn_timer_ -= dt;
        if (saucer_spawn_timer_ <= 0.0f) {
            saucer_.active = true;
            saucer_.x = 0.0f;
            saucer_.y = 3.5f;
            saucer_.vx = 4.0f;
            saucer_.shoot_timer = 2.0f;
        }
    } else {
        saucer_.x += saucer_.vx * dt;
        if (saucer_.x >= 16.0f) {
            saucer_.active = false;
            saucer_spawn_timer_ = 12.0f;
        }
    }
}

void Game113Asteroids::CheckCollisions() {
    // Bullet vs Asteroid
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;

        for (int a = 0; a < MAX_ASTEROIDS; ++a) {
            if (!asteroids_[a].active) continue;

            float hit_radius = (asteroids_[a].tier == 3) ? 1.6f : (asteroids_[a].tier == 2 ? 1.1f : 0.7f);
            float dx = WrapDiff(bullets_[b].x, asteroids_[a].x);
            float dy = WrapDiff(bullets_[b].y, asteroids_[a].y);

            if (dx < hit_radius && dy < hit_radius) {
                bullets_[b].active = false;
                SplitAsteroid(a);
                break;
            }
        }
    }

    // Bullet vs Saucer
    if (saucer_.active) {
        for (int b = 0; b < MAX_BULLETS; ++b) {
            if (!bullets_[b].active) continue;
            float dx = WrapDiff(bullets_[b].x, saucer_.x);
            float dy = WrapDiff(bullets_[b].y, saucer_.y);
            if (dx < 1.0f && dy < 1.0f) {
                bullets_[b].active = false;
                saucer_.active = false;
                saucer_spawn_timer_ = 14.0f;
                score_ += 200;
                break;
            }
        }
    }

    // Ship vs Asteroid
    for (int a = 0; a < MAX_ASTEROIDS; ++a) {
        if (!asteroids_[a].active) continue;

        float hit_radius = (asteroids_[a].tier == 3) ? 1.4f : (asteroids_[a].tier == 2 ? 1.0f : 0.6f);
        float dx = WrapDiff(px_, asteroids_[a].x);
        float dy = WrapDiff(py_, asteroids_[a].y);

        if (dx < hit_radius && dy < hit_radius) {
            state_ = STATE_PLAYER_EXPLODING;
            state_timer_ = 0.0f;
            SplitAsteroid(a);
            break;
        }
    }

    // Ship vs Saucer
    if (saucer_.active) {
        float dx = WrapDiff(px_, saucer_.x);
        float dy = WrapDiff(py_, saucer_.y);
        if (dx < 1.0f && dy < 1.0f) {
            state_ = STATE_PLAYER_EXPLODING;
            state_timer_ = 0.0f;
            saucer_.active = false;
        }
    }
}

void Game113Asteroids::CheckWaveClear() {
    bool any_asteroid = false;
    for (int i = 0; i < MAX_ASTEROIDS; ++i) {
        if (asteroids_[i].active) {
            any_asteroid = true;
            break;
        }
    }

    if (!any_asteroid) {
        state_ = STATE_WAVE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1000;
    }
}

void Game113Asteroids::Render(uint8_t* fb) {
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

    // 1. Asteroids
    for (int a = 0; a < MAX_ASTEROIDS; ++a) {
        if (!asteroids_[a].active) continue;

        int ax = static_cast<int>(std::round(asteroids_[a].x));
        int ay = static_cast<int>(std::round(asteroids_[a].y));

        if (asteroids_[a].tier == 3) {
            // Large diamond rock (Slate gray & cream edge)
            set_pixel(ax, ay, 180, 180, 190);
            set_pixel((ax + 1) % 16, ay, 140, 140, 150);
            set_pixel((ax + 15) % 16, ay, 140, 140, 150);
            set_pixel(ax, (ay + 1) % 16, 110, 110, 120);
            set_pixel(ax, (ay + 15) % 16, 210, 210, 220);
        } else if (asteroids_[a].tier == 2) {
            // Medium 2x2 rock
            set_pixel(ax, ay, 160, 160, 170);
            set_pixel((ax + 1) % 16, ay, 130, 130, 140);
            set_pixel(ax, (ay + 1) % 16, 110, 110, 120);
        } else {
            // Small 1-pixel fast meteorite
            set_pixel(ax, ay, 220, 220, 240);
        }
    }

    // 2. Flying Saucer
    if (saucer_.active) {
        int sx = static_cast<int>(std::round(saucer_.x));
        int sy = static_cast<int>(std::round(saucer_.y));
        set_pixel(sx, sy, 255, 60, 40);
        set_pixel((sx + 1) % 16, sy, 255, 200, 30);
        set_pixel((sx + 15) % 16, sy, 255, 200, 30);
        set_pixel(sx, (sy + 15) % 16, 0, 220, 255);
    }

    // 3. Bullets
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;
        int bx = static_cast<int>(std::round(bullets_[b].x));
        int by = static_cast<int>(std::round(bullets_[b].y));
        set_pixel(bx, by, 0, 255, 255);
    }

    // 4. Player Ship
    if (state_ == STATE_PLAYING) {
        int sx = static_cast<int>(std::round(px_));
        int sy = static_cast<int>(std::round(py_));

        // Nose tip
        int nx = static_cast<int>(std::round(px_ + std::cos(angle_) * 1.0f));
        int ny = static_cast<int>(std::round(py_ + std::sin(angle_) * 1.0f));
        set_pixel(WrapCoord(nx), WrapCoord(ny), 255, 255, 255);

        // Ship hull center
        set_pixel(sx, sy, 60, 160, 255);

        // Wings
        int w1x = static_cast<int>(std::round(px_ + std::cos(angle_ + 2.4f) * 1.0f));
        int w1y = static_cast<int>(std::round(py_ + std::sin(angle_ + 2.4f) * 1.0f));
        int w2x = static_cast<int>(std::round(px_ + std::cos(angle_ - 2.4f) * 1.0f));
        int w2y = static_cast<int>(std::round(py_ + std::sin(angle_ - 2.4f) * 1.0f));
        set_pixel(WrapCoord(w1x), WrapCoord(w1y), 40, 100, 220);
        set_pixel(WrapCoord(w2x), WrapCoord(w2y), 40, 100, 220);

        // Rocket exhaust plume
        if (thrusting_) {
            int tx = static_cast<int>(std::round(px_ - std::cos(angle_) * 1.2f));
            int ty = static_cast<int>(std::round(py_ - std::sin(angle_) * 1.2f));
            set_pixel(WrapCoord(tx), WrapCoord(ty), 255, 120, 20);
        }
    } else if (state_ == STATE_PLAYER_EXPLODING) {
        int sx = static_cast<int>(std::round(px_));
        int sy = static_cast<int>(std::round(py_));
        set_pixel(sx, sy, 255, 220, 50);
        set_pixel((sx + 1) % 16, (sy + 1) % 16, 255, 60, 30);
        set_pixel((sx + 15) % 16, (sy + 15) % 16, 255, 60, 30);
        set_pixel((sx + 1) % 16, (sy + 15) % 16, 255, 180, 0);
    }

    // 5. Lives HUD on top-left edge
    for (int l = 0; l < lives_; ++l) {
        set_pixel(l * 2, 0, 0, 220, 255);
    }
}

} // namespace arcade