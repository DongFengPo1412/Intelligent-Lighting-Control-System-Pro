#include "game_150_tagteamwrestling.h"
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

Game150TagTeamWrestling::Game150TagTeamWrestling() {
    Reset();
}

void Game150TagTeamWrestling::Init() {
    Reset();
}

void Game150TagTeamWrestling::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitMatch();
}

void Game150TagTeamWrestling::InitMatch() {
    state_ = STATE_NEUTRAL;
    state_timer_ = 0.0f;

    px_ = 5.0f;
    py_ = 8.0f;
    pvx_ = 0.0f;
    pvy_ = 0.0f;
    p_hp_ = 100.0f;
    p_stamina_ = 100.0f;
    partner_hp_ = 100.0f;
    partner_active_ = false;

    ox_ = 11.0f;
    oy_ = 8.0f;
    ovx_ = 0.0f;
    ovy_ = 0.0f;
    o_hp_ = 100.0f;
    o_stamina_ = 100.0f;

    grapple_meter_ = 0.0f;
    pin_count_ = 0.0f;
    pinning_player_ = true;
}

void Game150TagTeamWrestling::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    // Partner regeneration
    if (!partner_active_) {
        partner_hp_ = std::min(100.0f, partner_hp_ + dt * 4.0f);
    } else {
        p_hp_ = std::min(100.0f, p_hp_ + dt * 4.0f);
    }

    if (state_ == STATE_NEUTRAL) {
        float speed = 5.0f;
        float dx = 0.0f;
        float dy = 0.0f;
        if (buttons & BTN_LEFT)  dx -= speed;
        if (buttons & BTN_RIGHT) dx += speed;
        if (buttons & BTN_UP)    dy -= speed;
        if (buttons & BTN_DOWN)  dy += speed;

        // Tag corner (2.5, 2.5) with Key B
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            if (px_ <= 3.5f && py_ <= 3.5f) {
                partner_active_ = !partner_active_;
                std::swap(p_hp_, partner_hp_);
                score_ += 300;
                px_ = 4.5f;
                py_ = 4.5f;
                return;
            }
        }

        // Sprint rebound with Key A
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            if (dx != 0.0f || dy != 0.0f) {
                pvx_ = dx * 1.8f;
                pvy_ = dy * 1.8f;
                state_ = STATE_REBOUNDING;
                return;
            }
        }

        px_ += dx * dt;
        py_ += dy * dt;

        // Elastic ropes rebound
        if (px_ <= 2.5f) {
            px_ = 2.5f;
            if (dx < 0) { pvx_ = 9.0f; state_ = STATE_REBOUNDING; }
        } else if (px_ >= 13.5f) {
            px_ = 13.5f;
            if (dx > 0) { pvx_ = -9.0f; state_ = STATE_REBOUNDING; }
        }

        if (py_ <= 2.5f) {
            py_ = 2.5f;
            if (dy < 0) { pvy_ = 9.0f; state_ = STATE_REBOUNDING; }
        } else if (py_ >= 13.5f) {
            py_ = 13.5f;
            if (dy > 0) { pvy_ = -9.0f; state_ = STATE_REBOUNDING; }
        }

        // Opponent tracks player
        float odx = px_ - ox_;
        float ody = py_ - oy_;
        float dist = std::hypot(odx, ody);
        if (dist > 0.8f) {
            float o_speed = 3.2f;
            ox_ += (odx / dist) * o_speed * dt;
            oy_ += (ody / dist) * o_speed * dt;
        }

        // Grapple trigger
        if (std::hypot(px_ - ox_, py_ - oy_) < 0.9f) {
            state_ = STATE_GRAPPLE;
            state_timer_ = 0.0f;
            grapple_meter_ = 0.0f;
        }

    } else if (state_ == STATE_REBOUNDING) {
        px_ += pvx_ * dt;
        py_ += pvy_ * dt;
        pvx_ *= 0.92f;
        pvy_ *= 0.92f;

        if (std::hypot(px_ - ox_, py_ - oy_) < 1.2f) {
            o_hp_ = std::max(0.0f, o_hp_ - 25.0f);
            score_ += 400;
            ox_ = std::max(2.5f, std::min(13.5f, ox_ + pvx_ * 0.3f));
            state_ = STATE_DOWNED;
            state_timer_ = 0.0f;
            pinning_player_ = true;
            return;
        }

        if (std::abs(pvx_) < 1.0f && std::abs(pvy_) < 1.0f) {
            state_ = STATE_NEUTRAL;
        }

    } else if (state_ == STATE_GRAPPLE) {
        if (((buttons & BTN_A) && !(prev_buttons & BTN_A)) ||
            ((buttons & BTN_B) && !(prev_buttons & BTN_B))) {
            grapple_meter_ += 12.0f;
        }

        grapple_meter_ -= dt * 18.0f;

        if (grapple_meter_ >= 35.0f) {
            o_hp_ = std::max(0.0f, o_hp_ - 20.0f);
            score_ += 500;
            state_ = STATE_DOWNED;
            state_timer_ = 0.0f;
            pinning_player_ = true;
        } else if (grapple_meter_ <= -35.0f) {
            p_hp_ = std::max(0.0f, p_hp_ - 20.0f);
            state_ = STATE_DOWNED;
            state_timer_ = 0.0f;
            pinning_player_ = false;
        }

    } else if (state_ == STATE_DOWNED) {
        state_timer_ += dt;
        if (pinning_player_) {
            if (buttons & BTN_LEFT)  px_ -= 4.0f * dt;
            if (buttons & BTN_RIGHT) px_ += 4.0f * dt;
            if (buttons & BTN_UP)    py_ -= 4.0f * dt;
            if (buttons & BTN_DOWN)  py_ += 4.0f * dt;

            if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
                if (std::hypot(px_ - ox_, py_ - oy_) < 1.4f) {
                    state_ = STATE_PINFALL;
                    pin_count_ = 0.0f;
                    return;
                }
            }

            if (state_timer_ >= 2.5f) {
                state_ = STATE_NEUTRAL;
            }
        } else {
            if (state_timer_ >= 2.0f) {
                state_ = STATE_NEUTRAL;
            }
        }

    } else if (state_ == STATE_PINFALL) {
        pin_count_ += dt;

        if (pinning_player_) {
            float kickout_chance = o_hp_ / 120.0f;
            if (pin_count_ > 1.5f && kickout_chance > 0.4f) {
                state_ = STATE_NEUTRAL;
                return;
            }

            if (pin_count_ >= 3.0f) {
                score_ += 2500;
                state_ = STATE_MATCH_WON;
                state_timer_ = 0.0f;
            }
        } else {
            if (((buttons & BTN_A) && !(prev_buttons & BTN_A)) ||
                ((buttons & BTN_B) && !(prev_buttons & BTN_B))) {
                if (p_hp_ > 15.0f) {
                    state_ = STATE_NEUTRAL;
                    return;
                }
            }

            if (pin_count_ >= 3.0f) {
                lives_--;
                state_ = STATE_MATCH_LOST;
                state_timer_ = 0.0f;
            }
        }

    } else if (state_ == STATE_MATCH_WON || state_ == STATE_MATCH_LOST) {
        state_timer_ += dt;
        if (state_timer_ >= 2.0f) {
            if (state_ == STATE_MATCH_WON) {
                level_++;
                InitMatch();
            } else {
                if (lives_ > 0) {
                    InitMatch();
                } else {
                    if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
                        Reset();
                    }
                }
            }
        }
    }
}

