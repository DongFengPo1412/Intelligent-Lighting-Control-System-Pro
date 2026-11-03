#include "game_157_tapper.h"
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

static const float BARS_Y[4] = {3.5f, 6.5f, 9.5f, 12.5f};

Game157Tapper::Game157Tapper() {
    Reset();
}

void Game157Tapper::Init() {
    Reset();
}

void Game157Tapper::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game157Tapper::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    bar_idx_ = 1;
    bx_ = BAR_RIGHT;

    for (int i = 0; i < MAX_MUGS; ++i) mugs_[i].active = false;
    for (int i = 0; i < MAX_PATRONS; ++i) patrons_[i].active = false;
    for (int i = 0; i < MAX_TIPS; ++i) tips_[i].active = false;

    total_patrons_spawned_ = 2;
    total_patrons_required_ = 6 + level_ * 2;
    spawn_timer_ = 0.0f;

    patrons_[0] = {0, BAR_LEFT + 0.5f, 1.2f, false, true};
    patrons_[1] = {2, BAR_LEFT + 1.0f, 1.0f, false, true};
}

void Game157Tapper::LoseLife() {
    lives_--;
    state_ = STATE_MUG_SHATTERED;
    state_timer_ = 0.0f;
}

void Game157Tapper::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // 1. Bartender lane
        if ((buttons & BTN_UP) && !(prev_buttons & BTN_UP)) {
            if (bar_idx_ > 0) { bar_idx_--; bx_ = BAR_RIGHT; }
        } else if ((buttons & BTN_DOWN) && !(prev_buttons & BTN_DOWN)) {
            if (bar_idx_ < 3) { bar_idx_++; bx_ = BAR_RIGHT; }
        }

        float speed = 5.0f;
        if (buttons & BTN_LEFT)  bx_ = std::max(7.0f, bx_ - speed * dt);
        else if (buttons & BTN_RIGHT) bx_ = std::min(BAR_RIGHT, bx_ + speed * dt);

        // 2. Pour and slide with Key A
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            if (bx_ >= BAR_RIGHT - 1.0f) {
                for (int i = 0; i < MAX_MUGS; ++i) {
                    if (!mugs_[i].active) {
                        mugs_[i] = {bar_idx_, bx_ - 0.5f, -7.0f, false, true};
                        break;
                    }
                }
            }
        }

        // 3. Spawn patrons
        if (total_patrons_spawned_ < total_patrons_required_) {
            spawn_timer_ += dt;
            if (spawn_timer_ >= 2.5f) {
                spawn_timer_ = 0.0f;
                uint8_t bar = (total_patrons_spawned_ * 3) % 4;
                for (int i = 0; i < MAX_PATRONS; ++i) {
                    if (!patrons_[i].active) {
                        patrons_[i] = {bar, BAR_LEFT, 1.2f + (level_ * 0.2f), false, true};
                        total_patrons_spawned_++;
                        break;
                    }
                }
            }
        }

        // 4. Update mugs
        for (int i = 0; i < MAX_MUGS; ++i) {
            if (!mugs_[i].active) continue;
            mugs_[i].x += mugs_[i].vx * dt;

            // Full mug off left end
            if (!mugs_[i].empty && mugs_[i].x < BAR_LEFT - 0.5f) {
                mugs_[i].active = false;
                LoseLife();
                return;
            }

            // Empty mug caught by player
            if (mugs_[i].empty && mugs_[i].bar == bar_idx_) {
                if (std::abs(mugs_[i].x - bx_) < 1.0f) {
                    mugs_[i].active = false;
                    score_ += 100;
                    continue;
                }
            }

            // Empty mug off right end
            if (mugs_[i].empty && mugs_[i].x > BAR_RIGHT + 0.5f) {
                mugs_[i].active = false;
                LoseLife();
                return;
            }
        }

        // 5. Mug vs Patron
        for (int m = 0; m < MAX_MUGS; ++m) {
            if (!mugs_[m].active || mugs_[m].empty) continue;

            for (int p = 0; p < MAX_PATRONS; ++p) {
                if (patrons_[p].active && patrons_[p].bar == mugs_[m].bar && !patrons_[p].drinking) {
                    if (std::abs(mugs_[m].x - patrons_[p].x) < 1.0f) {
                        mugs_[m].active = false;
                        patrons_[p].drinking = true;
                        patrons_[p].x -= 2.5f;
                        score_ += 150;

                        // Spawn empty returning mug
                        for (int j = 0; j < MAX_MUGS; ++j) {
                            if (!mugs_[j].active) {
                                mugs_[j] = {patrons_[p].bar, patrons_[p].x + 0.5f, 5.5f, true, true};
                                break;
                            }
                        }

                        // Spawn tip
                        for (int t = 0; t < MAX_TIPS; ++t) {
                            if (!tips_[t].active) {
                                tips_[t] = {patrons_[p].bar, patrons_[p].x, true};
                                break;
                            }
                        }

                        if (patrons_[p].x <= BAR_LEFT) {
                            patrons_[p].active = false;
                        } else {
                            patrons_[p].drinking = false;
                        }
                        break;
                    }
                }
            }
        }

        // 6. Update patrons
        for (int p = 0; p < MAX_PATRONS; ++p) {
            if (!patrons_[p].active) continue;
            if (!patrons_[p].drinking) patrons_[p].x += patrons_[p].speed * dt;

            if (patrons_[p].x >= BAR_RIGHT - 0.2f) {
                LoseLife();
                return;
            }
        }

        // 7. Collect tips
        for (int t = 0; t < MAX_TIPS; ++t) {
            if (tips_[t].active && tips_[t].bar == bar_idx_ && std::abs(bx_ - tips_[t].x) < 1.0f) {
                tips_[t].active = false;
                score_ += 250;
            }
        }

        // 8. Stage Clear
        int active_p = 0;
        for (int p = 0; p < MAX_PATRONS; ++p) {
            if (patrons_[p].active) active_p++;
        }
        int active_m = 0;
        for (int m = 0; m < MAX_MUGS; ++m) {
            if (mugs_[m].active) active_m++;
        }

        if (total_patrons_spawned_ >= total_patrons_required_ && active_p == 0 && active_m == 0) {
            score_ += 2500;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
        }

    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_MUG_SHATTERED) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else {
                if (lives_ > 0) {
                    for (int m = 0; m < MAX_MUGS; ++m) mugs_[m].active = false;
                    bx_ = BAR_RIGHT;
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

void Game157Tapper::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Bars
    for (int b = 0; b < 4; ++b) {
        int iy = static_cast<int>(BARS_Y[b]);
        for (int x = 2; x <= 14; ++x) {
            set_pixel(x, iy, 140, 80, 40);
            if (iy + 1 < 16) set_pixel(x, iy + 1, 90, 50, 25);
        }
        if (iy - 1 >= 0) set_pixel(14, iy - 1, 220, 200, 50); // Tap
        set_pixel(1, iy, 70, 70, 70); // Door
    }

    // 2. Tips
    for (int t = 0; t < MAX_TIPS; ++t) {
        if (tips_[t].active) {
            int tx = static_cast<int>(std::round(tips_[t].x));
            int ty = static_cast<int>(BARS_Y[tips_[t].bar]);
            if (ty - 1 >= 0) set_pixel(tx, ty - 1, 255, 230, 40);
        }
    }

    // 3. Mugs
    for (int m = 0; m < MAX_MUGS; ++m) {
        if (!mugs_[m].active) continue;
        int mx = static_cast<int>(std::round(mugs_[m].x));
        int my = static_cast<int>(BARS_Y[mugs_[m].bar]);
        if (!mugs_[m].empty) {
            if (my - 1 >= 0) set_pixel(mx, my - 1, 240, 180, 40);
            if (my - 2 >= 0) set_pixel(mx, my - 2, 255, 255, 255);
        } else {
            if (my - 1 >= 0) set_pixel(mx, my - 1, 180, 220, 240);
        }
    }

    // 4. Patrons
    for (int p = 0; p < MAX_PATRONS; ++p) {
        if (!patrons_[p].active) continue;
        int px = static_cast<int>(std::round(patrons_[p].x));
        int py = static_cast<int>(BARS_Y[patrons_[p].bar]);
        if (py - 1 >= 0) set_pixel(px, py - 1, 220, 60, 50);
        if (py - 2 >= 0) set_pixel(px, py - 2, 240, 180, 140);
    }

    // 5. Bartender
    int bx = static_cast<int>(std::round(bx_));
    int by = static_cast<int>(BARS_Y[bar_idx_]);
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        if (by - 1 >= 0) set_pixel(bx, by - 1, 255, 255, 255);
        if (by - 2 >= 0) set_pixel(bx, by - 2, 240, 190, 150);
        if (bx + 1 < 16 && by - 1 >= 0) set_pixel(bx + 1, by - 1, 40, 40, 40);
    } else if (state_ == STATE_MUG_SHATTERED) {
        set_pixel(bx, by, 255, 60, 40);
        if (bx - 1 >= 0) set_pixel(bx - 1, by, 220, 220, 240);
        if (bx + 1 < 16) set_pixel(bx + 1, by, 220, 220, 240);
    }

    // 6. Lives
    for (int l = 0; l < std::min((int)lives_, 3); ++l) {
        set_pixel(l * 2, 0, 240, 180, 40);
    }
}

} // namespace arcade
