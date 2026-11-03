#include "game_159_spyvsspy.h"
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

Game159SpyVsSpy::Game159SpyVsSpy() {
    Reset();
}

void Game159SpyVsSpy::Init() {
    Reset();
}

void Game159SpyVsSpy::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game159SpyVsSpy::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    rx_ = 0;
    ry_ = 0;
    px_ = 7.5f;
    py_ = 7.5f;
    facing_x_ = 0.0f;
    facing_y_ = 1.0f;

    has_briefcase_ = false;
    items_mask_ = 0;

    for (int y = 0; y < 2; ++y) {
        for (int x = 0; x < 2; ++x) {
            num_furniture_[y][x] = 0;
        }
    }

    // Room 0,0: Briefcase, Money
    furniture_[0][0][0] = {4.0f, 5.0f, 1, false, false}; // Briefcase
    furniture_[0][0][1] = {11.0f, 11.0f, 4, false, false}; // Money
    num_furniture_[0][0] = 2;

    // Room 1,0: Passport
    furniture_[0][1][0] = {11.0f, 5.0f, 3, false, false}; // Passport
    furniture_[0][1][1] = {4.0f, 11.0f, 0, false, false};
    num_furniture_[0][1] = 2;

    // Room 0,1: Plans
    furniture_[1][0][0] = {4.0f, 5.0f, 2, false, false}; // Plans
    furniture_[1][0][1] = {11.0f, 11.0f, 0, false, false};
    num_furniture_[1][0] = 2;

    // Room 1,1: Key
    furniture_[1][1][0] = {4.0f, 5.0f, 5, false, false}; // Key
    num_furniture_[1][1] = 1;

    rival_rx_ = 1;
    rival_ry_ = 0;
    rival_x_ = 7.5f;
    rival_y_ = 7.5f;
    rival_alive_ = true;
    rival_respawn_timer_ = 0.0f;
}

void Game159SpyVsSpy::LoseLife() {
    lives_--;
    state_ = STATE_SPY_BLOWN_UP;
    state_timer_ = 0.0f;
}

