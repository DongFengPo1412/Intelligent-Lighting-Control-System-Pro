#include "game_169_warlords.h"
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

Game169Warlords::Game169Warlords() {
    Reset();
}

void Game169Warlords::Init() {
    Reset();
}

void Game169Warlords::Reset() {
    score_ = 0;
    round_ = 1;
    InitRound();
}

void Game169Warlords::GetShieldCoord(int wid, float t, float& out_x, float& out_y) const {
    if (wid == 0) {
        out_x = 0.5f + t * 4.0f;
        out_y = 11.5f + t * 3.5f;
    } else if (wid == 1) {
        out_x = 0.5f + t * 4.0f;
        out_y = 4.5f - t * 4.0f;
    } else if (wid == 2) {
        out_x = 11.5f + t * 3.5f;
        out_y = 0.5f + t * 4.0f;
    } else {
        out_x = 11.5f + t * 3.5f;
        out_y = 15.0f - t * 3.5f;
    }
}

uint8_t Game169Warlords::GetAliveCpus() const {
    uint8_t count = 0;
    for (int i = 1; i < NUM_WARLORDS; ++i) {
        if (warlords_[i].alive) count++;
    }
    return count;
}

void Game169Warlords::InitRound() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;

    warlords_[0] = {0, 1.0f, 14.0f, 0.5f, true};
    warlords_[1] = {1, 1.0f, 1.0f,  0.5f, true};
    warlords_[2] = {2, 14.0f, 1.0f, 0.5f, true};
    warlords_[3] = {3, 14.0f, 14.0f,0.5f, true};

    static const int8_t init_b[NUM_WARLORDS][MAX_BRICKS_PER_CASTLE][2] = {
        {{3, 14}, {3, 13}, {3, 12}, {2, 12}, {1, 12}, {0, 12}},
        {{3, 1},  {3, 2},  {3, 3},  {2, 3},  {1, 3},  {0, 3}},
        {{12, 1}, {12, 2}, {12, 3}, {13, 3}, {14, 3}, {15, 3}},
        {{12, 14},{12, 13},{12, 12},{13, 12},{14, 12},{15, 12}},
    };

    for (int w = 0; w < NUM_WARLORDS; ++w) {
        for (int b = 0; b < MAX_BRICKS_PER_CASTLE; ++b) {
            bricks_[w][b] = {init_b[w][b][0], init_b[w][b][1], true};
        }
    }

    ball_speed_ = 7.0f + static_cast<float>(round_) * 0.5f;
    ball_x_ = 7.5f;
    ball_y_ = 7.5f;
    ball_vx_ = std::cos(0.8f) * ball_speed_;
    ball_vy_ = std::sin(0.8f) * ball_speed_;
    ball_caught_by_ = -1;
    ball_catch_timer_ = 0.0f;
}