void Game150TagTeamWrestling::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Mat Canvas
    for (int y = 3; y <= 13; ++y) {
        for (int x = 3; x <= 13; ++x) {
            set_pixel(x, y, 40, 70, 110);
        }
    }

    // 2. Ropes
    for (int x = 2; x <= 14; ++x) {
        set_pixel(x, 2, 220, 220, 240);
        set_pixel(x, 14, 220, 220, 240);
    }
    for (int y = 2; y <= 14; ++y) {
        set_pixel(2, y, 220, 50, 50);
        set_pixel(14, y, 220, 50, 50);
    }

    // 3. Turnbuckles
    set_pixel(2, 2, 50, 220, 50);
    set_pixel(14, 2, 220, 50, 50);
    set_pixel(2, 14, 220, 220, 50);
    set_pixel(14, 14, 220, 220, 50);

    // 4. Partner
    set_pixel(1, 2, 60, 180, 255);

    // 5. Opponent
    int ox = static_cast<int>(std::round(ox_));
    int oy = static_cast<int>(std::round(oy_));
    set_pixel(ox, oy, 230, 40, 40);
    if (oy - 1 >= 0) set_pixel(ox, oy - 1, 240, 170, 130);

    // 6. Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    set_pixel(px, py, 30, 100, 240);
    if (py - 1 >= 0) set_pixel(px, py - 1, 240, 180, 140);

    // 7. Pin / Grapple indicator
    if (state_ == STATE_PINFALL) {
        int ref_count = static_cast<int>(pin_count_) + 1;
        set_pixel(8, 8, 255, 255, 255);
        for (int c = 0; c < std::min(ref_count, 3); ++c) {
            set_pixel(7 + c, 7, 255, 220, 30);
        }
    } else if (state_ == STATE_GRAPPLE) {
        int mid_x = static_cast<int>(std::round((px_ + ox_) * 0.5f));
        int mid_y = static_cast<int>(std::round((py_ + oy_) * 0.5f));
        set_pixel(mid_x, mid_y, 255, 240, 50);
    }

    // 8. Health bars
    int p_bar = static_cast<int>((p_hp_ / 100.0f) * 5.0f);
    for (int i = 0; i < p_bar; ++i) set_pixel(i, 0, 40, 160, 255);

    int o_bar = static_cast<int>((o_hp_ / 100.0f) * 5.0f);
    for (int i = 0; i < o_bar; ++i) set_pixel(15 - i, 0, 255, 40, 40);
}

} // namespace arcade
