#include "game_149_gaplus.h"
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

Game149Gaplus::Game149Gaplus() {
    Reset();
}

void Game149Gaplus::Init() {
    Reset();
}

void Game149Gaplus::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game149Gaplus::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 13.0f;
    beam_active_ = false;
    beam_energy_ = 1.0f;
    escorts_count_ = 0;
    fleet_sway_ = 0.0f;

    for (int i = 0; i < MAX_LASERS; ++i) lasers_[i].active = false;
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) enemy_bullets_[i].active = false;

    // Fleet of 8 enemies (2 rows of 4)
    int idx = 0;
    for (int r = 0; r < 2; ++r) {
        for (int c = 0; c < 4; ++c) {
            float bx = 3.0f + c * 3.0f;
            float by = 2.0f + r * 2.0f;
            enemies_[idx] = {bx, by, bx, by, 0, 0.0f, 0.0f, 0.0f, true};
            idx++;
        }
    }
}

void Game149Gaplus::LoseLife() {
    lives_--;
    state_ = STATE_PLAYER_HIT;
    state_timer_ = 0.0f;
}

void Game149Gaplus::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // 1. Movement
        float move_speed = 6.0f;
        float dx = 0.0f;
        float dy = 0.0f;
        if (buttons & BTN_LEFT)  dx -= move_speed;
        if (buttons & BTN_RIGHT) dx += move_speed;
        if (buttons & BTN_UP)    dy -= move_speed;
        if (buttons & BTN_DOWN)  dy += move_speed;

        px_ = std::max(1.5f, std::min(14.5f, px_ + dx * dt));
        py_ = std::max(8.5f, std::min(14.5f, py_ + dy * dt));

        // 2. Tractor Beam
        if (buttons & BTN_B) {
            if (beam_energy_ > 0.05f) {
                beam_active_ = true;
                beam_energy_ = std::max(0.0f, beam_energy_ - dt * 0.4f);
            } else {
                beam_active_ = false;
            }
        } else {
            beam_active_ = false;
            beam_energy_ = std::min(1.0f, beam_energy_ + dt * 0.3f);
        }

        // 3. Fire Lasers
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            // Main laser
            for (int i = 0; i < MAX_LASERS; ++i) {
                if (!lasers_[i].active) {
                    lasers_[i] = {px_, py_ - 1.0f, -14.0f, true};
                    break;
                }
            }
            // Escort lasers
            static const float offsets[4] = {-1.8f, 1.8f, -3.2f, 3.2f};
            for (int e = 0; e < escorts_count_; ++e) {
                for (int i = 0; i < MAX_LASERS; ++i) {
                    if (!lasers_[i].active) {
                        lasers_[i] = {px_ + offsets[e], py_ - 0.5f, -14.0f, true};
                        break;
                    }
                }
            }
        }

        // 4. Update Lasers
        for (int i = 0; i < MAX_LASERS; ++i) {
            if (!lasers_[i].active) continue;
            lasers_[i].y += lasers_[i].vy * dt;
            if (lasers_[i].y < 0.0f) {
                lasers_[i].active = false;
                continue;
            }

            for (int e = 0; e < MAX_ENEMIES; ++e) {
                if (enemies_[e].alive && enemies_[e].state != 2) {
                    if (std::abs(lasers_[i].x - enemies_[e].x) < 0.9f &&
                        std::abs(lasers_[i].y - enemies_[e].y) < 0.9f) {
                        enemies_[e].alive = false;
                        lasers_[i].active = false;
                        score_ += 150;
                        break;
                    }
                }
            }
        }

        // 5. Update Swarm
        fleet_sway_ += dt * 2.0f;
        float sway_offset = std::sin(fleet_sway_) * 1.5f;

        int diving_count = 0;
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (enemies_[i].alive && enemies_[i].state == 1) diving_count++;
        }

        if (diving_count < 2) {
            for (int i = 0; i < MAX_ENEMIES; ++i) {
                if (enemies_[i].alive && enemies_[i].state == 0) {
                    enemies_[i].state = 1;
                    enemies_[i].dive_t = 0.0f;
                    break;
                }
            }
        }

        for (int i = 0; i < MAX_ENEMIES; ++i) {
            auto& e = enemies_[i];
            if (!e.alive) continue;

            if (e.state == 0) {
                e.x = e.base_x + sway_offset;
                e.y = e.base_y;
            } else if (e.state == 1) {
                e.dive_t += dt;
                e.y += 4.5f * dt;
                e.x += std::sin(e.dive_t * 4.0f) * 5.0f * dt;
                e.x = std::max(1.0f, std::min(14.5f, e.x));

                if (e.y > 15.5f) {
                    e.y = 0.0f;
                    e.state = 0;
                }

                if (beam_active_ && escorts_count_ < MAX_ESCORTS) {
                    float half_w = 0.8f + (py_ - e.y) * 0.18f;
                    if (std::abs(e.x - px_) <= half_w && e.y < py_) {
                        e.state = 2; // captured_suck
                    }
                }
            } else if (e.state == 2) {
                e.x += (px_ - e.x) * std::min(1.0f, dt * 8.0f);
                e.y += 10.0f * dt;
                if (e.y >= py_ - 0.5f) {
                    e.alive = false;
                    escorts_count_ = std::min(MAX_ESCORTS, escorts_count_ + 1);
                    score_ += 500;
                }
            }
        }

        // 6. Bullets vs Escort Shields / Player
        for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
            if (!enemy_bullets_[i].active) continue;
            enemy_bullets_[i].y += enemy_bullets_[i].vy * dt;
            if (enemy_bullets_[i].y > 15.5f) {
                enemy_bullets_[i].active = false;
                continue;
            }

            if (escorts_count_ > 0) {
                if (std::abs(enemy_bullets_[i].y - py_) < 1.0f &&
                    std::abs(enemy_bullets_[i].x - px_) < 3.5f) {
                    escorts_count_--;
                    enemy_bullets_[i].active = false;
                    continue;
                }
            }

            if (std::abs(enemy_bullets_[i].x - px_) < 0.8f &&
                std::abs(enemy_bullets_[i].y - py_) < 0.8f) {
                LoseLife();
                return;
            }
        }

        // 7. Enemy collision with Player / Escort Shield
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            auto& e = enemies_[i];
            if (!e.alive || e.state == 2) continue;

            if (escorts_count_ > 0) {
                if (std::abs(e.y - py_) < 1.0f && std::abs(e.x - px_) < 3.0f) {
                    escorts_count_--;
                    e.alive = false;
                    score_ += 100;
                    continue;
                }
            }

            if (std::abs(e.x - px_) < 0.8f && std::abs(e.y - py_) < 0.8f) {
                LoseLife();
                return;
            }
        }

        // 8. Wave Clear
        bool all_dead = true;
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (enemies_[i].alive) {
                all_dead = false;
                break;
            }
        }
        if (all_dead) {
            score_ += 1500;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
        }

    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_PLAYER_HIT) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else {
                if (lives_ > 0) {
                    px_ = 7.5f;
                    py_ = 13.0f;
                    escorts_count_ = 0;
                    beam_active_ = false;
                    state_ = STATE_PLAYING;
                    state_timer_ = 0.0f;
                } else {
                    state_ = STATE_GAME_OVER;
                    state_timer_ = 0.0f;
                }
            }
        }
    } else if (state_ == STATE_GAME_OVER) {
        state_timer_ += dt;
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
    }
}

