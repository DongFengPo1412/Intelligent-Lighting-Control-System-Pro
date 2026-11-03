#include "game_152_flicky.h"
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

Game152Flicky::Game152Flicky() {
    Reset();
}

void Game152Flicky::Init() {
    Reset();
}

void Game152Flicky::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game152Flicky::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 8.0f;
    py_ = 13.0f;
    pvx_ = 0.0f;
    pvy_ = 0.0f;
    facing_ = 1;
    is_grounded_ = true;
    rescued_count_ = 0;
    trail_head_ = 0;
    trail_count_ = 0;

    chicks_[0] = {3.0f, 13.0f, 0, -1};
    chicks_[1] = {12.0f, 13.0f, 0, -1};
    chicks_[2] = {4.0f, 9.0f, 0, -1};
    chicks_[3] = {11.0f, 9.0f, 0, -1};
    chicks_[4] = {5.0f, 5.0f, 0, -1};
    chicks_[5] = {10.0f, 5.0f, 0, -1};

    cats_[0] = {13.0f, 13.0f, -2.2f, true};
    cats_[1] = {2.0f, 9.0f, 2.0f, true};

    throwables_[0] = {6.0f, 13.0f, 0.0f, true};
    throwables_[1] = {8.0f, 9.0f, 0.0f, true};

    for (int i = 0; i < MAX_ITEMS; ++i) flying_items_[i].active = false;
}

float Game152Flicky::GetPlatformY(float x, float y) const {
    if (y >= 13.0f) return 13.0f;
    if (y >= 8.5f && y <= 9.5f && x >= 2.0f && x <= 13.0f) return 9.0f;
    if (y >= 4.5f && y <= 5.5f && x >= 4.0f && x <= 11.0f) return 5.0f;
    return -1.0f;
}

void Game152Flicky::LoseLife() {
    lives_--;
    state_ = STATE_FLICKY_DOWN;
    state_timer_ = 0.0f;
}

