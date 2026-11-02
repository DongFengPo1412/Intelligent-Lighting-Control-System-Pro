#include "game_097_tapper.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game097Tapper::Game097Tapper() {
    Init();
}

void Game097Tapper::Init() {
    ResetBar(true);
}

void Game097Tapper::Reset() {
    ResetBar(true);
}

void Game097Tapper::ResetBar(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        round_ = 1;
    }
    state_ = STATE_SERVING;
    state_timer_ = 0.0f;
    patrons_satisfied_ = 0;

    current_lane_ = 0;
    bx_ = 13.0f;
    is_filling_mug_ = false;
    fill_timer_ = 0.0f;

    for (int l = 0; l < NUM_LANES; ++l) {
        tips_[l] = false;
        tip_x_[l] = 6.0f;
    }

    for (int i = 0; i < MAX_MUGS; ++i) {
        mugs_[i].active = false;
    }

    for (int i = 0; i < MAX_PATRONS; ++i) {
        patrons_[i].active = true;
        patrons_[i].lane = i % NUM_LANES;
        patrons_[i].x = 1.0f + (float)(i % 2) * 2.0f;
        patrons_[i].speed = 1.0f + (float)(i % 3) * 0.3f;
        patrons_[i].is_drinking = false;
        patrons_[i].drink_timer = 0.0f;
        patrons_[i].respawn_timer = 0.0f;
    }
}

void Game097Tapper::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_MUG_CRASHED || state_ == STATE_PATRON_OVERRUN) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetBar(false);
            }
        }
        return;
    }

    if (state_ == STATE_ROUND_CLEAR) {
        if (state_timer_ > 2.0f) {
            round_++;
            ResetBar(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetBar(true);
        }
        return;
    }

    UpdateBartender(dt, buttons, prev_buttons);
    UpdateMugs(dt);
    UpdatePatrons(dt);
    CheckCollisions();

    if (patrons_satisfied_ >= 6) {
        state_ = STATE_ROUND_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1500;
    }
}

void Game097Tapper::UpdateBartender(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Switch between the 4 bar counters
    if ((buttons & BTN_UP) && !(prev_buttons & BTN_UP)) {
        if (current_lane_ > 0) {
            current_lane_--;
            bx_ = 13.0f;
        }
    } else if ((buttons & BTN_DOWN) && !(prev_buttons & BTN_DOWN)) {
        if (current_lane_ < NUM_LANES - 1) {
            current_lane_++;
            bx_ = 13.0f;
        }
    }

    // Move along counter
    float move_speed = 6.0f;
    if (buttons & BTN_LEFT) {
        bx_ -= move_speed * dt;
    } else if (buttons & BTN_RIGHT) {
        bx_ += move_speed * dt;
    }
    bx_ = std::clamp(bx_, 7.5f, 13.5f);

    // Collect Tip on current bar counter
    if (tips_[current_lane_]) {
        if (std::fabs(bx_ - tip_x_[current_lane_]) < 1.0f) {
            tips_[current_lane_] = false;
            score_ += 100; // Tip bonus!
        }
    }

    // Button A: Pour and Slide Root Beer Mug
    if (buttons & BTN_A) {
        is_filling_mug_ = true;
        fill_timer_ += dt;
    } else {
        if (is_filling_mug_) {
            // Released Button A: Slide full foaming root beer down the counter!
            is_filling_mug_ = false;
            fill_timer_ = 0.0f;

            for (int i = 0; i < MAX_MUGS; ++i) {
                if (!mugs_[i].active) {
                    mugs_[i].active = true;
                    mugs_[i].lane = current_lane_;
                    mugs_[i].x = std::min(12.5f, bx_ - 0.5f);
                    mugs_[i].vx = -9.0f; // Sliders left toward customers
                    mugs_[i].is_empty = false;
                    score_ += 10;
                    break;
                }
            }
        }
    }
}