void Game149Gaplus::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Stars
    set_pixel(3, 4, 30, 40, 80);
    set_pixel(12, 8, 30, 40, 80);
    set_pixel(6, 12, 40, 50, 90);

    // Tractor Beam
    if (beam_active_) {
        int py_i = static_cast<int>(std::round(py_));
        int px_i = static_cast<int>(std::round(px_));
        for (int y = std::max(0, py_i - 8); y < py_i; ++y) {
            int half_w = static_cast<int>(0.8f + (py_i - y) * 0.25f);
            for (int bx = px_i - half_w; bx <= px_i + half_w; ++bx) {
                set_pixel(bx, y, 20, 140, 255);
            }
        }
    }

    // Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].alive) continue;
        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));
        if (enemies_[i].state == 2) {
            set_pixel(ex, ey, 255, 255, 255);
        } else if (enemies_[i].state == 1) {
            set_pixel(ex, ey, 255, 50, 50);
        } else {
            set_pixel(ex, ey, 220, 160, 40);
        }
    }

    // Lasers
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (lasers_[i].active) {
            set_pixel(static_cast<int>(std::round(lasers_[i].x)),
                      static_cast<int>(std::round(lasers_[i].y)), 255, 255, 100);
        }
    }

    // Escort wingmen
    int px_i = static_cast<int>(std::round(px_));
    int py_i = static_cast<int>(std::round(py_));
    static const int offsets[4] = {-2, 2, -3, 3};
    for (int e = 0; e < escorts_count_; ++e) {
        set_pixel(px_i + offsets[e], py_i, 60, 200, 255);
    }

    // Player Fighter
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px_i, py_i, 255, 220, 40);
        set_pixel(px_i, py_i - 1, 240, 60, 40);
        set_pixel(px_i - 1, py_i, 200, 40, 40);
        set_pixel(px_i + 1, py_i, 200, 40, 40);
    } else if (state_ == STATE_PLAYER_HIT) {
        set_pixel(px_i, py_i, 255, 80, 20);
    }

    // Lives
    for (int l = 0; l < std::min((int)lives_, 3); ++l) {
        set_pixel(l * 2, 0, 255, 220, 40);
    }
}

} // namespace arcade