void Game169Warlords::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_ROUND_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            round_++;
            InitRound();
        }
        return;
    }

    if (state_ == STATE_PLAYER_ELIMINATED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            state_ = STATE_GAME_OVER;
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    // Player Shield
    if (warlords_[0].alive) {
        if (buttons & (BTN_LEFT | BTN_UP)) {
            warlords_[0].shield_t = std::max(0.0f, warlords_[0].shield_t - 2.5f * dt);
        } else if (buttons & (BTN_RIGHT | BTN_DOWN)) {
            warlords_[0].shield_t = std::min(1.0f, warlords_[0].shield_t + 2.5f * dt);
        }
    }

    // CPU Shields
    for (int wid = 1; wid < NUM_WARLORDS; ++wid) {
        if (!warlords_[wid].alive) continue;
        float target_t = 0.5f;
        if (wid == 1) {
            target_t = (ball_x_ < 7.5f) ? (ball_x_ / 6.0f) : 0.5f;
        } else if (wid == 2) {
            target_t = (ball_x_ > 7.5f) ? (ball_y_ / 6.0f) : 0.5f;
        } else {
            target_t = (ball_x_ > 7.5f) ? ((ball_x_ - 10.0f) / 5.0f) : 0.5f;
        }
        target_t = std::max(0.0f, std::min(1.0f, target_t));

        float diff = target_t - warlords_[wid].shield_t;
        float step = 1.8f * dt;
        if (std::abs(diff) > step) {
            warlords_[wid].shield_t += (diff > 0 ? step : -step);
        }
    }

    // Fireball
    if (ball_caught_by_ != -1) {
        int wid = ball_caught_by_;
        float sx, sy;
        GetShieldCoord(wid, warlords_[wid].shield_t, sx, sy);
        ball_x_ = sx;
        ball_y_ = sy;
        ball_catch_timer_ -= dt;

        bool release = false;
        if (wid == 0) {
            if (((buttons & BTN_A) && !(prev_buttons & BTN_A)) || ball_catch_timer_ <= 0.0f) {
                release = true;
            }
        } else {
            if (ball_catch_timer_ <= 0.0f) release = true;
        }

        if (release) {
            float aim_dx = 7.5f - ball_x_;
            float aim_dy = 7.5f - ball_y_;
            float d_len = std::hypot(aim_dx, aim_dy);
            float power = ball_speed_ * 1.3f;
            ball_vx_ = (aim_dx / d_len) * power;
            ball_vy_ = (aim_dy / d_len) * power;
            ball_caught_by_ = -1;
        }
    } else {
        ball_x_ += ball_vx_ * dt;
        ball_y_ += ball_vy_ * dt;

        if (ball_x_ <= 0.0f) { ball_x_ = 0.0f; ball_vx_ = std::abs(ball_vx_); }
        else if (ball_x_ >= 15.0f) { ball_x_ = 15.0f; ball_vx_ = -std::abs(ball_vx_); }
        if (ball_y_ <= 0.0f) { ball_y_ = 0.0f; ball_vy_ = std::abs(ball_vy_); }
        else if (ball_y_ >= 15.0f) { ball_y_ = 15.0f; ball_vy_ = -std::abs(ball_vy_); }

        // Shield collisions
        for (int wid = 0; wid < NUM_WARLORDS; ++wid) {
            if (!warlords_[wid].alive) continue;
            float sx, sy;
            GetShieldCoord(wid, warlords_[wid].shield_t, sx, sy);
            if (std::hypot(sx - ball_x_, sy - ball_y_) < 1.1f) {
                if (wid == 0 && (buttons & BTN_A)) {
                    ball_caught_by_ = 0;
                    ball_catch_timer_ = 1.5f;
                    score_ += 50;
                    break;
                } else {
                    float dx = ball_x_ - warlords_[wid].king_x;
                    float dy = ball_y_ - warlords_[wid].king_y;
                    float d_len = std::hypot(dx, dy);
                    if (d_len > 0.1f) {
                        ball_vx_ = (dx / d_len) * ball_speed_;
                        ball_vy_ = (dy / d_len) * ball_speed_;
                        if (wid == 0) score_ += 25;
                    }
                    break;
                }
            }
        }

        // Brick collisions
        int bx = static_cast<int>(std::round(ball_x_));
        int by = static_cast<int>(std::round(ball_y_));
        for (int wid = 0; wid < NUM_WARLORDS; ++wid) {
            for (int b = 0; b < MAX_BRICKS_PER_CASTLE; ++b) {
                if (bricks_[wid][b].active && bricks_[wid][b].x == bx && bricks_[wid][b].y == by) {
                    bricks_[wid][b].active = false;
                    ball_vx_ = -ball_vx_;
                    ball_vy_ = -ball_vy_;
                    if (wid != 0) score_ += 100;
                    break;
                }
            }
        }

        // King assassinations
        for (int wid = 0; wid < NUM_WARLORDS; ++wid) {
            if (warlords_[wid].alive && std::hypot(warlords_[wid].king_x - ball_x_, warlords_[wid].king_y - ball_y_) < 1.0f) {
                warlords_[wid].alive = false;
                if (wid == 0) {
                    state_ = STATE_PLAYER_ELIMINATED;
                    state_timer_ = 1.5f;
                    return;
                } else {
                    score_ += 1000;
                }
            }
        }

        if (GetAliveCpus() == 0 && warlords_[0].alive) {
            state_ = STATE_ROUND_CLEAR;
            state_timer_ = 2.0f;
            score_ += 3000;
        }
    }
}

void Game169Warlords::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Bricks
    for (int wid = 0; wid < NUM_WARLORDS; ++wid) {
        for (int b = 0; b < MAX_BRICKS_PER_CASTLE; ++b) {
            if (bricks_[wid][b].active) {
                int bx = bricks_[wid][b].x;
                int by = bricks_[wid][b].y;
                if (wid == 0) set_pixel(bx, by, 0, 180, 255);
                else if (wid == 1) set_pixel(bx, by, 255, 60, 60);
                else if (wid == 2) set_pixel(bx, by, 255, 200, 0);
                else set_pixel(bx, by, 40, 220, 80);
            }
        }
    }

    // Kings
    for (int wid = 0; wid < NUM_WARLORDS; ++wid) {
        if (warlords_[wid].alive) {
            int kx = static_cast<int>(std::round(warlords_[wid].king_x));
            int ky = static_cast<int>(std::round(warlords_[wid].king_y));
            set_pixel(kx, ky, 255, 255, 255);
            set_pixel(kx, (ky > 8) ? (ky - 1) : (ky + 1), 255, 215, 0);
        }
    }

    // Shields
    for (int wid = 0; wid < NUM_WARLORDS; ++wid) {
        if (warlords_[wid].alive) {
            float sx, sy;
            GetShieldCoord(wid, warlords_[wid].shield_t, sx, sy);
            int ix = static_cast<int>(std::round(sx));
            int iy = static_cast<int>(std::round(sy));
            if (wid == 0) set_pixel(ix, iy, 255, 255, 255);
            else set_pixel(ix, iy, 200, 150, 255);
        }
    }

    // Fireball
    int fx = static_cast<int>(std::round(ball_x_));
    int fy = static_cast<int>(std::round(ball_y_));
    set_pixel(fx, fy, 255, 120, 0);
    set_pixel(fx, fy - 1, 255, 40, 0);
}

} // namespace arcade

