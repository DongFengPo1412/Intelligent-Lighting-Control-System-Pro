#include "game_164_robotron.h"
#include <cstring>
#include <cmath>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = (1 << 0);
static constexpr uint16_t BTN_DOWN  = (1 << 1);
static constexpr uint16_t BTN_LEFT  = (1 << 2);
static constexpr uint16_t BTN_RIGHT = (1 << 3);
static constexpr uint16_t BTN_A     = (1 << 4);
static constexpr uint16_t BTN_B     = (1 << 5);

Game164Robotron::Game164Robotron() {
    Reset();
}

void Game164Robotron::Init() {
    Reset();
}

void Game164Robotron::Reset() {
    score_ = 0;
    lives_ = 3;
    wave_ = 1;
    InitWave();
}

void Game164Robotron::InitWave() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 7.5f;
    facing_dx_ = 0.0f;
    facing_dy_ = -1.0f;
    speed_ = 5.5f;
    fire_cooldown_ = 0.0f;
    emp_charges_ = 1;

    for (int i = 0; i < MAX_LASERS; ++i) lasers_[i].active = false;

    // Humans
    humans_[0] = {3.0f, 4.0f, 1.2f, 0.8f, true, false};
    humans_[1] = {12.0f, 4.0f, -1.0f, 1.1f, true, false};
    humans_[2] = {7.5f, 12.0f, 1.1f, -1.0f, true, false};

    // Hulks (Indestructible)
    hulks_[0] = {2.0f, 2.0f, 0.8f, 0.6f};
    hulks_[1] = {13.0f, 13.0f, -0.7f, -0.8f};

    // Grunts
    total_grunts_ = std::min(MAX_GRUNTS, 6 + wave_ * 2);
    for (int i = 0; i < total_grunts_; ++i) {
        float gx = (i % 2 == 0) ? 1.0f : 14.0f;
        float gy = 2.0f + static_cast<float>((i * 5) % 12);
        grunts_[i] = {gx, gy, 1.8f + wave_ * 0.25f, true};
    }
}

void Game164Robotron::FireLaser() {
    if (fire_cooldown_ > 0.0f || state_ != STATE_PLAYING) return;

    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) {
            lasers_[i].x = px_ + facing_dx_ * 0.8f;
            lasers_[i].y = py_ + facing_dy_ * 0.8f;
            lasers_[i].vx = facing_dx_ * 16.0f;
            lasers_[i].vy = facing_dy_ * 16.0f;
            lasers_[i].life = 0.8f;
            lasers_[i].active = true;
            fire_cooldown_ = 0.16f;
            break;
        }
    }
}

void Game164Robotron::TriggerEmp() {
    if (emp_charges_ > 0 && state_ == STATE_PLAYING) {
        emp_charges_--;
        for (int i = 0; i < total_grunts_; ++i) {
            if (grunts_[i].alive) {
                grunts_[i].alive = false;
                score_ += 100;
            }
        }
    }
}

