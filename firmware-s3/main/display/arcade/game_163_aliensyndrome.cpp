#include "game_163_aliensyndrome.h"
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

Game163AlienSyndrome::Game163AlienSyndrome() {
    Reset();
}

void Game163AlienSyndrome::Init() {
    Reset();
}

void Game163AlienSyndrome::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game163AlienSyndrome::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 2.0f;
    py_ = 2.0f;
    facing_dx_ = 1.0f;
    facing_dy_ = 0.0f;
    speed_ = 5.0f;
    has_laser_ = false;
    fire_cooldown_ = 0.0f;
    exit_open_ = false;
    evac_timer_ = 15.0f;
    exit_x_ = 8.0f;
    exit_y_ = 0.0f;

    weapon_pod_x_ = 8.0f;
    weapon_pod_y_ = 4.0f;
    weapon_pod_collected_ = false;

    comrades_rescued_ = 0;
    comrades_[0] = {13.0f, 2.0f, false};
    comrades_[1] = {2.0f, 13.0f, false};
    comrades_[2] = {13.0f, 13.0f, false};
    comrades_[3] = {8.0f, 8.0f, false};

    for (int i = 0; i < MAX_BULLETS; ++i) bullets_[i].active = false;
    for (int i = 0; i < MAX_ALIENS; ++i) aliens_[i].alive = false;

    aliens_[0] = {0, 10.0f, 5.0f, 2.2f, true};
    aliens_[1] = {1, 5.0f, 10.0f, 2.0f, true};
    alien_spawn_timer_ = 1.5f;
}

void Game163AlienSyndrome::FireWeapon() {
    if (fire_cooldown_ > 0.0f || (state_ != STATE_PLAYING && state_ != STATE_EVACUATION)) return;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].x = px_ + facing_dx_ * 0.8f;
            bullets_[i].y = py_ + facing_dy_ * 0.8f;
            bullets_[i].vx = facing_dx_ * 15.0f;
            bullets_[i].vy = facing_dy_ * 15.0f;
            bullets_[i].is_laser = has_laser_;
            bullets_[i].life = 1.0f;
            bullets_[i].active = true;
            fire_cooldown_ = has_laser_ ? 0.15f : 0.25f;
            break;
        }
    }
}

void Game163AlienSyndrome::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_MISSION_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            level_++;
            InitLevel();
        }
        return;
    }

    if (state_ == STATE_PLAYER_DIED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = exit_open_ ? STATE_EVACUATION : STATE_PLAYING;
                px_ = 2.0f;
                py_ = 2.0f;
                has_laser_ = false;
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

    if (state_ == STATE_EVACUATION) {
        evac_timer_ -= dt;
        if (evac_timer_ <= 0.0f) {
            lives_--;
            state_ = STATE_PLAYER_DIED;
            state_timer_ = 1.5f;
            return;
        }
    }

    // Player Movement
    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT) {
        dx -= 1.0f; facing_dx_ = -1.0f; facing_dy_ = 0.0f;
    } else if (buttons & BTN_RIGHT) {
        dx += 1.0f; facing_dx_ = 1.0f; facing_dy_ = 0.0f;
    } else if (buttons & BTN_UP) {
        dy -= 1.0f; facing_dx_ = 0.0f; facing_dy_ = -1.0f;
    } else if (buttons & BTN_DOWN) {
        dy += 1.0f; facing_dx_ = 0.0f; facing_dy_ = 1.0f;
    }

    if (dx != 0.0f || dy != 0.0f) {
        px_ += dx * speed_ * dt;
        py_ += dy * speed_ * dt;
    }

    px_ = std::max(1.0f, std::min(14.0f, px_));
    py_ = std::max(1.0f, std::min(14.0f, py_));

    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        FireWeapon();
    }

    // Key B: Smart flare
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        for (int i = 0; i < MAX_ALIENS; ++i) {
            if (aliens_[i].alive && std::hypot(aliens_[i].x - px_, aliens_[i].y - py_) < 4.0f) {
                aliens_[i].alive = false;
                score_ += 150;
            }
        }
    }

    // Weapon pod interaction
    if (!weapon_pod_collected_ && std::hypot(weapon_pod_x_ - px_, weapon_pod_y_ - py_) < 1.0f) {
        weapon_pod_collected_ = true;
        has_laser_ = true;
        score_ += 300;
    }

    // Comrades rescue
    for (int i = 0; i < NUM_COMRADES; ++i) {
        if (!comrades_[i].rescued && std::hypot(comrades_[i].x - px_, comrades_[i].y - py_) < 1.0f) {
            comrades_[i].rescued = true;
            comrades_rescued_++;
            score_ += 200;

            if (comrades_rescued_ >= NUM_COMRADES) {
                exit_open_ = true;
                state_ = STATE_EVACUATION;
                score_ += 1000;
            }
        }
    }

    // Exit reach
    if (exit_open_ && std::hypot(exit_x_ - px_, exit_y_ - py_) < 1.2f) {
        state_ = STATE_MISSION_CLEAR;
        state_timer_ = 2.0f;
        score_ += static_cast<uint32_t>(evac_timer_ * 100.0f) + 2000;
        return;
    }

    // Bullets update
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        bullets_[i].x += bullets_[i].vx * dt;
        bullets_[i].y += bullets_[i].vy * dt;
        bullets_[i].life -= dt;

        if (bullets_[i].life <= 0.0f || bullets_[i].x < 0.0f || bullets_[i].x > 15.0f ||
            bullets_[i].y < 0.0f || bullets_[i].y > 15.0f) {
            bullets_[i].active = false;
            continue;
        }

        for (int a = 0; a < MAX_ALIENS; ++a) {
            if (aliens_[a].alive && std::hypot(aliens_[a].x - bullets_[i].x, aliens_[a].y - bullets_[i].y) < 1.0f) {
                aliens_[a].alive = false;
                score_ += 100;
                if (!bullets_[i].is_laser) {
                    bullets_[i].active = false;
                }
                break;
            }
        }
    }

    // Spawn aliens
    int active_aliens = 0;
    for (int a = 0; a < MAX_ALIENS; ++a) {
        if (aliens_[a].alive) active_aliens++;
    }

    alien_spawn_timer_ -= dt;
    if (alien_spawn_timer_ <= 0.0f && active_aliens < MAX_ALIENS) {
        for (int a = 0; a < MAX_ALIENS; ++a) {
            if (!aliens_[a].alive) {
                aliens_[a] = {static_cast<int8_t>(a),
                              (a % 2 == 0) ? 14.0f : 1.0f,
                              (a % 2 == 0) ? 14.0f : 8.0f,
                              2.2f + level_ * 0.3f,
                              true};
                break;
            }
        }
        alien_spawn_timer_ = 2.0f;
    }

    // Update aliens
    for (int a = 0; a < MAX_ALIENS; ++a) {
        if (!aliens_[a].alive) continue;

        float adx = px_ - aliens_[a].x;
        float ady = py_ - aliens_[a].y;
        float dist = std::hypot(adx, ady);
        if (dist > 0.2f) {
            aliens_[a].x += (adx / dist) * aliens_[a].speed * dt;
            aliens_[a].y += (ady / dist) * aliens_[a].speed * dt;
        }

        if (std::hypot(aliens_[a].x - px_, aliens_[a].y - py_) < 0.8f) {
            lives_--;
            state_ = STATE_PLAYER_DIED;
            state_timer_ = 1.0f;
            return;
        }
    }
}

