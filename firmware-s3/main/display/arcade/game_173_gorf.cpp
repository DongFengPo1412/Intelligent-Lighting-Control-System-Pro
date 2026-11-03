#include "game_173_gorf.h"
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

Game173Gorf::Game173Gorf() {
    Reset();
}

void Game173Gorf::Init() {
    Reset();
}

void Game173Gorf::Reset() {
    score_ = 0;
    lives_ = 3;
    cycle_ = 1;
    phase_ = PHASE_LASER_ATTACK;
    InitPhase();
}

void Game173Gorf::InitPhase() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 13.0f;
    laser_active_ = false;

    for (int i = 0; i < MAX_BOMBS; ++i) bombs_[i].active = false;

    if (phase_ == PHASE_LASER_ATTACK) {
        for (int i = 0; i < NUM_ESCORTS; ++i) {
            escorts_[i] = {
                2.5f + i * 3.2f,
                2.5f,
                (i % 2 == 0) ? 1.2f : -1.2f,
                true,
                1.0f + i * 0.8f,
                0.0f
            };
        }
    } else if (phase_ == PHASE_SPACE_WARP) {
        for (int i = 0; i < NUM_WARP_SHIPS; ++i) {
            warp_ships_[i] = {
                i * (3.14159f / 3.0f),
                0.5f,
                1.4f + cycle_ * 0.2f,
                true
            };
        }
    } else if (phase_ == PHASE_FLAGSHIP_CORE) {
        shield_bits_ = 0xFF;
        flagship_core_hp_ = 1;
        flagship_x_ = 7.5f;
        flagship_dir_ = 1.0f;
    }
}

void Game173Gorf::KillPlayer() {
    lives_--;
    state_ = STATE_PLAYER_DIED;
    state_timer_ = 1.0f;
    laser_active_ = false;
}

void Game173Gorf::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PHASE_TRANSITION) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (phase_ == PHASE_FLAGSHIP_CORE) {
                cycle_++;
                phase_ = PHASE_LASER_ATTACK;
            } else {
                phase_++;
            }
            InitPhase();
        }
        return;
    }

    if (state_ == STATE_FLAGSHIP_EXPLODING) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            state_ = STATE_PHASE_TRANSITION;
            state_timer_ = 1.0f;
        }
        return;
    }

    if (state_ == STATE_PLAYER_DIED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                py_ = 13.0f;
                laser_active_ = false;
                for (int i = 0; i < MAX_BOMBS; ++i) bombs_[i].active = false;
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

    // 2D Movement
    float speed = 7.0f;
    if (buttons & BTN_LEFT)  px_ -= speed * dt;
    if (buttons & BTN_RIGHT) px_ += speed * dt;
    if (buttons & BTN_UP)    py_ -= speed * dt;
    if (buttons & BTN_DOWN)  py_ += speed * dt;

    px_ = std::max(1.0f, std::min(14.0f, px_));
    py_ = std::max(9.0f, std::min(14.0f, py_));

    // Fire laser
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        laser_active_ = true;
        lx_ = px_;
        ly_ = py_ - 1.0f;
    }

    if (laser_active_) {
        ly_ -= 18.0f * dt;
        if (ly_ < 0.0f) {
            laser_active_ = false;
        } else {
            CheckLaserHit();
        }
    }

    if (phase_ == PHASE_LASER_ATTACK) {
        UpdateLaserAttack(dt);
    } else if (phase_ == PHASE_SPACE_WARP) {
        UpdateSpaceWarp(dt);
    } else if (phase_ == PHASE_FLAGSHIP_CORE) {
        UpdateFlagship(dt);
    }

    // Bombs
    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (!bombs_[i].active) continue;
        bombs_[i].y += 6.0f * dt;
        if (bombs_[i].y > 15.0f) {
            bombs_[i].active = false;
        } else if (std::hypot(bombs_[i].x - px_, bombs_[i].y - py_) < 0.8f) {
            bombs_[i].active = false;
            KillPlayer();
            return;
        }
    }
}

