#include "game_170_battlezone.h"
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

Game170Battlezone::Game170Battlezone() {
    Reset();
}

void Game170Battlezone::Init() {
    Reset();
}

void Game170Battlezone::Reset() {
    score_ = 0;
    lives_ = 3;
    sector_ = 1;

    obstacles_[0] = {4.0f, 5.0f};
    obstacles_[1] = {12.0f, 5.0f};
    obstacles_[2] = {8.0f, 8.0f};

    InitSector();
}

bool Game170Battlezone::IsBlockedByObstacle(float x, float y) const {
    for (int i = 0; i < NUM_OBSTACLES; ++i) {
        if (std::hypot(obstacles_[i].x - x, obstacles_[i].y - y) < 1.0f) {
            return true;
        }
    }
    return false;
}

void Game170Battlezone::InitSector() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 8.0f;
    py_ = 10.0f;
    angle_ = -1.5707963f; // Facing UP
    speed_ = 4.2f;
    rot_speed_ = 3.5f;
    fire_cooldown_ = 0.0f;

    for (int i = 0; i < MAX_SHELLS; ++i) shells_[i].active = false;
    for (int i = 0; i < MAX_ENEMIES; ++i) enemies_[i].alive = false;

    enemies_killed_ = 0;
    target_kills_ = 4 + sector_ * 2;

    SpawnEnemy(false);
}

void Game170Battlezone::SpawnEnemy(bool is_supertank) {
    int active_count = 0;
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].alive) active_count++;
    }
    if (active_count >= MAX_ENEMIES) return;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].alive) {
            float ex = (enemies_killed_ % 2 == 0) ? 2.0f : 14.0f;
            float ey = (enemies_killed_ % 4 < 2) ? 2.0f : 8.0f;
            enemies_[i] = {static_cast<int8_t>(i), ex, ey, 1.5707963f, is_supertank ? 2.2f : 1.5f, 2.5f, is_supertank, true};
            break;
        }
    }
}

void Game170Battlezone::FireCannon() {
    if (fire_cooldown_ > 0.0f || state_ != STATE_PLAYING) return;

    for (int i = 0; i < MAX_SHELLS; ++i) {
        if (!shells_[i].active) {
            float shell_speed = 12.0f;
            shells_[i].x = px_ + std::cos(angle_) * 0.8f;
            shells_[i].y = py_ + std::sin(angle_) * 0.8f;
            shells_[i].vx = std::cos(angle_) * shell_speed;
            shells_[i].vy = std::sin(angle_) * shell_speed;
            shells_[i].is_player = true;
            shells_[i].life = 1.2f;
            shells_[i].active = true;
            fire_cooldown_ = 0.35f;
            break;
        }
    }
}

