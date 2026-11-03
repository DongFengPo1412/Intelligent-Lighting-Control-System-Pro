#include "game_145_tumblepop.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = (1 << 0);
static constexpr uint16_t BTN_DOWN  = (1 << 1);
static constexpr uint16_t BTN_LEFT  = (1 << 2);
static constexpr uint16_t BTN_RIGHT = (1 << 3);
static constexpr uint16_t BTN_A     = (1 << 4);
static constexpr uint16_t BTN_B     = (1 << 5);

static constexpr float PLATFORMS_Y[4] = {14.0f, 10.0f, 6.0f, 2.0f};

Game145Tumblepop::Game145Tumblepop()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      px_(2.0f),
      py_(14.0f),
      pvy_(0.0f),
      facing_(1),
      is_jumping_(false),
      is_vacuuming_(false),
      monsters_in_pack_(0) {
    rolling_ball_.active = false;
    Reset();
}

void Game145Tumblepop::Init() {
    Reset();
}

void Game145Tumblepop::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game145Tumblepop::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 2.0f;
    py_ = 14.0f;
    pvy_ = 0.0f;
    facing_ = 1;
    is_jumping_ = false;
    is_vacuuming_ = false;
    monsters_in_pack_ = 0;
    rolling_ball_.active = false;

    enemies_[0] = {6.0f, 14.0f, 2.0f, 0, false, true};
    enemies_[1] = {12.0f, 10.0f, -2.0f, 1, false, true};
    enemies_[2] = {4.0f, 6.0f, 2.2f, 0, false, true};
    enemies_[3] = {10.0f, 2.0f, -1.8f, 1, false, true};
}

void Game145Tumblepop::LoseLife() {
    if (lives_ > 0) lives_--;
    state_ = STATE_PLAYER_DOWN;
    state_timer_ = 0.0f;
}