void Game173Gorf::CheckLaserHit() {
    if (!laser_active_) return;

    if (phase_ == PHASE_LASER_ATTACK) {
        for (int i = 0; i < NUM_ESCORTS; ++i) {
            if (escorts_[i].alive && std::hypot(escorts_[i].x - lx_, escorts_[i].y - ly_) < 1.0f) {
                escorts_[i].alive = false;
                laser_active_ = false;
                score_ += 200;
                bool any_alive = false;
                for (int j = 0; j < NUM_ESCORTS; ++j) {
                    if (escorts_[j].alive) { any_alive = true; break; }
                }
                if (!any_alive) {
                    state_ = STATE_PHASE_TRANSITION;
                    state_timer_ = 1.0f;
                    score_ += 500;
                }
                break;
            }
        }
    } else if (phase_ == PHASE_SPACE_WARP) {
        float cx = 7.5f, cy = 6.0f;
        for (int i = 0; i < NUM_WARP_SHIPS; ++i) {
            if (!warp_ships_[i].alive) continue;
            float sx = cx + std::cos(warp_ships_[i].angle) * warp_ships_[i].radius;
            float sy = cy + std::sin(warp_ships_[i].angle) * warp_ships_[i].radius;
            if (std::hypot(sx - lx_, sy - ly_) < 1.0f) {
                warp_ships_[i].alive = false;
                laser_active_ = false;
                score_ += 150;
                bool any_alive = false;
                for (int j = 0; j < NUM_WARP_SHIPS; ++j) {
                    if (warp_ships_[j].alive) { any_alive = true; break; }
                }
                if (!any_alive) {
                    state_ = STATE_PHASE_TRANSITION;
                    state_timer_ = 1.0f;
                    score_ += 600;
                }
                break;
            }
        }
    } else if (phase_ == PHASE_FLAGSHIP_CORE) {
        if (ly_ >= 4.5f && ly_ <= 5.5f && lx_ >= 3.5f && lx_ <= 11.5f) {
            int col = static_cast<int>(std::round(lx_)) - 4;
            if (col >= 0 && col < 8) {
                uint8_t bit_mask = (1 << col);
                if (shield_bits_ & bit_mask) {
                    shield_bits_ &= ~bit_mask;
                    laser_active_ = false;
                    score_ += 100;
                    return;
                }
            }
        }

        if (std::hypot(flagship_x_ - lx_, 3.0f - ly_) < 1.0f) {
            flagship_core_hp_--;
            laser_active_ = false;
            if (flagship_core_hp_ <= 0) {
                state_ = STATE_FLAGSHIP_EXPLODING;
                state_timer_ = 1.5f;
                score_ += 2500;
            }
        }
    }
}

void Game173Gorf::UpdateLaserAttack(float dt) {
    for (int i = 0; i < NUM_ESCORTS; ++i) {
        if (!escorts_[i].alive) continue;
        escorts_[i].x += escorts_[i].vx * dt;
        if (escorts_[i].x > 14.0f) {
            escorts_[i].x = 14.0f;
            escorts_[i].vx = -std::abs(escorts_[i].vx);
        } else if (escorts_[i].x < 1.5f) {
            escorts_[i].x = 1.5f;
            escorts_[i].vx = std::abs(escorts_[i].vx);
        }

        escorts_[i].laser_timer -= dt;
        if (escorts_[i].laser_timer <= 0.0f) {
            escorts_[i].firing_beam = 0.4f;
            escorts_[i].laser_timer = 2.0f;
        }

        if (escorts_[i].firing_beam > 0.0f) {
            escorts_[i].firing_beam -= dt;
            if (std::abs(px_ - escorts_[i].x) < 0.8f && py_ >= escorts_[i].y) {
                KillPlayer();
                return;
            }
        }
    }
}

void Game173Gorf::UpdateSpaceWarp(float dt) {
    float cx = 7.5f, cy = 6.0f;
    for (int i = 0; i < NUM_WARP_SHIPS; ++i) {
        if (!warp_ships_[i].alive) continue;
        warp_ships_[i].angle += 3.0f * dt;
        warp_ships_[i].radius += warp_ships_[i].speed * dt;
        float sx = cx + std::cos(warp_ships_[i].angle) * warp_ships_[i].radius;
        float sy = cy + std::sin(warp_ships_[i].angle) * warp_ships_[i].radius;

        if (std::hypot(sx - px_, sy - py_) < 0.9f) {
            KillPlayer();
            return;
        }

        if (warp_ships_[i].radius > 9.0f) {
            warp_ships_[i].radius = 0.5f;
            warp_ships_[i].angle += 1.0f;
        }
    }
}

