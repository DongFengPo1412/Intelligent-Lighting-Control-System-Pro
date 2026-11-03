#include "game_142_mariner.h"
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

Game142Mariner::Game142Mariner()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      oxygen_(100.0f),
      px_(3.0f),
      py_(7.0f) {
    Reset();
}

void Game142Mariner::Init() {
    Reset();
}

void Game142Mariner::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game142Mariner::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    oxygen_ = 100.0f;
    px_ = 3.0f;
    py_ = 7.0f;

    for (int i = 0; i < MAX_TORPEDOES; ++i) torpedoes_[i].active = false;
    for (int i = 0; i < MAX_MISSILES; ++i) vertical_missiles_[i].active = false;
    for (int i = 0; i < MAX_DEPTH_CHARGES; ++i) depth_charges_[i].active = false;

    for (int x = 0; x < 16; ++x) {
        seabed_[x] = 13.0f + std::sin(x * 0.4f) * 1.5f;
    }

    enemies_[0] = {14.0f, 1.0f, -2.0f, 0, 1.5f, true};
    enemies_[1] = {13.0f, 6.0f, -2.5f, 1, 2.2f, true};
    enemies_[2] = {15.0f, 10.0f, -1.8f, 1, 3.0f, true};

    bubbles_[0] = {6.0f, 12.0f, -2.0f, true};
    bubbles_[1] = {12.0f, 13.0f, -2.0f, true};

    treasure_ = {9.0f, 13.0f, false};
}

void Game142Mariner::Crash() {
    if (lives_ > 0) lives_--;
    state_ = STATE_SUB_CRASH;
    state_timer_ = 0.0f;
}