void Game164Robotron::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_WAVE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            wave_++;
            InitWave();
        }
        return;
    }

    if (state_ == STATE_PLAYER_DIED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                py_ = 7.5f;
                emp_charges_ = 1;
            } else {
                state_ = STATE_GAME_OVER;
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

    if (fire_cooldown_ > 0.0f) fire_cooldown_ -= dt;

    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT)  dx -= 1.0f;
    if (buttons & BTN_RIGHT) dx += 1.0f;
    if (buttons & BTN_UP)    dy -= 1.0f;
    if (buttons & BTN_DOWN)  dy += 1.0f;

    if (dx != 0.0f || dy != 0.0f) {
        float len_d = std::hypot(dx, dy);
        facing_dx_ = dx / len_d;
        facing_dy_ = dy / len_d;
        px_ += (dx / len_d) * speed_ * dt;
        py_ += (dy / len_d) * speed_ * dt;
    }

    px_ = std::max(1.0f, std::min(14.0f, px_));
    py_ = std::max(1.0f, std::min(14.0f, py_));

    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        FireLaser();
    }
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        TriggerEmp();
    }

    // Humans
    for (int i = 0; i < NUM_HUMANS; ++i) {
        if (humans_[i].alive && !humans_[i].rescued) {
            humans_[i].x += humans_[i].vx * dt;
            humans_[i].y += humans_[i].vy * dt;
            if (humans_[i].x <= 1.0f || humans_[i].x >= 14.0f) humans_[i].vx = -humans_[i].vx;
            if (humans_[i].y <= 1.0f || humans_[i].y >= 14.0f) humans_[i].vy = -humans_[i].vy;

            if (std::hypot(humans_[i].x - px_, humans_[i].y - py_) < 1.0f) {
                humans_[i].rescued = true;
                score_ += 1000;
            }
        }
    }

    // Hulks (Indestructible)
    for (int i = 0; i < NUM_HULKS; ++i) {
        hulks_[i].x += hulks_[i].vx * dt;
        hulks_[i].y += hulks_[i].vy * dt;
        if (hulks_[i].x <= 1.0f || hulks_[i].x >= 14.0f) hulks_[i].vx = -hulks_[i].vx;
        if (hulks_[i].y <= 1.0f || hulks_[i].y >= 14.0f) hulks_[i].vy = -hulks_[i].vy;

        for (int h = 0; h < NUM_HUMANS; ++h) {
            if (humans_[h].alive && !humans_[h].rescued) {
                if (std::hypot(hulks_[i].x - humans_[h].x, hulks_[i].y - humans_[h].y) < 0.9f) {
                    humans_[h].alive = false;
                }
            }
        }

        if (std::hypot(hulks_[i].x - px_, hulks_[i].y - py_) < 0.9f) {
            lives_--;
            state_ = STATE_PLAYER_DIED;
            state_timer_ = 1.0f;
            return;
        }
    }

    // Lasers
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) continue;

        lasers_[i].x += lasers_[i].vx * dt;
        lasers_[i].y += lasers_[i].vy * dt;
        lasers_[i].life -= dt;

        if (lasers_[i].life <= 0.0f || lasers_[i].x < 0.0f || lasers_[i].x > 15.0f ||
            lasers_[i].y < 0.0f || lasers_[i].y > 15.0f) {
            lasers_[i].active = false;
            continue;
        }

        // Hulk knockback
        for (int h = 0; h < NUM_HULKS; ++h) {
            if (std::hypot(hulks_[h].x - lasers_[i].x, hulks_[h].y - lasers_[i].y) < 1.0f) {
                hulks_[h].x += (lasers_[i].vx / 16.0f) * 0.6f;
                hulks_[h].y += (lasers_[i].vy / 16.0f) * 0.6f;
                hulks_[h].x = std::max(1.0f, std::min(14.0f, hulks_[h].x));
                hulks_[h].y = std::max(1.0f, std::min(14.0f, hulks_[h].y));
                lasers_[i].active = false;
                break;
            }
        }

        if (!lasers_[i].active) continue;

        // Grunts
        for (int g = 0; g < total_grunts_; ++g) {
            if (grunts_[g].alive && std::hypot(grunts_[g].x - lasers_[i].x, grunts_[g].y - lasers_[i].y) < 1.0f) {
                grunts_[g].alive = false;
                lasers_[i].active = false;
                score_ += 100;
                break;
            }
        }
    }

    // Grunts
    int active_grunts = 0;
    for (int g = 0; g < total_grunts_; ++g) {
        if (!grunts_[g].alive) continue;
        active_grunts++;

        float gdx = px_ - grunts_[g].x;
        float gdy = py_ - grunts_[g].y;
        float dist = std::hypot(gdx, gdy);
        if (dist > 0.1f) {
            grunts_[g].x += (gdx / dist) * grunts_[g].speed * dt;
            grunts_[g].y += (gdy / dist) * grunts_[g].speed * dt;
        }

        if (std::hypot(grunts_[g].x - px_, grunts_[g].y - py_) < 0.8f) {
            lives_--;
            state_ = STATE_PLAYER_DIED;
            state_timer_ = 1.0f;
            return;
        }
    }

    if (active_grunts == 0) {
        state_ = STATE_WAVE_CLEAR;
        state_timer_ = 1.5f;
        score_ += 2000;
    }
}

void Game164Robotron::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Arena walls
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 0, 80, 0, 180);
        set_pixel(x, 15, 80, 0, 180);
    }
    for (int y = 0; y < 16; ++y) {
        set_pixel(0, y, 80, 0, 180);
        set_pixel(15, y, 80, 0, 180);
    }

    // Humans
    for (int i = 0; i < NUM_HUMANS; ++i) {
        if (humans_[i].alive && !humans_[i].rescued) {
            int hx = static_cast<int>(std::round(humans_[i].x));
            int hy = static_cast<int>(std::round(humans_[i].y));
            set_pixel(hx, hy, 0, 240, 255);
        }
    }

    // Hulks
    for (int i = 0; i < NUM_HULKS; ++i) {
        int kx = static_cast<int>(std::round(hulks_[i].x));
        int ky = static_cast<int>(std::round(hulks_[i].y));
        set_pixel(kx, ky, 0, 220, 40);
        set_pixel(kx + 1, ky, 0, 160, 20);
    }

    // Grunts
    for (int i = 0; i < total_grunts_; ++i) {
        if (grunts_[i].alive) {
            int gx = static_cast<int>(std::round(grunts_[i].x));
            int gy = static_cast<int>(std::round(grunts_[i].y));
            set_pixel(gx, gy, 255, 30, 30);
        }
    }

    // Lasers
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (lasers_[i].active) {
            int lx = static_cast<int>(std::round(lasers_[i].x));
            int ly = static_cast<int>(std::round(lasers_[i].y));
            set_pixel(lx, ly, 255, 255, 120);
        }
    }

    // Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_WAVE_CLEAR) {
        set_pixel(px, py, 255, 255, 255);
        set_pixel(px, py - 1, 255, 140, 0);
    } else if (state_ == STATE_PLAYER_DIED) {
        set_pixel(px, py, 255, 40, 0);
    }
}

} // namespace arcade