void Game173Gorf::UpdateFlagship(float dt) {
    flagship_x_ += flagship_dir_ * 1.5f * dt;
    if (flagship_x_ > 9.0f) {
        flagship_x_ = 9.0f;
        flagship_dir_ = -1.0f;
    } else if (flagship_x_ < 6.0f) {
        flagship_x_ = 6.0f;
        flagship_dir_ = 1.0f;
    }

    bool has_free_bomb = false;
    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (!bombs_[i].active) {
            bombs_[i] = {flagship_x_, 4.5f, true};
            has_free_bomb = true;
            break;
        }
    }
    (void)has_free_bomb;
}

void Game173Gorf::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    if (phase_ == PHASE_LASER_ATTACK) {
        for (int i = 0; i < NUM_ESCORTS; ++i) {
            if (escorts_[i].alive) {
                int ex = static_cast<int>(std::round(escorts_[i].x));
                int ey = static_cast<int>(std::round(escorts_[i].y));
                set_pixel(ex, ey, 255, 60, 60);
                set_pixel(ex - 1, ey - 1, 200, 40, 40);
                set_pixel(ex + 1, ey - 1, 200, 40, 40);
                if (escorts_[i].firing_beam > 0.0f) {
                    for (int by = ey + 1; by < 16; ++by) {
                        set_pixel(ex, by, 80, 240, 255);
                    }
                }
            }
        }
    } else if (phase_ == PHASE_SPACE_WARP) {
        float cx = 7.5f, cy = 6.0f;
        set_pixel(7, 6, 120, 40, 200);
        set_pixel(8, 6, 120, 40, 200);
        for (int i = 0; i < NUM_WARP_SHIPS; ++i) {
            if (warp_ships_[i].alive) {
                int sx = static_cast<int>(std::round(cx + std::cos(warp_ships_[i].angle) * warp_ships_[i].radius));
                int sy = static_cast<int>(std::round(cy + std::sin(warp_ships_[i].angle) * warp_ships_[i].radius));
                set_pixel(sx, sy, 255, 200, 40);
            }
        }
    } else if (phase_ == PHASE_FLAGSHIP_CORE) {
        int fx = static_cast<int>(std::round(flagship_x_));
        if (state_ == STATE_FLAGSHIP_EXPLODING) {
            for (int y = 1; y <= 5; ++y) {
                for (int x = 3; x <= 12; ++x) {
                    if ((x + y) % 2 == 0) set_pixel(x, y, 255, 120, 20);
                    else set_pixel(x, y, 255, 240, 40);
                }
            }
        } else {
            for (int x = fx - 4; x <= fx + 4; ++x) {
                set_pixel(x, 1, 140, 30, 160);
                set_pixel(x, 2, 180, 40, 200);
            }
            set_pixel(fx, 3, 255, 255, 255);
            set_pixel(fx - 1, 3, 255, 100, 0);
            set_pixel(fx + 1, 3, 255, 100, 0);

            for (int col = 0; col < 8; ++col) {
                if (shield_bits_ & (1 << col)) {
                    set_pixel(4 + col, 5, 0, 180, 255);
                }
            }
        }
    }

    // Bombs
    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (bombs_[i].active) {
            set_pixel(static_cast<int>(std::round(bombs_[i].x)),
                      static_cast<int>(std::round(bombs_[i].y)),
                      255, 120, 0);
        }
    }

    // Laser
    if (laser_active_) {
        int lx = static_cast<int>(std::round(lx_));
        int ly = static_cast<int>(std::round(ly_));
        set_pixel(lx, ly, 255, 255, 80);
        set_pixel(lx, ly + 1, 255, 200, 0);
    }

    // Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_PHASE_TRANSITION || state_ == STATE_FLAGSHIP_EXPLODING) {
        set_pixel(px, py - 1, 80, 240, 255);
        set_pixel(px, py, 40, 120, 240);
        set_pixel(px - 1, py + 1, 200, 40, 40);
        set_pixel(px + 1, py + 1, 200, 40, 40);
    } else if (state_ == STATE_PLAYER_DIED) {
        set_pixel(px, py, 255, 100, 0);
        set_pixel(px - 1, py, 255, 0, 0);
        set_pixel(px + 1, py, 255, 0, 0);
    }
}

} // namespace arcade