void Game142Mariner::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        oxygen_ -= 3.0f * dt;
        if (oxygen_ <= 0.0f) {
            oxygen_ = 0.0f;
            Crash();
            return;
        }

        float move_speed = 6.0f;
        if (buttons & BTN_LEFT)  px_ = std::max(1.0f, px_ - move_speed * dt);
        if (buttons & BTN_RIGHT) px_ = std::min(14.0f, px_ + move_speed * dt);
        if (buttons & BTN_UP)    py_ = std::max(2.0f, py_ - move_speed * 0.8f * dt);
        if (buttons & BTN_DOWN)  py_ = std::min(14.5f, py_ + move_speed * 0.8f * dt);

        int col_idx = std::max(0, std::min(15, static_cast<int>(std::round(px_))));
        if (py_ >= seabed_[col_idx] - 0.4f) {
            Crash();
            return;
        }

        // Fire Torpedo (Horizontal: BTN_A)
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            for (int i = 0; i < MAX_TORPEDOES; ++i) {
                if (!torpedoes_[i].active) {
                    torpedoes_[i].x = px_ + 1.0f;
                    torpedoes_[i].y = py_;
                    torpedoes_[i].active = true;
                    break;
                }
            }
        }

        // Fire Vertical Missile (Upward: BTN_B)
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            for (int i = 0; i < MAX_MISSILES; ++i) {
                if (!vertical_missiles_[i].active) {
                    vertical_missiles_[i].x = px_;
                    vertical_missiles_[i].y = py_ - 1.0f;
                    vertical_missiles_[i].active = true;
                    break;
                }
            }
        }

        // Torpedoes
        for (int i = 0; i < MAX_TORPEDOES; ++i) {
            if (torpedoes_[i].active) {
                torpedoes_[i].x += 14.0f * dt;
                if (torpedoes_[i].x > 15.5f) {
                    torpedoes_[i].active = false;
                    continue;
                }

                for (int k = 0; k < NUM_ENEMIES; ++k) {
                    if (enemies_[k].alive && enemies_[k].type == 1) {
                        if (std::abs(torpedoes_[i].x - enemies_[k].x) < 1.1f &&
                            std::abs(torpedoes_[i].y - enemies_[k].y) < 0.9f) {
                            enemies_[k].alive = false;
                            torpedoes_[i].active = false;
                            score_ += 150;
                            break;
                        }
                    }
                }
            }
        }

        // Vertical Missiles
        for (int i = 0; i < MAX_MISSILES; ++i) {
            if (vertical_missiles_[i].active) {
                vertical_missiles_[i].y -= 12.0f * dt;
                if (vertical_missiles_[i].y < 0.5f) {
                    vertical_missiles_[i].active = false;
                    continue;
                }

                for (int d = 0; d < MAX_DEPTH_CHARGES; ++d) {
                    if (depth_charges_[d].active) {
                        if (std::abs(vertical_missiles_[i].x - depth_charges_[d].x) < 1.0f &&
                            std::abs(vertical_missiles_[i].y - depth_charges_[d].y) < 1.0f) {
                            depth_charges_[d].active = false;
                            vertical_missiles_[i].active = false;
                            score_ += 80;
                            break;
                        }
                    }
                }

                if (vertical_missiles_[i].active) {
                    for (int k = 0; k < NUM_ENEMIES; ++k) {
                        if (enemies_[k].alive && enemies_[k].type == 0) {
                            if (std::abs(vertical_missiles_[i].x - enemies_[k].x) < 1.4f &&
                                std::abs(vertical_missiles_[i].y - enemies_[k].y) < 1.0f) {
                                enemies_[k].alive = false;
                                vertical_missiles_[i].active = false;
                                score_ += 300;
                                break;
                            }
                        }
                    }
                }
            }
        }

        // Enemies & Depth charges
        bool all_dead = true;
        for (int k = 0; k < NUM_ENEMIES; ++k) {
            if (enemies_[k].alive) {
                all_dead = false;
                enemies_[k].x += enemies_[k].vx * dt;
                if (enemies_[k].x < -1.0f) enemies_[k].x = 16.5f;

                enemies_[k].shoot_timer -= dt;
                if (enemies_[k].shoot_timer <= 0.0f) {
                    enemies_[k].shoot_timer = 2.5f;
                    if (enemies_[k].type == 0) {
                        for (int d = 0; d < MAX_DEPTH_CHARGES; ++d) {
                            if (!depth_charges_[d].active) {
                                depth_charges_[d].x = enemies_[k].x;
                                depth_charges_[d].y = 2.0f;
                                depth_charges_[d].vy = 3.5f;
                                depth_charges_[d].active = true;
                                break;
                            }
                        }
                    }
                }

                if (std::abs(px_ - enemies_[k].x) < 1.0f && std::abs(py_ - enemies_[k].y) < 0.9f) {
                    Crash();
                    return;
                }
            }
        }

        // Depth charges update
        for (int d = 0; d < MAX_DEPTH_CHARGES; ++d) {
            if (depth_charges_[d].active) {
                depth_charges_[d].y += depth_charges_[d].vy * dt;
                if (depth_charges_[d].y > 15.0f) {
                    depth_charges_[d].active = false;
                    continue;
                }

                if (std::abs(px_ - depth_charges_[d].x) < 0.9f && std::abs(py_ - depth_charges_[d].y) < 0.9f) {
                    depth_charges_[d].active = false;
                    Crash();
                    return;
                }
            }
        }

        // Bubbles
        for (int b = 0; b < NUM_BUBBLES; ++b) {
            if (bubbles_[b].alive) {
                bubbles_[b].y += bubbles_[b].vy * dt;
                if (bubbles_[b].y < 2.0f) {
                    bubbles_[b].y = 13.5f;
                    bubbles_[b].x = std::fmod(bubbles_[b].x + 4.0f, 14.0f) + 1.0f;
                }

                if (std::abs(px_ - bubbles_[b].x) < 1.0f && std::abs(py_ - bubbles_[b].y) < 1.0f) {
                    bubbles_[b].alive = false;
                    oxygen_ = std::min(100.0f, oxygen_ + 35.0f);
                    score_ += 50;
                }
            }
        }

        // Treasure
        if (!treasure_.collected) {
            if (std::abs(px_ - treasure_.x) < 1.1f && std::abs(py_ - treasure_.y) < 1.0f) {
                treasure_.collected = true;
                score_ += 500;
            }
        }

        if (all_dead) {
            score_ += 1000;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_SUB_CRASH) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_SUB_CRASH) {
                if (lives_ > 0) {
                    px_ = 3.0f;
                    py_ = 7.0f;
                    oxygen_ = 100.0f;
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

void Game142Mariner::Render(uint8_t* fb) {
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

    // Surface waves
    for (int x = 0; x < 16; ++x) set_pixel(x, 1, 50, 180, 240);

    // Seabed
    for (int x = 0; x < 16; ++x) {
        int floor_y = static_cast<int>(std::round(seabed_[x]));
        for (int y = floor_y; y < 16; ++y) set_pixel(x, y, 60, 40, 25);
        set_pixel(x, floor_y, 110, 80, 40);
    }

    // Treasure
    if (!treasure_.collected) {
        int tx = static_cast<int>(std::round(treasure_.x));
        int ty = static_cast<int>(std::round(treasure_.y));
        set_pixel(tx, ty, 255, 215, 30);
        set_pixel(tx, ty - 1, 255, 255, 100);
    }

    // Bubbles
    for (int b = 0; b < NUM_BUBBLES; ++b) {
        if (bubbles_[b].alive) {
            set_pixel(static_cast<int>(std::round(bubbles_[b].x)),
                      static_cast<int>(std::round(bubbles_[b].y)), 180, 240, 255);
        }
    }

    // Enemies
    for (int i = 0; i < NUM_ENEMIES; ++i) {
        if (enemies_[i].alive) {
            int ex = static_cast<int>(std::round(enemies_[i].x));
            int ey = static_cast<int>(std::round(enemies_[i].y));
            if (enemies_[i].type == 0) {
                set_pixel(ex, ey, 180, 180, 190);
                set_pixel(ex - 1, ey, 140, 140, 150);
                set_pixel(ex + 1, ey, 140, 140, 150);
                set_pixel(ex, ey - 1, 80, 80, 90);
            } else {
                set_pixel(ex, ey, 240, 40, 40);
                set_pixel(ex + 1, ey, 180, 30, 30);
                set_pixel(ex, ey - 1, 255, 100, 80);
            }
        }
    }

    // Depth charges
    for (int d = 0; d < MAX_DEPTH_CHARGES; ++d) {
        if (depth_charges_[d].active) {
            set_pixel(static_cast<int>(std::round(depth_charges_[d].x)),
                      static_cast<int>(std::round(depth_charges_[d].y)), 255, 120, 20);
        }
    }

    // Torpedoes & Missiles
    for (int i = 0; i < MAX_TORPEDOES; ++i) {
        if (torpedoes_[i].active) {
            set_pixel(static_cast<int>(std::round(torpedoes_[i].x)),
                      static_cast<int>(std::round(torpedoes_[i].y)), 255, 255, 255);
        }
    }
    for (int i = 0; i < MAX_MISSILES; ++i) {
        if (vertical_missiles_[i].active) {
            set_pixel(static_cast<int>(std::round(vertical_missiles_[i].x)),
                      static_cast<int>(std::round(vertical_missiles_[i].y)), 255, 230, 50);
        }
    }

    // Submarine
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 240, 200, 30);
        set_pixel(px - 1, py, 200, 160, 20);
        set_pixel(px + 1, py, 255, 240, 80);
        set_pixel(px, py - 1, 240, 200, 30);
        set_pixel(px, py + 1, 160, 140, 20);
    } else if (state_ == STATE_SUB_CRASH) {
        set_pixel(px, py, 255, 100, 30);
        set_pixel(px - 1, py, 255, 40, 20);
        set_pixel(px + 1, py, 255, 40, 20);
    }

    // Oxygen
    int o2_pixels = static_cast<int>(std::round((oxygen_ / 100.0f) * 15.0f));
    for (int x = 0; x <= o2_pixels && x < 16; ++x) {
        set_pixel(x, 15, 60, 180, 255);
    }
}

} // namespace arcade
