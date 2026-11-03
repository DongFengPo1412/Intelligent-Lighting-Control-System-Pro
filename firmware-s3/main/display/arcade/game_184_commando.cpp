#include "game_184_commando.h"
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

Game184Commando::Game184Commando() {
    Reset();
}

void Game184Commando::Init() {
    Reset();
}

void Game184Commando::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game184Commando::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 13.0f;
    facing_x_ = 0.0f;
    facing_y_ = -1.0f;
    speed_ = 5.5f;
    grenades_ = 6;
    distance_ = 0.0f;
    target_distance_ = 160.0f + stage_ * 40.0f;
    gate_breached_ = false;

    for (int i = 0; i < MAX_BULLETS; ++i) bullets_[i].active = false;
    for (int i = 0; i < MAX_GRENADES; ++i) grenades_[i].active = false;

    SpawnWave();
}

void Game184Commando::SpawnWave() {
    enemies_[0] = {4.0f, 2.0f, 1.2f, 1.5f, 0, 1, true};
    enemies_[1] = {11.0f, 1.5f, -1.2f, 1.5f, 0, 1, true};
    enemies_[2] = {7.5f, 4.0f, 0.0f, 0.0f, 1, 2, true};
    enemies_[3] = {13.0f, 6.0f, -1.5f, 0.5f, 2, 1, true};

    pows_[0] = {3.0f, 5.0f, false, true};
    pows_[1] = {0.0f, 0.0f, false, false};
}

void Game184Commando::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_JOE_KILLED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                py_ = 13.0f;
                for (int i = 0; i < MAX_BULLETS; ++i) bullets_[i].active = false;
                for (int i = 0; i < MAX_GRENADES; ++i) grenades_[i].active = false;
            } else {
                state_ = STATE_GAME_OVER;
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if (((buttons & BTN_A) && !(prev_buttons & BTN_A)) ||
            ((buttons & BTN_B) && !(prev_buttons & BTN_B))) {
            Reset();
        }
        return;
    }

    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT)  dx -= 1.0f;
    if (buttons & BTN_RIGHT) dx += 1.0f;
    if (buttons & BTN_UP)    dy -= 1.0f;
    if (buttons & BTN_DOWN)  dy += 1.0f;

    if (dx != 0.0f || dy != 0.0f) {
        float inv = 1.0f / std::hypot(dx, dy);
        facing_x_ = dx * inv;
        facing_y_ = dy * inv;
        px_ += dx * speed_ * dt;
        py_ += dy * speed_ * dt;
    }

    if (distance_ < target_distance_ && py_ < 8.0f) {
        float scroll = 8.0f - py_;
        py_ = 8.0f;
        distance_ += scroll;
        for (int i = 0; i < MAX_ENEMIES; ++i) enemies_[i].y += scroll;
        for (int i = 0; i < MAX_POWS; ++i) pows_[i].y += scroll;
    }

    px_ = std::max(1.0f, std::min(14.0f, px_));
    py_ = std::max(2.0f, std::min(14.0f, py_));

    // Fire Machine Gun (Btn A)
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        for (int i = 0; i < MAX_BULLETS; ++i) {
            if (!bullets_[i].active) {
                bullets_[i] = {px_, py_, facing_x_ * 16.0f, facing_y_ * 16.0f, true};
                break;
            }
        }
    }

    // Lob Grenade (Btn B)
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B) && grenades_ > 0) {
        grenades_--;
        for (int i = 0; i < MAX_GRENADES; ++i) {
            if (!grenades_[i].active) {
                grenades_[i] = {
                    px_, py_,
                    px_ + facing_x_ * 4.0f, py_ + facing_y_ * 4.0f,
                    0.4f, true
                };
                break;
            }
        }
    }

    // Update Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        bullets_[i].x += bullets_[i].vx * dt;
        bullets_[i].y += bullets_[i].vy * dt;

        if (bullets_[i].x < 0.0f || bullets_[i].x > 15.0f || bullets_[i].y < 0.0f || bullets_[i].y > 15.0f) {
            bullets_[i].active = false;
            continue;
        }

        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (enemies_[e].alive && std::hypot(enemies_[e].x - bullets_[i].x, enemies_[e].y - bullets_[i].y) < 0.9f) {
                bullets_[i].active = false;
                if (enemies_[e].type != 1) { // Bunker blocks rifle shots
                    enemies_[e].alive = false;
                    score_ += 100;
                    if (enemies_[e].type == 2) {
                        grenades_ = std::min(static_cast<uint8_t>(8), static_cast<uint8_t>(grenades_ + 4));
                        score_ += 300;
                    }
                }
                break;
            }
        }
    }

    // Update Grenades
    for (int i = 0; i < MAX_GRENADES; ++i) {
        if (!grenades_[i].active) continue;
        grenades_[i].timer -= dt;
        grenades_[i].x += (grenades_[i].tx - grenades_[i].x) * 8.0f * dt;
        grenades_[i].y += (grenades_[i].ty - grenades_[i].y) * 8.0f * dt;

        if (grenades_[i].timer <= 0.0f) {
            grenades_[i].active = false;
            float gx = grenades_[i].tx;
            float gy = grenades_[i].ty;

            for (int e = 0; e < MAX_ENEMIES; ++e) {
                if (enemies_[e].alive && std::hypot(enemies_[e].x - gx, enemies_[e].y - gy) < 1.8f) {
                    enemies_[e].hp -= 2;
                    if (enemies_[e].hp <= 0) {
                        enemies_[e].alive = false;
                        score_ += (enemies_[e].type == 1) ? 300 : 150;
                    }
                }
            }

            if (distance_ >= target_distance_ && std::hypot(7.5f - gx, 1.5f - gy) < 2.5f) {
                gate_breached_ = true;
                state_ = STATE_STAGE_CLEAR;
                state_timer_ = 2.0f;
                score_ += 3000;
                return;
            }
        }
    }

    // POWs
    for (int i = 0; i < MAX_POWS; ++i) {
        if (pows_[i].active && !pows_[i].rescued && std::hypot(pows_[i].x - px_, pows_[i].y - py_) < 1.0f) {
            pows_[i].rescued = true;
            score_ += 500;
        }
    }

    // Enemies AI
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].alive) continue;
        if (enemies_[i].type != 1) {
            enemies_[i].x += enemies_[i].vx * dt;
            enemies_[i].y += enemies_[i].vy * dt;
        }

        if (std::hypot(enemies_[i].x - px_, enemies_[i].y - py_) < 0.8f) {
            lives_--;
            state_ = STATE_JOE_KILLED;
            state_timer_ = 1.0f;
            return;
        }
    }

    bool any_enemy_alive = false;
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].alive) { any_enemy_alive = true; break; }
    }
    if (!any_enemy_alive && distance_ < target_distance_) {
        SpawnWave();
    }
}