void Game170Battlezone::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_SECTOR_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            sector_++;
            InitSector();
        }
        return;
    }

    if (state_ == STATE_TANK_EXPLODING) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 8.0f;
                py_ = 10.0f;
                angle_ = -1.5707963f;
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

    if (buttons & BTN_LEFT)  angle_ -= rot_speed_ * dt;
    if (buttons & BTN_RIGHT) angle_ += rot_speed_ * dt;

    float move_v = 0.0f;
    if (buttons & BTN_UP)   move_v += speed_;
    if (buttons & BTN_DOWN) move_v -= speed_ * 0.6f;

    if (move_v != 0.0f) {
        float new_px = px_ + std::cos(angle_) * move_v * dt;
        float new_py = py_ + std::sin(angle_) * move_v * dt;
        if (!IsBlockedByObstacle(new_px, new_py)) {
            px_ = std::max(1.0f, std::min(14.5f, new_px));
            py_ = std::max(2.5f, std::min(14.5f, new_py));
        }
    }

    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        FireCannon();
    }

    // Shells
    for (int i = 0; i < MAX_SHELLS; ++i) {
        if (!shells_[i].active) continue;

        shells_[i].x += shells_[i].vx * dt;
        shells_[i].y += shells_[i].vy * dt;
        shells_[i].life -= dt;

        if (IsBlockedByObstacle(shells_[i].x, shells_[i].y) || shells_[i].life <= 0.0f ||
            shells_[i].x < 0.0f || shells_[i].x > 15.0f || shells_[i].y < 0.0f || shells_[i].y > 15.0f) {
            shells_[i].active = false;
            continue;
        }

        if (shells_[i].is_player) {
            for (int e = 0; e < MAX_ENEMIES; ++e) {
                if (enemies_[e].alive && std::hypot(enemies_[e].x - shells_[i].x, enemies_[e].y - shells_[i].y) < 1.1f) {
                    enemies_[e].alive = false;
                    enemies_killed_++;
                    score_ += enemies_[e].is_supertank ? 1000 : 500;
                    shells_[i].active = false;

                    if (enemies_killed_ >= target_kills_) {
                        state_ = STATE_SECTOR_CLEAR;
                        state_timer_ = 2.0f;
                        score_ += 2500;
                    } else {
                        SpawnEnemy(enemies_killed_ % 2 == 1);
                    }
                    break;
                }
            }
        } else {
            if (std::hypot(px_ - shells_[i].x, py_ - shells_[i].y) < 0.9f) {
                shells_[i].active = false;
                lives_--;
                state_ = STATE_TANK_EXPLODING;
                state_timer_ = 1.0f;
                return;
            }
        }
    }

    // Enemies
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].alive) continue;

        float edx = px_ - enemies_[e].x;
        float edy = py_ - enemies_[e].y;
        float target_angle = std::atan2(edy, edx);

        float diff = std::fmod(target_angle - enemies_[e].angle + 3.1415926f, 6.2831853f) - 3.1415926f;
        enemies_[e].angle += (diff > 0 ? 1.0f : -1.0f) * std::min(std::abs(diff), 2.0f * dt);

        float dist = std::hypot(edx, edy);
        if (dist > 3.0f) {
            float new_ex = enemies_[e].x + std::cos(enemies_[e].angle) * enemies_[e].speed * dt;
            float new_ey = enemies_[e].y + std::sin(enemies_[e].angle) * enemies_[e].speed * dt;
            if (!IsBlockedByObstacle(new_ex, new_ey)) {
                enemies_[e].x = std::max(1.0f, std::min(14.5f, new_ex));
                enemies_[e].y = std::max(2.5f, std::min(14.5f, new_ey));
            }
        }

        enemies_[e].fire_timer -= dt;
        if (enemies_[e].fire_timer <= 0.0f && dist < 12.0f) {
            for (int s = 0; s < MAX_SHELLS; ++s) {
                if (!shells_[s].active) {
                    float shell_speed = 8.0f;
                    shells_[s].x = enemies_[e].x + std::cos(enemies_[e].angle) * 0.8f;
                    shells_[s].y = enemies_[e].y + std::sin(enemies_[e].angle) * 0.8f;
                    shells_[s].vx = std::cos(enemies_[e].angle) * shell_speed;
                    shells_[s].vy = std::sin(enemies_[e].angle) * shell_speed;
                    shells_[s].is_player = false;
                    shells_[s].life = 1.5f;
                    shells_[s].active = true;
                    enemies_[e].fire_timer = 3.0f;
                    break;
                }
            }
        }

        if (dist < 1.0f) {
            lives_--;
            state_ = STATE_TANK_EXPLODING;
            state_timer_ = 1.0f;
            return;
        }
    }
}

void Game170Battlezone::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Radar perimeter bar (y=1)
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 1, 0, 100, 40);
    }

    // Radar blips
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (enemies_[e].alive) {
            float rel_angle = std::atan2(enemies_[e].y - py_, enemies_[e].x - px_) - angle_;
            rel_angle = std::fmod(rel_angle + 3.1415926f, 6.2831853f) - 3.1415926f;
            int rx = static_cast<int>(std::round(8.0f + (rel_angle / 3.1415926f) * 7.0f));
            rx = std::max(0, std::min(15, rx));
            set_pixel(rx, 0, 255, 30, 30);
        }
    }

    // Geometric Obstacles
    for (int i = 0; i < NUM_OBSTACLES; ++i) {
        int ox = static_cast<int>(std::round(obstacles_[i].x));
        int oy = static_cast<int>(std::round(obstacles_[i].y));
        set_pixel(ox, oy, 40, 200, 220);
        set_pixel(ox + 1, oy, 20, 120, 140);
    }

    // Enemies
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (enemies_[e].alive) {
            int ex = static_cast<int>(std::round(enemies_[e].x));
            int ey = static_cast<int>(std::round(enemies_[e].y));
            if (enemies_[e].is_supertank) set_pixel(ex, ey, 255, 60, 60);
            else set_pixel(ex, ey, 220, 120, 40);
        }
    }

    // Shells
    for (int s = 0; s < MAX_SHELLS; ++s) {
        if (shells_[s].active) {
            int sx = static_cast<int>(std::round(shells_[s].x));
            int sy = static_cast<int>(std::round(shells_[s].y));
            if (shells_[s].is_player) set_pixel(sx, sy, 255, 255, 255);
            else set_pixel(sx, sy, 255, 100, 0);
        }
    }

    // Player Tank
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_SECTOR_CLEAR) {
        set_pixel(px, py, 0, 255, 100);
        int tx = static_cast<int>(std::round(px_ + std::cos(angle_) * 1.1f));
        int ty = static_cast<int>(std::round(py_ + std::sin(angle_) * 1.1f));
        set_pixel(tx, ty, 100, 255, 150);
    } else if (state_ == STATE_TANK_EXPLODING) {
        set_pixel(px, py, 255, 50, 0);
    }
}

} // namespace arcade