void Game145Tumblepop::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        float move_speed = 5.5f;
        if (buttons & BTN_LEFT) {
            px_ = std::max(1.0f, px_ - move_speed * dt);
            facing_ = -1;
        }
        if (buttons & BTN_RIGHT) {
            px_ = std::min(14.0f, px_ + move_speed * dt);
            facing_ = 1;
        }

        // Jump (UP or BTN_B when pack is empty)
        if (!is_jumping_) {
            if ((buttons & BTN_UP) || ((buttons & BTN_B) && !(prev_buttons & BTN_B) && monsters_in_pack_ == 0)) {
                is_jumping_ = true;
                pvy_ = -9.0f;
            }
        }

        if (is_jumping_) {
            pvy_ += 20.0f * dt;
            py_ += pvy_ * dt;
            if (pvy_ >= 0.0f) {
                for (float plat_y : PLATFORMS_Y) {
                    if (std::abs(py_ - plat_y) < 0.5f) {
                        py_ = plat_y;
                        pvy_ = 0.0f;
                        is_jumping_ = false;
                        break;
                    }
                }
            }
            if (py_ >= 14.0f) {
                py_ = 14.0f;
                pvy_ = 0.0f;
                is_jumping_ = false;
            }
        }

        if (!is_jumping_ && (buttons & BTN_DOWN)) {
            if (py_ < 14.0f) {
                py_ += 1.0f;
                is_jumping_ = true;
                pvy_ = 2.0f;
            }
        }

        // Vacuum (BTN_A)
        is_vacuuming_ = bool(buttons & BTN_A);

        // Eject Monster Ball (BTN_B when monsters stored)
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            if (monsters_in_pack_ > 0 && !rolling_ball_.active) {
                uint8_t power = monsters_in_pack_;
                rolling_ball_.x = px_ + facing_ * 1.2f;
                rolling_ball_.y = py_;
                rolling_ball_.vx = facing_ * (10.0f + power * 2.0f);
                rolling_ball_.bounces = 4;
                rolling_ball_.power = power;
                rolling_ball_.active = true;
                monsters_in_pack_ = 0;
            }
        }

        // Enemies & Suction
        float cone_dist = 4.5f;
        bool all_dead = true;
        for (int i = 0; i < NUM_ENEMIES; ++i) {
            if (!enemies_[i].alive) continue;
            all_dead = false;

            if (is_vacuuming_ && std::abs(enemies_[i].y - py_) < 1.0f) {
                bool in_cone = false;
                if (facing_ > 0 && enemies_[i].x - px_ >= 0.0f && enemies_[i].x - px_ <= cone_dist) in_cone = true;
                else if (facing_ < 0 && px_ - enemies_[i].x >= 0.0f && px_ - enemies_[i].x <= cone_dist) in_cone = true;

                if (in_cone) {
                    enemies_[i].being_sucked = true;
                    float pull_speed = 7.0f;
                    if (enemies_[i].x > px_) enemies_[i].x -= pull_speed * dt;
                    else enemies_[i].x += pull_speed * dt;

                    if (std::abs(enemies_[i].x - px_) < 1.1f) {
                        if (monsters_in_pack_ < MAX_PACK) {
                            enemies_[i].alive = false;
                            monsters_in_pack_++;
                            score_ += 100;
                            continue;
                        }
                    }
                } else {
                    enemies_[i].being_sucked = false;
                }
            } else {
                enemies_[i].being_sucked = false;
            }

            if (!enemies_[i].being_sucked) {
                enemies_[i].x += enemies_[i].vx * dt;
                if (enemies_[i].x <= 1.5f || enemies_[i].x >= 14.0f) {
                    enemies_[i].vx = -enemies_[i].vx;
                }
            }

            if (std::abs(px_ - enemies_[i].x) < 0.9f && std::abs(py_ - enemies_[i].y) < 0.8f) {
                if (!enemies_[i].being_sucked) {
                    LoseLife();
                    return;
                }
            }
        }

        // Rolling Monster Ball
        if (rolling_ball_.active) {
            rolling_ball_.x += rolling_ball_.vx * dt;
            if (rolling_ball_.x <= 1.0f) {
                rolling_ball_.x = 1.0f;
                rolling_ball_.vx = -rolling_ball_.vx;
                rolling_ball_.bounces--;
            } else if (rolling_ball_.x >= 14.5f) {
                rolling_ball_.x = 14.5f;
                rolling_ball_.vx = -rolling_ball_.vx;
                rolling_ball_.bounces--;
            }

            if (rolling_ball_.bounces <= 0) {
                rolling_ball_.active = false;
            }

            if (rolling_ball_.active) {
                for (int i = 0; i < NUM_ENEMIES; ++i) {
                    if (enemies_[i].alive) {
                        if (std::abs(rolling_ball_.x - enemies_[i].x) < 1.2f &&
                            std::abs(rolling_ball_.y - enemies_[i].y) < 1.0f) {
                            enemies_[i].alive = false;
                            score_ += 250;
                        }
                    }
                }
            }
        }

        if (all_dead && monsters_in_pack_ == 0 && !rolling_ball_.active) {
            score_ += 1000;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_PLAYER_DOWN) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_PLAYER_DOWN) {
                if (lives_ > 0) {
                    px_ = 2.0f;
                    py_ = 14.0f;
                    pvy_ = 0.0f;
                    monsters_in_pack_ = 0;
                    rolling_ball_.active = false;
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

void Game145Tumblepop::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Platforms
    for (float plat_y : PLATFORMS_Y) {
        int py_i = static_cast<int>(std::round(plat_y));
        for (int x = 1; x <= 14; ++x) {
            set_pixel(x, py_i + 1, 120, 80, 50);
            set_pixel(x, py_i, 160, 110, 70);
        }
    }

    // Suction cone
    if (is_vacuuming_) {
        int py_i = static_cast<int>(std::round(py_));
        int px_i = static_cast<int>(std::round(px_));
        for (int d = 1; d <= 4; ++d) {
            set_pixel(px_i + facing_ * d, py_i, 80, 240, 255);
            set_pixel(px_i + facing_ * d, py_i - 1, 40, 180, 220);
        }
    }

    // Rolling monster ball
    if (rolling_ball_.active) {
        int rx = static_cast<int>(std::round(rolling_ball_.x));
        int ry = static_cast<int>(std::round(rolling_ball_.y));
        set_pixel(rx, ry, 255, 60, 200);
        set_pixel(rx - 1, ry, 220, 40, 160);
        set_pixel(rx + 1, ry, 220, 40, 160);
        set_pixel(rx, ry - 1, 255, 200, 255);
    }

    // Enemies
    for (int i = 0; i < NUM_ENEMIES; ++i) {
        if (enemies_[i].alive) {
            int ex = static_cast<int>(std::round(enemies_[i].x));
            int ey = static_cast<int>(std::round(enemies_[i].y));
            if (enemies_[i].being_sucked) {
                set_pixel(ex, ey, 255, 255, 255);
                set_pixel(ex, ey - 1, 100, 200, 255);
            } else {
                if (enemies_[i].type == 0) {
                    set_pixel(ex, ey, 240, 60, 60);
                    set_pixel(ex, ey - 1, 255, 140, 80);
                } else {
                    set_pixel(ex, ey, 180, 60, 220);
                    set_pixel(ex, ey - 1, 220, 100, 255);
                }
            }
        }
    }

    // Player
    int px_i = static_cast<int>(std::round(px_));
    int py_i = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px_i, py_i, 50, 120, 240);
        set_pixel(px_i, py_i - 1, 255, 220, 160);
        set_pixel(px_i - facing_, py_i - 1, 240, 160, 40);
        set_pixel(px_i + facing_, py_i, 200, 200, 220);
    } else if (state_ == STATE_PLAYER_DOWN) {
        set_pixel(px_i, py_i, 255, 60, 40);
    }

    // Pack count
    for (int b = 0; b < monsters_in_pack_; ++b) {
        set_pixel(b * 2, 15, 255, 220, 40);
    }
}

} // namespace arcade