void Game184Commando::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Desert ground
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) set_pixel(x, y, 160, 130, 80);
    }

    // Iron gate
    if (distance_ >= target_distance_) {
        for (int x = 4; x <= 11; ++x) {
            set_pixel(x, 1, 80, 80, 90);
            set_pixel(x, 2, 140, 140, 150);
        }
        set_pixel(4, 0, 180, 40, 40);
        set_pixel(11, 0, 180, 40, 40);
    }

    // POWs
    for (int i = 0; i < MAX_POWS; ++i) {
        if (pows_[i].active && !pows_[i].rescued) {
            set_pixel(static_cast<int>(std::round(pows_[i].x)),
                      static_cast<int>(std::round(pows_[i].y)),
                      255, 255, 255);
        }
    }

    // Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].alive) {
            int ex = static_cast<int>(std::round(enemies_[i].x));
            int ey = static_cast<int>(std::round(enemies_[i].y));
            if (enemies_[i].type == 1) {
                set_pixel(ex, ey, 90, 70, 50);
                set_pixel(ex - 1, ey, 70, 50, 40);
                set_pixel(ex + 1, ey, 70, 50, 40);
                set_pixel(ex, ey - 1, 20, 20, 20);
            } else if (enemies_[i].type == 2) {
                set_pixel(ex, ey, 255, 200, 0);
            } else {
                set_pixel(ex, ey, 80, 140, 60);
            }
        }
    }

    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (bullets_[i].active) {
            set_pixel(static_cast<int>(std::round(bullets_[i].x)),
                      static_cast<int>(std::round(bullets_[i].y)),
                      255, 255, 140);
        }
    }

    // Grenades
    for (int i = 0; i < MAX_GRENADES; ++i) {
        if (grenades_[i].active) {
            set_pixel(static_cast<int>(std::round(grenades_[i].x)),
                      static_cast<int>(std::round(grenades_[i].y)),
                      40, 220, 40);
        }
    }

    // Joe
    int jx = static_cast<int>(std::round(px_));
    int jy = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(jx, jy, 40, 100, 220);
        set_pixel(jx, jy - 1, 255, 60, 40);
        set_pixel(jx + static_cast<int>(facing_x_), jy + static_cast<int>(facing_y_), 220, 220, 240);
    } else if (state_ == STATE_JOE_KILLED) {
        set_pixel(jx, jy, 255, 60, 0);
    }
}

} // namespace arcade
