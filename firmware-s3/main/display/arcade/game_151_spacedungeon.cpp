#include "game_151_spacedungeon.h"
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

Game151SpaceDungeon::Game151SpaceDungeon() {
    Reset();
}

void Game151SpaceDungeon::Init() {
    Reset();
}

void Game151SpaceDungeon::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game151SpaceDungeon::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    rx_ = 1;
    ry_ = 1;
    px_ = 7.5f;
    py_ = 7.5f;
    facing_x_ = 0.0f;
    facing_y_ = -1.0f;
    treasures_carried_ = 0;
    treasures_banked_ = 0;

    for (int i = 0; i < MAX_LASERS; ++i) lasers_[i].active = false;

    for (int gy = 0; gy < 3; ++gy) {
        for (int gx = 0; gx < 3; ++gx) {
            num_treasures_[gy][gx] = 0;
            num_enemies_[gy][gx] = 0;

            if (gx == 2 && gy == 2) continue; // Collect-o-matic elevator room

            treasures_[gy][gx][0] = {4.0f, 4.0f, false};
            num_treasures_[gy][gx] = 1;
            if ((gx + gy) % 2 == 1) {
                treasures_[gy][gx][1] = {11.0f, 11.0f, false};
                num_treasures_[gy][gx] = 2;
            }

            enemies_[gy][gx][0] = {4.0f, 11.0f, 2.0f, 1.5f, true};
            enemies_[gy][gx][1] = {11.0f, 4.0f, -1.8f, 2.2f, true};
            num_enemies_[gy][gx] = 2;
        }
    }

    thief_ = {0, 0, 7.5f, 7.5f, 2.5f, 0.0f, 0, true};
}

void Game151SpaceDungeon::LoseLife() {
    lives_--;
    state_ = STATE_PLAYER_HIT;
    state_timer_ = 0.0f;

    // Drop carried treasures in current room
    for (int i = 0; i < treasures_carried_; ++i) {
        if (num_treasures_[ry_][rx_] < MAX_ROOM_TREASURES) {
            float ox = (i % 2) * 1.5f - 0.75f;
            treasures_[ry_][rx_][num_treasures_[ry_][rx_]++] = {
                std::max(2.0f, std::min(13.0f, px_ + ox)),
                std::max(2.0f, std::min(13.0f, py_)),
                false
            };
        }
    }
    treasures_carried_ = 0;
}

