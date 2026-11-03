#include "game_144_moonpatrol.h"
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

Game144MoonPatrol::Game144MoonPatrol()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      distance_(0.0f),
      target_distance_(120.0f),
      checkpoint_letter_('A'),
      speed_(6.0f),
      bx_(3.5f),
      by_(GROUND_Y),
      bvy_(0.0f),
      is_jumping_(false) {
    Reset();
}

void Game144MoonPatrol::Init() {
    Reset();
}

void Game144MoonPatrol::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game144MoonPatrol::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    distance_ = 0.0f;
    checkpoint_letter_ = 'A';
    speed_ = 6.0f;

    bx_ = 3.5f;
    by_ = GROUND_Y;
    bvy_ = 0.0f;
    is_jumping_ = false;

    for (int i = 0; i < MAX_LASERS; ++i) forward_lasers_[i].active = false;
    for (int i = 0; i < MAX_MISSILES; ++i) upward_missiles_[i].active = false;
    for (int i = 0; i < MAX_BOMBS; ++i) bombs_[i].active = false;

    hazards_[0] = {18.0f, 0, 2.0f, true};
    hazards_[1] = {30.0f, 1, 1.0f, true};
    hazards_[2] = {45.0f, 0, 2.5f, true};
    hazards_[3] = {60.0f, 1, 1.0f, true};
    hazards_[4] = {75.0f, 2, 1.0f, true};
    hazards_[5] = {95.0f, 0, 2.0f, true};

    ufos_[0] = {12.0f, 2.5f, -1.5f, 1.2f, true, 0.0f};
    ufos_[1] = {15.0f, 4.0f, -2.0f, 2.5f, true, 0.0f};
}

void Game144MoonPatrol::Crash() {
    if (lives_ > 0) lives_--;
    state_ = STATE_BUGGY_CRASH;
    state_timer_ = 0.0f;
}