void Game097Tapper::UpdateMugs(float dt) {
    for (int i = 0; i < MAX_MUGS; ++i) {
        Mug& m = mugs_[i];
        if (!m.active) continue;

        m.x += m.vx * dt;

        // 1. Full beer slide off left end of counter (Smashes on floor!)
        if (!m.is_empty && m.x <= 0.5f) {
            m.active = false;
            state_ = STATE_MUG_CRASHED;
            state_timer_ = 0.0f;
            return;
        }

        // 2. Empty mug sliding right: Catch or Smash!
        if (m.is_empty) {
            // Check if bartender caught the empty mug
            if (m.lane == current_lane_) {
                float dx = std::fabs(m.x - bx_);
                if (dx < 0.8f) {
                    m.active = false;
                    score_ += 100; // Caught empty mug!
                    continue;
                }
            }

            // If empty mug passes right end of bar uncaught -> Smashes on floor!
            if (m.x >= 14.2f) {
                m.active = false;
                state_ = STATE_MUG_CRASHED;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game097Tapper::UpdatePatrons(float dt) {
    for (int i = 0; i < MAX_PATRONS; ++i) {
        Patron& p = patrons_[i];
        if (!p.active) {
            if (p.respawn_timer > 0.0f) {
                p.respawn_timer -= dt;
            } else {
                p.active = true;
                p.lane = (i * 2 + round_) % NUM_LANES;
                p.x = 1.0f;
                p.speed = 1.0f + (float)(rand() % 3) * 0.4f;
                p.is_drinking = false;
                p.drink_timer = 0.0f;
            }
            continue;
        }

        if (p.is_drinking) {
            p.drink_timer -= dt;
            if (p.drink_timer <= 0.0f) {
                p.is_drinking = false;
                // Slide empty mug back to the right!
                for (int m = 0; m < MAX_MUGS; ++m) {
                    if (!mugs_[m].active) {
                        mugs_[m].active = true;
                        mugs_[m].lane = p.lane;
                        mugs_[m].x = p.x + 0.8f;
                        mugs_[m].vx = 7.5f; // Slides right back to bartender
                        mugs_[m].is_empty = true;
                        break;
                    }
                }

                // Leave a tip on the bar counter!
                tips_[p.lane] = true;
                tip_x_[p.lane] = p.x;

                // Satisfied patron leaves bar!
                p.active = false;
                p.respawn_timer = 2.5f;
                patrons_satisfied_++;
            }
            continue;
        }

        // Advance towards bartender
        p.x += p.speed * dt;

        // Patron reaches tap and overruns bartender!
        if (p.x >= 13.0f) {
            state_ = STATE_PATRON_OVERRUN;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game097Tapper::CheckCollisions() {
    for (int m_idx = 0; m_idx < MAX_MUGS; ++m_idx) {
        Mug& m = mugs_[m_idx];
        if (!m.active || m.is_empty) continue;

        for (int p_idx = 0; p_idx < MAX_PATRONS; ++p_idx) {
            Patron& p = patrons_[p_idx];
            if (!p.active || p.is_drinking) continue;

            if (m.lane == p.lane) {
                float dx = std::fabs(m.x - p.x);
                if (dx < 1.1f) {
                    // Patron catches full mug and drinks!
                    m.active = false;
                    p.is_drinking = true;
                    p.drink_timer = 1.0f;
                    p.x = std::max(1.0f, p.x - 3.0f); // Pushed back!
                    score_ += 50;
                    break;
                }
            }
        }
    }
}

void Game097Tapper::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 4 Bar Counters (y = 3, 6, 9, 12)
    int lane_ys[4] = {3, 6, 9, 12};

    for (int l = 0; l < NUM_LANES; ++l) {
        int by = lane_ys[l];
        // Counter wood surface
        for (int x = 1; x <= 14; ++x) {
            set_pixel(x, by, 160, 85, 30);
        }
        // Brass tap on the right
        set_pixel(14, by - 1, 230, 200, 40);
        // Brass footrail
        for (int x = 1; x <= 14; ++x) {
            set_pixel(x, by + 1, 80, 50, 20);
        }

        // Money Tip on bar counter
        if (tips_[l]) {
            int tx = (int)std::round(tip_x_[l]);
            set_pixel(tx, by - 1, 50, 220, 50); // Green cash tip
        }
    }

    // Patrons
    for (int i = 0; i < MAX_PATRONS; ++i) {
        const Patron& p = patrons_[i];
        if (!p.active) continue;

        int px = (int)std::round(p.x);
        int py = lane_ys[p.lane];

        if (p.is_drinking) {
            // Chugging root beer
            set_pixel(px, py - 1, 255, 200, 50); // Mug at face
            set_pixel(px - 1, py - 1, 200, 150, 100);
            set_pixel(px, py, 40, 80, 200);
        } else {
            // Demanding cowboy / athlete patron
            set_pixel(px, py - 1, 220, 160, 120); // Face
            set_pixel(px, py - 2, 140, 70, 20);   // Cowboy hat
            set_pixel(px, py, 180, 40, 40);       // Shirt
            set_pixel(px + 1, py, 220, 160, 120); // Hand reaching out
        }
    }

    // Mugs
    for (int i = 0; i < MAX_MUGS; ++i) {
        const Mug& m = mugs_[i];
        if (!m.active) continue;

        int mx = (int)std::round(m.x);
        int my = lane_ys[m.lane] - 1;

        if (m.is_empty) {
            // Empty transparent glass mug outline
            set_pixel(mx, my, 200, 230, 255);
        } else {
            // Full Foaming Root Beer Mug
            set_pixel(mx, my, 180, 100, 20);     // Amber root beer
            set_pixel(mx, my - 1, 255, 255, 255); // White froth foam
        }
    }

    // Bartender
    int b_lane_y = lane_ys[current_lane_];
    int bx = (int)std::round(bx_);

    if (state_ == STATE_MUG_CRASHED || state_ == STATE_PATRON_OVERRUN) {
        // Crashed glass shards / dismayed bartender
        set_pixel(bx, b_lane_y - 1, 255, 50, 50);
        set_pixel(bx + 1, b_lane_y, 255, 255, 255); // Shards
        set_pixel(bx - 1, b_lane_y, 255, 255, 255);
    } else {
        // Bartender in white shirt & red bowtie
        set_pixel(bx, b_lane_y, 30, 30, 30);           // Black trousers
        set_pixel(bx, b_lane_y - 1, 255, 255, 255);     // White shirt
        set_pixel(bx - 1, b_lane_y - 1, 240, 50, 50);   // Red bowtie
        set_pixel(bx, b_lane_y - 2, 240, 190, 140);     // Face & mustache

        if (is_filling_mug_) {
            set_pixel(bx - 1, b_lane_y - 2, 255, 220, 40); // Pulling tap handle
        }
    }

    // Top HUD: Lives on left
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 240, 180, 50); // Mini beer mug icons
    }
}

} // namespace arcade