void Game159SpyVsSpy::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // 1. Movement
        float speed = 5.0f;
        float dx = 0.0f;
        float dy = 0.0f;
        if (buttons & BTN_LEFT) {
            dx -= speed; facing_x_ = -1.0f; facing_y_ = 0.0f;
        } else if (buttons & BTN_RIGHT) {
            dx += speed; facing_x_ = 1.0f; facing_y_ = 0.0f;
        } else if (buttons & BTN_UP) {
            dy -= speed; facing_x_ = 0.0f; facing_y_ = -1.0f;
        } else if (buttons & BTN_DOWN) {
            dy += speed; facing_x_ = 0.0f; facing_y_ = 1.0f;
        }

        px_ += dx * dt;
        py_ += dy * dt;

        // 2. Doorways
        if (py_ <= 0.8f) {
            if (px_ >= 6.0f && px_ <= 9.0f && ry_ > 0) { ry_--; py_ = 14.2f; }
            else py_ = 1.5f;
        } else if (py_ >= 14.5f) {
            if (px_ >= 6.0f && px_ <= 9.0f && ry_ < 1) { ry_++; py_ = 1.5f; }
            else py_ = 14.0f;
        }

        if (px_ <= 0.8f) {
            if (py_ >= 6.0f && py_ <= 9.0f && rx_ > 0) { rx_--; px_ = 14.2f; }
            else px_ = 1.5f;
        } else if (px_ >= 14.5f) {
            if (py_ >= 6.0f && py_ <= 9.0f && rx_ < 1) { rx_++; px_ = 1.5f; }
            else px_ = 14.0f;
        }

        // 3. Search Key A
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            if (rx_ == 1 && ry_ == 1) {
                if (std::abs(px_ - 12.0f) < 1.8f && std::abs(py_ - 12.0f) < 1.8f) {
                    if (has_briefcase_ && (items_mask_ == 0x0F)) {
                        score_ += 3000;
                        state_ = STATE_STAGE_CLEAR;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            }

            for (int i = 0; i < num_furniture_[ry_][rx_]; ++i) {
                auto& f = furniture_[ry_][rx_][i];
                if (std::abs(px_ - f.x) < 1.4f && std::abs(py_ - f.y) < 1.4f) {
                    if (f.has_bomb) {
                        f.has_bomb = false;
                        LoseLife();
                        return;
                    }

                    if (!f.searched) {
                        f.searched = true;
                        if (f.item_type == 1) {
                            has_briefcase_ = true;
                            score_ += 500;
                        } else if (f.item_type >= 2 && f.item_type <= 5) {
                            items_mask_ |= (1 << (f.item_type - 2));
                            score_ += 250;
                        }
                    }
                    break;
                }
            }
        }

        // 4. Lay trap Key B
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            for (int i = 0; i < num_furniture_[ry_][rx_]; ++i) {
                auto& f = furniture_[ry_][rx_][i];
                if (std::abs(px_ - f.x) < 1.4f && std::abs(py_ - f.y) < 1.4f) {
                    if (!f.has_bomb) {
                        f.has_bomb = true;
                        score_ += 100;
                    }
                    break;
                }
            }
        }

        // 5. Black Spy AI
        if (!rival_alive_) {
            rival_respawn_timer_ -= dt;
            if (rival_respawn_timer_ <= 0.0f) {
                rival_alive_ = true;
                rival_rx_ = (rx_ + 1) % 2;
                rival_ry_ = (ry_ + 1) % 2;
                rival_x_ = 7.5f;
                rival_y_ = 7.5f;
            }
        }

        if (rival_alive_ && rival_rx_ == rx_ && rival_ry_ == ry_) {
            float rdx = px_ - rival_x_;
            float rdy = py_ - rival_y_;
            float dist = std::hypot(rdx, rdy);
            if (dist > 0.8f) {
                rival_x_ += (rdx / dist) * 2.8f * dt;
                rival_y_ += (rdy / dist) * 2.8f * dt;
            }

            for (int i = 0; i < num_furniture_[ry_][rx_]; ++i) {
                auto& f = furniture_[ry_][rx_][i];
                if (std::abs(rival_x_ - f.x) < 1.2f && std::abs(rival_y_ - f.y) < 1.2f) {
                    if (f.has_bomb) {
                        f.has_bomb = false;
                        rival_alive_ = false;
                        rival_respawn_timer_ = 3.0f;
                        score_ += 1000;
                        break;
                    }
                }
            }

            if (dist < 0.9f && (buttons & BTN_A) && !(prev_buttons & BTN_A)) {
                rival_alive_ = false;
                rival_respawn_timer_ = 3.0f;
                score_ += 500;
            }
        }

    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_SPY_BLOWN_UP) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else {
                if (lives_ > 0) {
                    px_ = 7.5f;
                    py_ = 7.5f;
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

void Game159SpyVsSpy::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Walls
    for (int x = 0; x < 16; ++x) {
        if (!(x >= 6 && x <= 9 && ry_ > 0)) set_pixel(x, 0, 90, 80, 110);
        if (!(x >= 6 && x <= 9 && ry_ < 1)) set_pixel(x, 15, 90, 80, 110);
    }
    for (int y = 0; y < 16; ++y) {
        if (!(y >= 6 && y <= 9 && rx_ > 0)) set_pixel(0, y, 90, 80, 110);
        if (!(y >= 6 && y <= 9 && rx_ < 1)) set_pixel(15, y, 90, 80, 110);
    }

    // 2. Airport Gate in Room (1, 1)
    if (rx_ == 1 && ry_ == 1) {
        set_pixel(12, 12, 60, 200, 255);
        set_pixel(12, 11, 240, 240, 40);
        set_pixel(13, 12, 60, 200, 255);
    }

    // 3. Furniture
    for (int i = 0; i < num_furniture_[ry_][rx_]; ++i) {
        const auto& f = furniture_[ry_][rx_][i];
        int fx = static_cast<int>(std::round(f.x));
        int fy = static_cast<int>(std::round(f.y));
        set_pixel(fx, fy, 160, 100, 50);
        if (fx + 1 < 16) set_pixel(fx + 1, fy, 160, 100, 50);
        if (fy - 1 >= 0) set_pixel(fx, fy - 1, 130, 80, 40);
        if (f.has_bomb && fy - 1 >= 0 && fx + 1 < 16) {
            set_pixel(fx + 1, fy - 1, 255, 40, 40);
        }
    }

    // 4. Black Spy
    if (rival_alive_ && rival_rx_ == rx_ && rival_ry_ == ry_) {
        int rx = static_cast<int>(std::round(rival_x_));
        int ry = static_cast<int>(std::round(rival_y_));
        set_pixel(rx, ry, 30, 30, 30);
        if (ry - 1 >= 0) set_pixel(rx, ry - 1, 240, 200, 160);
        if (ry - 2 >= 0) set_pixel(rx, ry - 2, 20, 20, 20);
    }

    // 5. White Spy
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 240, 240, 240);
        if (py - 1 >= 0) set_pixel(px, py - 1, 240, 200, 160);
        if (py - 2 >= 0) set_pixel(px, py - 2, 230, 230, 230);
        if (has_briefcase_ && px + 1 < 16) set_pixel(px + 1, py, 140, 70, 30);
    } else if (state_ == STATE_SPY_BLOWN_UP) {
        set_pixel(px, py, 255, 60, 30);
    }

    // 6. Items & Lives
    if (has_briefcase_) set_pixel(0, 0, 140, 70, 30);
    for (int i = 0; i < 4; ++i) {
        if (items_mask_ & (1 << i)) set_pixel(2 + i, 0, 40, 220, 120);
    }
    for (int l = 0; l < std::min((int)lives_, 3); ++l) {
        set_pixel(15 - l * 2, 0, 240, 240, 240);
    }
}

} // namespace arcade