void Game144MoonPatrol::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        float target_speed = 6.0f;
        if (buttons & BTN_RIGHT) {
            target_speed = 9.0f;
            bx_ = std::min(5.5f, bx_ + 2.0f * dt);
        } else if (buttons & BTN_LEFT) {
            target_speed = 3.5f;
            bx_ = std::max(2.0f, bx_ - 2.0f * dt);
        }

        speed_ += (target_speed - speed_) * 4.0f * dt;
        distance_ += speed_ * dt;
        score_ += static_cast<uint32_t>(speed_ * dt * 2.0f);

        int cp_idx = std::min(25, static_cast<int>(distance_ / (target_distance_ / 5.0f)));
        checkpoint_letter_ = static_cast<char>('A' + cp_idx);

        if (distance_ >= target_distance_) {
            score_ += 1000;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
            return;
        }

        // Hydraulic Jump (BTN_B)
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            if (!is_jumping_) {
                is_jumping_ = true;
                bvy_ = -11.0f;
            }
        }

        if (is_jumping_) {
            bvy_ += 22.0f * dt;
            by_ += bvy_ * dt;
            if (by_ >= GROUND_Y) {
                by_ = GROUND_Y;
                bvy_ = 0.0f;
                is_jumping_ = false;
            }
        }

        // Dual Fire (BTN_A)
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            for (int i = 0; i < MAX_LASERS; ++i) {
                if (!forward_lasers_[i].active) {
                    forward_lasers_[i].x = bx_ + 1.2f;
                    forward_lasers_[i].y = by_ - 0.2f;
                    forward_lasers_[i].active = true;
                    break;
                }
            }
            for (int i = 0; i < MAX_MISSILES; ++i) {
                if (!upward_missiles_[i].active) {
                    upward_missiles_[i].x = bx_;
                    upward_missiles_[i].y = by_ - 1.2f;
                    upward_missiles_[i].active = true;
                    break;
                }
            }
        }

        // Update Forward Lasers
        for (int i = 0; i < MAX_LASERS; ++i) {
            if (forward_lasers_[i].active) {
                forward_lasers_[i].x += 18.0f * dt;
                if (forward_lasers_[i].x > 16.0f) {
                    forward_lasers_[i].active = false;
                    continue;
                }

                for (int h = 0; h < NUM_HAZARDS; ++h) {
                    if (hazards_[h].alive && hazards_[h].type != 0) {
                        float hx = hazards_[h].x - distance_;
                        if (std::abs(forward_lasers_[i].x - hx) < 1.4f &&
                            std::abs(forward_lasers_[i].y - GROUND_Y) < 1.4f) {
                            hazards_[h].alive = false;
                            forward_lasers_[i].active = false;
                            score_ += 100;
                            break;
                        }
                    }
                }
            }
        }

        // Update Upward Missiles
        for (int i = 0; i < MAX_MISSILES; ++i) {
            if (upward_missiles_[i].active) {
                upward_missiles_[i].y -= 16.0f * dt;
                if (upward_missiles_[i].y < 0.0f) {
                    upward_missiles_[i].active = false;
                    continue;
                }

                for (int b = 0; b < MAX_BOMBS; ++b) {
                    if (bombs_[b].active) {
                        if (std::abs(upward_missiles_[i].x - bombs_[b].x) < 1.0f &&
                            std::abs(upward_missiles_[i].y - bombs_[b].y) < 1.0f) {
                            bombs_[b].active = false;
                            upward_missiles_[i].active = false;
                            score_ += 50;
                            break;
                        }
                    }
                }

                if (upward_missiles_[i].active) {
                    for (int u = 0; u < NUM_UFOS; ++u) {
                        if (ufos_[u].alive) {
                            if (std::abs(upward_missiles_[i].x - ufos_[u].x) < 1.2f &&
                                std::abs(upward_missiles_[i].y - ufos_[u].y) < 1.0f) {
                                ufos_[u].alive = false;
                                ufos_[u].respawn_timer = 3.0f;
                                upward_missiles_[i].active = false;
                                score_ += 200;
                                break;
                            }
                        }
                    }
                }
            }
        }

        // Update UFOs & Bombs
        for (int u = 0; u < NUM_UFOS; ++u) {
            if (ufos_[u].alive) {
                ufos_[u].x += ufos_[u].vx * dt;
                if (ufos_[u].x < -1.0f) ufos_[u].x = 16.5f;
                else if (ufos_[u].x > 16.5f) ufos_[u].x = -1.0f;

                ufos_[u].shoot_timer -= dt;
                if (ufos_[u].shoot_timer <= 0.0f) {
                    ufos_[u].shoot_timer = 2.2f;
                    for (int b = 0; b < MAX_BOMBS; ++b) {
                        if (!bombs_[b].active) {
                            bombs_[b].x = ufos_[u].x;
                            bombs_[b].y = ufos_[u].y + 0.5f;
                            bombs_[b].vy = 5.5f;
                            bombs_[b].active = true;
                            break;
                        }
                    }
                }
            } else {
                ufos_[u].respawn_timer -= dt;
                if (ufos_[u].respawn_timer <= 0.0f) {
                    ufos_[u].x = 16.5f;
                    ufos_[u].alive = true;
                }
            }
        }

        for (int b = 0; b < MAX_BOMBS; ++b) {
            if (bombs_[b].active) {
                bombs_[b].y += bombs_[b].vy * dt;
                if (std::abs(bx_ - bombs_[b].x) < 1.0f && std::abs(by_ - bombs_[b].y) < 1.0f) {
                    bombs_[b].active = false;
                    Crash();
                    return;
                }

                if (bombs_[b].y >= GROUND_Y) {
                    bombs_[b].active = false;
                    continue;
                }
            }
        }

        // Ground hazards collision
        for (int h = 0; h < NUM_HAZARDS; ++h) {
            if (hazards_[h].alive) {
                float hx = hazards_[h].x - distance_;
                if (hazards_[h].type == 0) {
                    if (!is_jumping_) {
                        if (std::abs(bx_ - hx) < (hazards_[h].width / 2.0f + 0.2f)) {
                            Crash();
                            return;
                        }
                    }
                } else {
                    if (std::abs(bx_ - hx) < 0.9f && std::abs(by_ - GROUND_Y) < 0.6f) {
                        Crash();
                        return;
                    }
                }
            }
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_BUGGY_CRASH) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_BUGGY_CRASH) {
                if (lives_ > 0) {
                    by_ = GROUND_Y;
                    bvy_ = 0.0f;
                    is_jumping_ = false;
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

void Game144MoonPatrol::Render(uint8_t* fb) {
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

    // Parallax background
    for (int x = 0; x < 16; ++x) {
        int bg_h = static_cast<int>(8.0f + std::sin((x + distance_ * 0.15f) * 0.5f) * 1.5f);
        for (int y = bg_h; y < 10; ++y) set_pixel(x, y, 40, 30, 60);
    }

    // Lunar Ground
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 13, 160, 160, 170);
        set_pixel(x, 14, 110, 110, 120);
        set_pixel(x, 15, 70, 70, 80);
    }

    // Hazards
    for (int h = 0; h < NUM_HAZARDS; ++h) {
        if (hazards_[h].alive) {
            int hx = static_cast<int>(std::round(hazards_[h].x - distance_));
            if (hx >= -2 && hx < 18) {
                if (hazards_[h].type == 0) {
                    int w = static_cast<int>(std::round(hazards_[h].width));
                    for (int cx = hx - w / 2; cx <= hx + w / 2; ++cx) {
                        set_pixel(cx, 13, 0, 0, 0);
                        set_pixel(cx, 14, 20, 20, 25);
                    }
                } else if (hazards_[h].type == 1) {
                    set_pixel(hx, 12, 190, 130, 80);
                    set_pixel(hx, 13, 140, 90, 50);
                } else {
                    set_pixel(hx, 13, 255, 40, 30);
                }
            }
        }
    }

    // UFOs
    for (int u = 0; u < NUM_UFOS; ++u) {
        if (ufos_[u].alive) {
            int ux = static_cast<int>(std::round(ufos_[u].x));
            int uy = static_cast<int>(std::round(ufos_[u].y));
            set_pixel(ux, uy, 60, 220, 255);
            set_pixel(ux - 1, uy, 40, 160, 200);
            set_pixel(ux + 1, uy, 40, 160, 200);
            set_pixel(ux, uy - 1, 255, 255, 255);
        }
    }

    // Bombs
    for (int b = 0; b < MAX_BOMBS; ++b) {
        if (bombs_[b].active) {
            set_pixel(static_cast<int>(std::round(bombs_[b].x)),
                      static_cast<int>(std::round(bombs_[b].y)), 255, 100, 40);
        }
    }

    // Lasers & Missiles
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (forward_lasers_[i].active) {
            set_pixel(static_cast<int>(std::round(forward_lasers_[i].x)),
                      static_cast<int>(std::round(forward_lasers_[i].y)), 255, 255, 80);
        }
    }
    for (int i = 0; i < MAX_MISSILES; ++i) {
        if (upward_missiles_[i].active) {
            set_pixel(static_cast<int>(std::round(upward_missiles_[i].x)),
                      static_cast<int>(std::round(upward_missiles_[i].y)), 255, 60, 60);
        }
    }

    // Buggy
    int bx = static_cast<int>(std::round(bx_));
    int by = static_cast<int>(std::round(by_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(bx - 1, by, 30, 30, 40);
        set_pixel(bx, by, 30, 30, 40);
        set_pixel(bx + 1, by, 30, 30, 40);

        set_pixel(bx - 1, by - 1, 50, 140, 240);
        set_pixel(bx, by - 1, 60, 180, 255);
        set_pixel(bx + 1, by - 1, 240, 240, 240);
        set_pixel(bx + 2, by - 1, 255, 200, 40);
        set_pixel(bx, by - 2, 255, 80, 80);
    } else if (state_ == STATE_BUGGY_CRASH) {
        set_pixel(bx, by, 255, 120, 20);
        set_pixel(bx - 1, by - 1, 255, 40, 20);
        set_pixel(bx + 1, by - 1, 255, 40, 20);
    }

    // Checkpoint
    set_pixel(0, 0, 255, 255, 255);
}

} // namespace arcade