void Game152Flicky::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // 1. Jump
        if (((buttons & (BTN_A | BTN_UP)) && !(prev_buttons & (BTN_A | BTN_UP))) ||
            ((buttons & BTN_A) && is_grounded_)) {
            pvy_ = -6.2f;
            is_grounded_ = false;
        }

        // 2. Horizontal run
        float speed = 5.0f;
        if (buttons & BTN_LEFT) {
            pvx_ = -speed; facing_ = -1;
        } else if (buttons & BTN_RIGHT) {
            pvx_ = speed; facing_ = 1;
        } else {
            pvx_ = 0.0f;
        }

        pvy_ += 12.0f * dt;
        px_ += pvx_ * dt;
        py_ += pvy_ * dt;

        px_ = std::max(1.0f, std::min(14.5f, px_));

        float plat_y = GetPlatformY(px_, py_);
        if (plat_y > 0.0f && pvy_ >= 0.0f && py_ >= plat_y) {
            py_ = plat_y;
            pvy_ = 0.0f;
            is_grounded_ = true;
        } else {
            is_grounded_ = false;
        }

        // 3. Trail history
        trail_x_[trail_head_] = px_;
        trail_y_[trail_head_] = py_;
        trail_head_ = (trail_head_ + 1) % TRAIL_HISTORY_LEN;
        if (trail_count_ < TRAIL_HISTORY_LEN) trail_count_++;

        // 4. Chicks Pickup & Follow
        int num_following = 0;
        for (int i = 0; i < NUM_CHICKS; ++i) {
            if (chicks_[i].state == 1) num_following++;
        }

        for (int i = 0; i < NUM_CHICKS; ++i) {
            if (chicks_[i].state == 0) {
                if (std::abs(px_ - chicks_[i].x) < 0.9f && std::abs(py_ - chicks_[i].y) < 0.9f) {
                    chicks_[i].state = 1;
                    chicks_[i].order = num_following++;
                    score_ += 50;
                }
            }
        }

        for (int i = 0; i < NUM_CHICKS; ++i) {
            if (chicks_[i].state == 1) {
                int lag = (chicks_[i].order + 1) * 8;
                if (trail_count_ > lag) {
                    int idx = (trail_head_ - lag + TRAIL_HISTORY_LEN) % TRAIL_HISTORY_LEN;
                    chicks_[i].x = trail_x_[idx];
                    chicks_[i].y = trail_y_[idx];
                }
            }
        }

        // 5. Throw item with Key B
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            for (int t = 0; t < MAX_ITEMS; ++t) {
                if (throwables_[t].active && std::abs(px_ - throwables_[t].x) < 1.2f &&
                    std::abs(py_ - throwables_[t].y) < 1.2f) {
                    throwables_[t].active = false;
                    for (int f = 0; f < MAX_ITEMS; ++f) {
                        if (!flying_items_[f].active) {
                            flying_items_[f] = {px_ + facing_ * 0.8f, py_ - 0.2f, facing_ * 10.0f, true};
                            break;
                        }
                    }
                    break;
                }
            }
        }

        // 6. Flying items
        for (int f = 0; f < MAX_ITEMS; ++f) {
            if (!flying_items_[f].active) continue;
            flying_items_[f].x += flying_items_[f].vx * dt;
            if (flying_items_[f].x < 0.0f || flying_items_[f].x > 15.5f) {
                flying_items_[f].active = false;
                continue;
            }

            for (int c = 0; c < NUM_CATS; ++c) {
                if (cats_[c].alive && std::abs(flying_items_[f].x - cats_[c].x) < 1.0f &&
                    std::abs(flying_items_[f].y - cats_[c].y) < 1.0f) {
                    cats_[c].alive = false;
                    flying_items_[f].active = false;
                    score_ += 300;
                    break;
                }
            }
        }

        // 7. Cats & Train cutting
        for (int c = 0; c < NUM_CATS; ++c) {
            if (!cats_[c].alive) continue;
            cats_[c].x += cats_[c].vx * dt;
            if (cats_[c].x <= 1.5f || cats_[c].x >= 14.0f) cats_[c].vx = -cats_[c].vx;

            if (std::abs(px_ - cats_[c].x) < 0.8f && std::abs(py_ - cats_[c].y) < 0.8f) {
                LoseLife();
                return;
            }

            for (int i = 0; i < NUM_CHICKS; ++i) {
                if (chicks_[i].state == 1) {
                    if (std::abs(chicks_[i].x - cats_[c].x) < 0.7f &&
                        std::abs(chicks_[i].y - cats_[c].y) < 0.7f) {
                        int cut_order = chicks_[i].order;
                        for (int j = 0; j < NUM_CHICKS; ++j) {
                            if (chicks_[j].state == 1 && chicks_[j].order >= cut_order) {
                                chicks_[j].state = 0;
                                chicks_[j].order = -1;
                            }
                        }
                        break;
                    }
                }
            }
        }

        // 8. Nest door delivery at (1.5, 13.0)
        if (std::abs(px_ - 1.5f) < 1.2f && std::abs(py_ - 13.0f) < 1.2f) {
            uint32_t mult = 1;
            for (int i = 0; i < NUM_CHICKS; ++i) {
                if (chicks_[i].state == 1) {
                    chicks_[i].state = 2; // rescued
                    rescued_count_++;
                    score_ += 100 * mult;
                    mult *= 2;
                }
            }
        }

        if (rescued_count_ >= NUM_CHICKS) {
            score_ += 2500;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
        }

    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_FLICKY_DOWN) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else {
                if (lives_ > 0) {
                    px_ = 8.0f;
                    py_ = 13.0f;
                    pvx_ = 0.0f;
                    pvy_ = 0.0f;
                    trail_head_ = 0;
                    trail_count_ = 0;
                    for (int i = 0; i < NUM_CHICKS; ++i) {
                        if (chicks_[i].state == 1) {
                            chicks_[i].state = 0;
                            chicks_[i].order = -1;
                        }
                    }
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

void Game152Flicky::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Platforms
    for (int x = 0; x < 16; ++x) set_pixel(x, 14, 180, 100, 120);
    for (int x = 2; x <= 13; ++x) set_pixel(x, 10, 180, 100, 120);
    for (int x = 4; x <= 11; ++x) set_pixel(x, 6, 180, 100, 120);

    // 2. Door
    set_pixel(1, 13, 220, 140, 40);
    set_pixel(1, 12, 160, 90, 20);

    // 3. Throwables
    for (int t = 0; t < MAX_ITEMS; ++t) {
        if (throwables_[t].active) {
            set_pixel(static_cast<int>(std::round(throwables_[t].x)),
                      static_cast<int>(std::round(throwables_[t].y)), 60, 220, 120);
        }
    }

    // 4. Flying items
    for (int f = 0; f < MAX_ITEMS; ++f) {
        if (flying_items_[f].active) {
            set_pixel(static_cast<int>(std::round(flying_items_[f].x)),
                      static_cast<int>(std::round(flying_items_[f].y)), 100, 255, 180);
        }
    }

    // 5. Chicks
    for (int i = 0; i < NUM_CHICKS; ++i) {
        if (chicks_[i].state == 0 || chicks_[i].state == 1) {
            set_pixel(static_cast<int>(std::round(chicks_[i].x)),
                      static_cast<int>(std::round(chicks_[i].y)), 255, 230, 30);
        }
    }

    // 6. Cats
    for (int c = 0; c < NUM_CATS; ++c) {
        if (cats_[c].alive) {
            int cx = static_cast<int>(std::round(cats_[c].x));
            int cy = static_cast<int>(std::round(cats_[c].y));
            set_pixel(cx, cy, 240, 80, 40);
            if (cy - 1 >= 0) set_pixel(cx, cy - 1, 255, 150, 60);
        }
    }

    // 7. Flicky
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 40, 120, 255);
        if (py - 1 >= 0) set_pixel(px, py - 1, 60, 160, 255);
        int bx = px + facing_;
        if (bx >= 0 && bx < 16 && py - 1 >= 0) set_pixel(bx, py - 1, 255, 80, 30);
    } else if (state_ == STATE_FLICKY_DOWN) {
        set_pixel(px, py, 255, 60, 60);
    }

    // 8. Lives & Rescued
    for (int l = 0; l < std::min((int)lives_, 3); ++l) {
        set_pixel(l * 2, 0, 40, 120, 255);
    }
    for (int r = 0; r < std::min((int)rescued_count_, 6); ++r) {
        set_pixel(15 - r, 0, 255, 230, 30);
    }
}

} // namespace arcade