void Game151SpaceDungeon::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // 1. Movement
        float speed = 5.5f;
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
        if (py_ <= 0.5f) {
            if (px_ >= 6.0f && px_ <= 9.0f && ry_ > 0) {
                ry_--; py_ = 14.5f;
            } else {
                py_ = 1.2f;
            }
        } else if (py_ >= 14.5f) {
            if (px_ >= 6.0f && px_ <= 9.0f && ry_ < 2) {
                ry_++; py_ = 1.2f;
            } else {
                py_ = 14.2f;
            }
        }

        if (px_ <= 0.5f) {
            if (py_ >= 6.0f && py_ <= 9.0f && rx_ > 0) {
                rx_--; px_ = 14.5f;
            } else {
                px_ = 1.2f;
            }
        } else if (px_ >= 14.5f) {
            if (py_ >= 6.0f && py_ <= 9.0f && rx_ < 2) {
                rx_++; px_ = 1.2f;
            } else {
                px_ = 14.2f;
            }
        }

        // 3. Fire Laser
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            for (int i = 0; i < MAX_LASERS; ++i) {
                if (!lasers_[i].active) {
                    lasers_[i] = {
                        px_ + facing_x_ * 0.8f,
                        py_ + facing_y_ * 0.8f,
                        facing_x_ * 14.0f,
                        facing_y_ * 14.0f,
                        true
                    };
                    break;
                }
            }
        }

        // 4. Update Lasers
        for (int i = 0; i < MAX_LASERS; ++i) {
            if (!lasers_[i].active) continue;
            lasers_[i].x += lasers_[i].vx * dt;
            lasers_[i].y += lasers_[i].vy * dt;

            if (lasers_[i].x < 0.5f || lasers_[i].x > 14.5f ||
                lasers_[i].y < 0.5f || lasers_[i].y > 14.5f) {
                lasers_[i].active = false;
                continue;
            }

            // Laser vs room enemies
            for (int e = 0; e < num_enemies_[ry_][rx_]; ++e) {
                auto& en = enemies_[ry_][rx_][e];
                if (en.alive && std::abs(lasers_[i].x - en.x) < 1.0f &&
                    std::abs(lasers_[i].y - en.y) < 1.0f) {
                    en.alive = false;
                    lasers_[i].active = false;
                    score_ += 150;
                    break;
                }
            }

            // Laser vs thief
            if (thief_.alive && thief_.rx == rx_ && thief_.ry == ry_) {
                if (std::abs(lasers_[i].x - thief_.x) < 1.0f &&
                    std::abs(lasers_[i].y - thief_.y) < 1.0f) {
                    thief_.alive = false;
                    lasers_[i].active = false;
                    score_ += 500;
                    for (int s = 0; s < thief_.stolen_loot; ++s) {
                        if (num_treasures_[ry_][rx_] < MAX_ROOM_TREASURES) {
                            treasures_[ry_][rx_][num_treasures_[ry_][rx_]++] = {thief_.x, thief_.y, false};
                        }
                    }
                    thief_.stolen_loot = 0;
                }
            }
        }

        // 5. Elevator Room (2, 2)
        if (rx_ == 2 && ry_ == 2) {
            if (std::abs(px_ - 7.5f) < 1.8f && std::abs(py_ - 7.5f) < 1.8f) {
                if (treasures_carried_ > 0) {
                    score_ += treasures_carried_ * 500;
                    treasures_banked_ += treasures_carried_;
                    treasures_carried_ = 0;
                }
                if (treasures_banked_ >= 4) {
                    score_ += 2000;
                    state_ = STATE_STAGE_CLEAR;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }

        // 6. Treasures pickup
        for (int t = 0; t < num_treasures_[ry_][rx_]; ++t) {
            auto& tr = treasures_[ry_][rx_][t];
            if (!tr.collected && std::abs(px_ - tr.x) < 1.0f && std::abs(py_ - tr.y) < 1.0f) {
                tr.collected = true;
                treasures_carried_++;
                score_ += 100;
            }
        }

        // 7. Enemies update
        for (int e = 0; e < num_enemies_[ry_][rx_]; ++e) {
            auto& en = enemies_[ry_][rx_][e];
            if (!en.alive) continue;

            en.x += en.vx * dt;
            en.y += en.vy * dt;

            if (en.x <= 1.5f || en.x >= 13.5f) en.vx = -en.vx;
            if (en.y <= 1.5f || en.y >= 13.5f) en.vy = -en.vy;

            if (std::abs(px_ - en.x) < 0.9f && std::abs(py_ - en.y) < 0.9f) {
                LoseLife();
                return;
            }
        }

        // 8. Thief AI
        if (thief_.alive && thief_.rx == rx_ && thief_.ry == ry_) {
            thief_.x += thief_.vx * dt;
            thief_.y += thief_.vy * dt;
            if (thief_.x <= 1.5f || thief_.x >= 13.5f) thief_.vx = -thief_.vx;

            if (treasures_carried_ > 0 && std::abs(px_ - thief_.x) < 1.0f &&
                std::abs(py_ - thief_.y) < 1.0f) {
                treasures_carried_--;
                thief_.stolen_loot++;
                thief_.vx = (px_ < 7.5f) ? 4.0f : -4.0f;
            }
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

void Game151SpaceDungeon::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Walls and doors
    for (int x = 0; x < 16; ++x) {
        if (!(x >= 6 && x <= 9 && ry_ > 0)) set_pixel(x, 0, 70, 70, 90);
        if (!(x >= 6 && x <= 9 && ry_ < 2)) set_pixel(x, 15, 70, 70, 90);
    }
    for (int y = 0; y < 16; ++y) {
        if (!(y >= 6 && y <= 9 && rx_ > 0)) set_pixel(0, y, 70, 70, 90);
        if (!(y >= 6 && y <= 9 && rx_ < 2)) set_pixel(15, y, 70, 70, 90);
    }

    // 2. Elevator Pad in Room (2, 2)
    if (rx_ == 2 && ry_ == 2) {
        for (int ey = 6; ey <= 9; ++ey) {
            for (int ex = 6; ex <= 9; ++ex) {
                set_pixel(ex, ey, 220, 200, 40);
            }
        }
    }

    // 3. Treasures
    for (int t = 0; t < num_treasures_[ry_][rx_]; ++t) {
        const auto& tr = treasures_[ry_][rx_][t];
        if (!tr.collected) {
            int tx = static_cast<int>(std::round(tr.x));
            int ty = static_cast<int>(std::round(tr.y));
            set_pixel(tx, ty, 255, 215, 0);
            if (ty - 1 >= 0) set_pixel(tx, ty - 1, 255, 240, 100);
        }
    }

    // 4. Thief
    if (thief_.alive && thief_.rx == rx_ && thief_.ry == ry_) {
        int thx = static_cast<int>(std::round(thief_.x));
        int thy = static_cast<int>(std::round(thief_.y));
        set_pixel(thx, thy, 50, 220, 60);
    }

    // 5. Enemies
    for (int e = 0; e < num_enemies_[ry_][rx_]; ++e) {
        const auto& en = enemies_[ry_][rx_][e];
        if (en.alive) {
            int ex = static_cast<int>(std::round(en.x));
            int ey = static_cast<int>(std::round(en.y));
            set_pixel(ex, ey, 255, 50, 50);
            if (ex - 1 >= 0) set_pixel(ex - 1, ey, 200, 30, 30);
            if (ex + 1 < 16) set_pixel(ex + 1, ey, 200, 30, 30);
        }
    }

    // 6. Lasers
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (lasers_[i].active) {
            set_pixel(static_cast<int>(std::round(lasers_[i].x)),
                      static_cast<int>(std::round(lasers_[i].y)), 100, 230, 255);
        }
    }

    // 7. Player Ship
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 40, 180, 255);
        int fx = static_cast<int>(std::round(px_ + facing_x_));
        int fy = static_cast<int>(std::round(py_ + facing_y_));
        set_pixel(fx, fy, 255, 220, 40);
    } else if (state_ == STATE_PLAYER_HIT) {
        set_pixel(px, py, 255, 80, 40);
    }

    // 8. Mini-map indicator
    set_pixel(rx_, ry_, 255, 255, 255);

    // Carried treasures
    for (int c = 0; c < std::min((int)treasures_carried_, 4); ++c) {
        set_pixel(11 + c, 0, 255, 215, 0);
    }
}

} // namespace arcade
