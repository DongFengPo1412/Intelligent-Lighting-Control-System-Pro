#include "game_153_circuscharlie.h"
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

Game153CircusCharlie::Game153CircusCharlie() {
    Reset();
}

void Game153CircusCharlie::Init() {
    Reset();
}

void Game153CircusCharlie::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game153CircusCharlie::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    track_pos_ = 0.0f;
    y_ = GROUND_Y;
    vy_ = 0.0f;
    is_jumping_ = false;

    fire_pots_[0] = 16.0f;
    fire_pots_[1] = 32.0f;
    fire_pots_[2] = 48.0f;
    fire_pots_[3] = 64.0f;
    num_fire_pots_ = 4;

    fire_hoops_[0] = {10.0f, 1.2f, true, false};
    fire_hoops_[1] = {24.0f, 1.5f, false, false};
    fire_hoops_[2] = {40.0f, 1.2f, true, false};
    fire_hoops_[3] = {56.0f, 1.6f, false, false};
    fire_hoops_[4] = {72.0f, 1.4f, true, false};
    num_fire_hoops_ = 5;
}

void Game153CircusCharlie::LoseLife() {
    lives_--;
    state_ = STATE_CHARLIE_DOWN;
    state_timer_ = 0.0f;
}

void Game153CircusCharlie::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // 1. Lion reins
        float gallop_speed = 3.2f;
        if (buttons & BTN_LEFT) {
            gallop_speed = -1.2f;
        } else if (buttons & BTN_RIGHT) {
            gallop_speed = 5.2f;
        }

        track_pos_ += gallop_speed * dt;
        track_pos_ = std::max(0.0f, std::min(COURSE_LENGTH, track_pos_));

        // 2. Jump
        if (((buttons & (BTN_A | BTN_UP)) && !(prev_buttons & (BTN_A | BTN_UP))) ||
            ((buttons & BTN_A) && !is_jumping_)) {
            vy_ = -6.4f;
            is_jumping_ = true;
        }

        if (is_jumping_) {
            vy_ += 13.0f * dt;
            y_ += vy_ * dt;
            if (y_ >= GROUND_Y) {
                y_ = GROUND_Y;
                vy_ = 0.0f;
                is_jumping_ = false;
            }
        }

        // 3. Move Hoops
        for (int i = 0; i < num_fire_hoops_; ++i) {
            fire_hoops_[i].track_pos -= fire_hoops_[i].speed * dt;
            if (fire_hoops_[i].track_pos < track_pos_ - 10.0f) {
                fire_hoops_[i].track_pos = track_pos_ + 18.0f;
                fire_hoops_[i].money_taken = false;
            }
        }

        // 4. Pot collisions
        for (int i = 0; i < num_fire_pots_; ++i) {
            float dist = std::abs(track_pos_ - fire_pots_[i]);
            if (dist < 1.0f && y_ > GROUND_Y - 1.2f) {
                LoseLife();
                return;
            }
        }

        // 5. Hoop collisions
        for (int i = 0; i < num_fire_hoops_; ++i) {
            float dist = std::abs(track_pos_ - fire_hoops_[i].track_pos);
            if (dist < 0.9f) {
                if (y_ >= 9.0f && y_ <= 12.0f) {
                    if (fire_hoops_[i].has_money && !fire_hoops_[i].money_taken) {
                        fire_hoops_[i].money_taken = true;
                        score_ += 500;
                    } else {
                        score_ += 10;
                    }
                } else {
                    LoseLife();
                    return;
                }
            }
        }

        // 6. Finish
        if (track_pos_ >= COURSE_LENGTH - 1.5f) {
            score_ += 2000;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
        }

    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_CHARLIE_DOWN) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else {
                if (lives_ > 0) {
                    track_pos_ = std::max(0.0f, track_pos_ - 6.0f);
                    y_ = GROUND_Y;
                    vy_ = 0.0f;
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

void Game153CircusCharlie::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    int screen_charlie_x = 4;

    // 1. Sawdust Floor
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 14, 210, 160, 60);
        set_pixel(x, 15, 120, 80, 30);
    }

    // 2. Audience Bunting
    for (int x = 0; x < 16; ++x) {
        if (x % 2 == 0) set_pixel(x, 1, 220, 40, 40);
        else set_pixel(x, 1, 240, 240, 240);
    }

    // 3. Victory Podium
    int podium_sx = static_cast<int>(std::round(screen_charlie_x + (COURSE_LENGTH - track_pos_)));
    if (podium_sx >= 0 && podium_sx < 16) {
        set_pixel(podium_sx, 13, 60, 180, 255);
        set_pixel(podium_sx, 12, 255, 220, 40);
    }

    // 4. Fire Pots
    for (int i = 0; i < num_fire_pots_; ++i) {
        int sx = static_cast<int>(std::round(screen_charlie_x + (fire_pots_[i] - track_pos_)));
        if (sx >= 0 && sx < 16) {
            set_pixel(sx, 13, 60, 60, 60);
            set_pixel(sx, 12, 255, 60, 20);
            set_pixel(sx, 11, 255, 200, 30);
        }
    }

    // 5. Fire Hoops
    for (int i = 0; i < num_fire_hoops_; ++i) {
        int sx = static_cast<int>(std::round(screen_charlie_x + (fire_hoops_[i].track_pos - track_pos_)));
        if (sx >= 0 && sx < 16) {
            set_pixel(sx, 13, 255, 40, 20);
            set_pixel(sx, 9, 255, 40, 20);
            if (sx - 1 >= 0) set_pixel(sx - 1, 11, 255, 140, 30);
            if (sx + 1 < 16) set_pixel(sx + 1, 11, 255, 140, 30);
            if (fire_hoops_[i].has_money && !fire_hoops_[i].money_taken) {
                set_pixel(sx, 11, 255, 230, 40);
            }
        }
    }

    // 6. Charlie & Lion
    int cx = screen_charlie_x;
    int cy = static_cast<int>(std::round(y_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(cx, cy, 230, 140, 30);
        if (cx + 1 < 16) set_pixel(cx + 1, cy, 230, 140, 30);
        if (cx - 1 >= 0) set_pixel(cx - 1, cy, 180, 100, 20);
        if (cy - 1 >= 0) set_pixel(cx, cy - 1, 40, 120, 255);
        if (cy - 2 >= 0) set_pixel(cx, cy - 2, 255, 230, 200);
    } else if (state_ == STATE_CHARLIE_DOWN) {
        set_pixel(cx, cy, 255, 40, 20);
    }

    // 7. Progress & Lives
    int prog_dots = static_cast<int>((track_pos_ / COURSE_LENGTH) * 8.0f);
    for (int i = 0; i < prog_dots; ++i) set_pixel(8 + i, 0, 40, 220, 120);
    for (int l = 0; l < std::min((int)lives_, 3); ++l) set_pixel(l * 2, 0, 240, 60, 60);
}

} // namespace arcade

