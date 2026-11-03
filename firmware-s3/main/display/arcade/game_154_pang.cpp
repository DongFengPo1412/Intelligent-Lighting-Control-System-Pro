#include "game_154_pang.h"
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

Game154Pang::Game154Pang() {
    Reset();
}

void Game154Pang::Init() {
    Reset();
}

void Game154Pang::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game154Pang::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = FLOOR_Y;
    facing_ = 1;

    harpoon_active_ = false;
    harpoon_anchored_ = false;
    harpoon_anchor_timer_ = 0.0f;

    for (int i = 0; i < MAX_BALLS; ++i) balls_[i].active = false;

    // Ball 1: huge
    balls_[0] = {4.0f, 4.0f, 2.2f, 0.0f, 3, true};
    if (level_ > 1) {
        balls_[1] = {11.0f, 4.0f, -2.2f, 0.0f, 2, true};
    }
}

void Game154Pang::LoseLife() {
    lives_--;
    state_ = STATE_PLAYER_HIT;
    state_timer_ = 0.0f;
}

void Game154Pang::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // 1. Movement
        float speed = 5.5f;
        float dx = 0.0f;
        if (buttons & BTN_LEFT) {
            dx -= speed; facing_ = -1;
        } else if (buttons & BTN_RIGHT) {
            dx += speed; facing_ = 1;
        }
        px_ = std::max(1.0f, std::min(14.5f, px_ + dx * dt));

        // 2. Fire Harpoon
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            if (!harpoon_active_) {
                harpoon_active_ = true;
                harpoon_x_ = px_;
                harpoon_tip_y_ = FLOOR_Y - 0.5f;
                harpoon_anchored_ = false;
                harpoon_anchor_timer_ = 0.0f;
            }
        }

        // 3. Update Harpoon
        if (harpoon_active_) {
            if (!harpoon_anchored_) {
                harpoon_tip_y_ -= 16.0f * dt;
                if (harpoon_tip_y_ <= CEILING_Y) {
                    harpoon_tip_y_ = CEILING_Y;
                    harpoon_anchored_ = true;
                    harpoon_anchor_timer_ = 0.8f;
                }
            } else {
                harpoon_anchor_timer_ -= dt;
                if (harpoon_anchor_timer_ <= 0.0f) {
                    harpoon_active_ = false;
                }
            }
        }

        // 4. Update Balls
        float gravity = 14.0f;
        static const float bounce_speeds[4] = {0.0f, -5.4f, -7.0f, -8.8f};
        static const float radii[4] = {0.0f, 0.6f, 1.0f, 1.4f};

        for (int i = 0; i < MAX_BALLS; ++i) {
            if (!balls_[i].active) continue;

            auto& b = balls_[i];
            b.vy += gravity * dt;
            b.x += b.vx * dt;
            b.y += b.vy * dt;

            float r = radii[b.size];

            if (b.x <= 1.0f + r) {
                b.x = 1.0f + r;
                b.vx = std::abs(b.vx);
            } else if (b.x >= 15.0f - r) {
                b.x = 15.0f - r;
                b.vx = -std::abs(b.vx);
            }

            if (b.y >= FLOOR_Y - r) {
                b.y = FLOOR_Y - r;
                b.vy = bounce_speeds[b.size];
            }

            // Harpoon collision
            if (harpoon_active_) {
                if (b.y >= harpoon_tip_y_ && b.y <= FLOOR_Y) {
                    if (std::abs(b.x - harpoon_x_) < r + 0.3f) {
                        harpoon_active_ = false;
                        b.active = false;

                        if (b.size == 3) score_ += 100;
                        else if (b.size == 2) score_ += 200;
                        else score_ += 400;

                        if (b.size > 1) {
                            uint8_t new_size = b.size - 1;
                            // Spawn 2 smaller balls
                            for (int s = 0; s < 2; ++s) {
                                for (int j = 0; j < MAX_BALLS; ++j) {
                                    if (!balls_[j].active) {
                                        float off_x = (s == 0) ? -0.4f : 0.4f;
                                        float new_vx = (s == 0) ? -2.2f : 2.2f;
                                        balls_[j] = {b.x + off_x, b.y, new_vx, -4.0f, new_size, true};
                                        break;
                                    }
                                }
                            }
                        }
                        break;
                    }
                }
            }

            // Player collision
            if (std::hypot(b.x - px_, b.y - py_) < r + 0.6f) {
                LoseLife();
                return;
            }
        }

        // 5. Stage Clear
        bool any_ball = false;
        for (int i = 0; i < MAX_BALLS; ++i) {
            if (balls_[i].active) { any_ball = true; break; }
        }
        if (!any_ball) {
            score_ += 2000;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
        }

    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_PLAYER_HIT) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else {
                if (lives_ > 0) {
                    px_ = 7.5f;
                    py_ = FLOOR_Y;
                    harpoon_active_ = false;
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

void Game154Pang::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Borders
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 15, 100, 100, 110);
        set_pixel(x, 0, 70, 70, 80);
    }
    for (int y = 0; y < 16; ++y) {
        set_pixel(0, y, 70, 70, 80);
        set_pixel(15, y, 70, 70, 80);
    }

    // 2. Harpoon Wire
    if (harpoon_active_) {
        int hx = static_cast<int>(std::round(harpoon_x_));
        int tip_y = static_cast<int>(std::round(harpoon_tip_y_));
        set_pixel(hx, tip_y, 255, 230, 80);
        if (hx - 1 >= 0) set_pixel(hx - 1, tip_y + 1, 255, 200, 50);
        if (hx + 1 < 16) set_pixel(hx + 1, tip_y + 1, 255, 200, 50);

        for (int wy = tip_y + 1; wy <= static_cast<int>(FLOOR_Y); ++wy) {
            set_pixel(hx, wy, 200, 200, 220);
        }
    }

    // 3. Balls
    for (int i = 0; i < MAX_BALLS; ++i) {
        if (!balls_[i].active) continue;
        int bx = static_cast<int>(std::round(balls_[i].x));
        int by = static_cast<int>(std::round(balls_[i].y));

        if (balls_[i].size == 3) {
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    set_pixel(bx + dx, by + dy, 240, 40, 40);
                }
            }
            set_pixel(bx - 1, by - 1, 255, 140, 140);
        } else if (balls_[i].size == 2) {
            set_pixel(bx, by, 255, 90, 30);
            if (bx + 1 < 16) set_pixel(bx + 1, by, 240, 70, 30);
            if (by - 1 >= 0) set_pixel(bx, by - 1, 255, 160, 80);
        } else {
            set_pixel(bx, by, 255, 220, 40);
        }
    }

    // 4. Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 30, 80, 220);
        if (py - 1 >= 0) set_pixel(px, py - 1, 255, 60, 40);
        if (py - 2 >= 0) set_pixel(px, py - 2, 240, 200, 150);
    } else if (state_ == STATE_PLAYER_HIT) {
        set_pixel(px, py, 255, 50, 50);
    }

    // 5. Lives
    for (int l = 0; l < std::min((int)lives_, 3); ++l) {
        set_pixel(1 + l * 2, 0, 255, 60, 40);
    }
}

} // namespace arcade