void Game163AlienSyndrome::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Border ribs
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 0, 40, 20, 50);
        set_pixel(x, 15, 40, 20, 50);
    }
    for (int y = 0; y < 16; ++y) {
        set_pixel(0, y, 40, 20, 50);
        set_pixel(15, y, 40, 20, 50);
    }

    // Exit Airlock
    if (exit_open_) {
        set_pixel(7, 0, 0, 255, 120);
        set_pixel(8, 0, 0, 255, 255);
        set_pixel(9, 0, 0, 255, 120);
    } else {
        set_pixel(8, 0, 180, 40, 40);
    }

    // Weapon pod
    if (!weapon_pod_collected_) {
        int wx = static_cast<int>(std::round(weapon_pod_x_));
        int wy = static_cast<int>(std::round(weapon_pod_y_));
        set_pixel(wx, wy, 255, 220, 0);
    }

    // Comrades in cocoons
    for (int i = 0; i < NUM_COMRADES; ++i) {
        if (!comrades_[i].rescued) {
            int cx = static_cast<int>(std::round(comrades_[i].x));
            int cy = static_cast<int>(std::round(comrades_[i].y));
            set_pixel(cx, cy, 255, 180, 180);
        }
    }

    // Aliens
    for (int a = 0; a < MAX_ALIENS; ++a) {
        if (aliens_[a].alive) {
            int ax = static_cast<int>(std::round(aliens_[a].x));
            int ay = static_cast<int>(std::round(aliens_[a].y));
            set_pixel(ax, ay, 220, 30, 80);
        }
    }

    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (bullets_[i].active) {
            int bx = static_cast<int>(std::round(bullets_[i].x));
            int by = static_cast<int>(std::round(bullets_[i].y));
            if (bullets_[i].is_laser) {
                set_pixel(bx, by, 0, 255, 255);
            } else {
                set_pixel(bx, by, 255, 255, 100);
            }
        }
    }

    // Ricky Trooper
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_EVACUATION || state_ == STATE_MISSION_CLEAR) {
        if (has_laser_) {
            set_pixel(px, py, 0, 240, 255);
        } else {
            set_pixel(px, py, 255, 255, 255);
        }
    } else if (state_ == STATE_PLAYER_DIED) {
        set_pixel(px, py, 255, 80, 20);
    }
}

} // namespace arcade

