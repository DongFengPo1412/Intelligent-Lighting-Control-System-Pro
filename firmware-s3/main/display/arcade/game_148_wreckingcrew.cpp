#include "game_148_wreckingcrew.h"
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

static const int FLOOR_Y[4] = {2, 6, 10, 14};

Game148WreckingCrew::Game148WreckingCrew() {
    Reset();
}

void Game148WreckingCrew::Init() {
    Reset();
}

void Game148WreckingCrew::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game148WreckingCrew::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 2.0f;
    py_ = 14.0f;
    facing_ = 1;
    hammer_timer_ = 0.0f;

    // Ladders
    ladders_[0] = {4, 10, 14};
    ladders_[1] = {11, 6, 10};
    ladders_[2] = {6, 2, 6};
    num_ladders_ = 3;

    // Walls
    num_walls_ = 10;
    walls_[0] = {6, 14, 1, false};
    walls_[1] = {9, 14, 2, true};
    walls_[2] = {12, 14, 1, false};

    walls_[3] = {2, 10, 1, false};
    walls_[4] = {7, 10, 1, false};

    walls_[5] = {3, 6, 2, true};
    walls_[6] = {9, 6, 1, false};
    walls_[7] = {13, 6, 1, false};

    walls_[8] = {9, 2, 1, false};
    walls_[9] = {12, 2, 2, true};

    // Dynamite
    dynamite_[0] = {8, 14, true};
    dynamite_[1] = {8, 6, true};
    num_dynamite_ = 2;

    // Enemies
    enemies_[0] = {13.0f, 14.0f, -1.8f, true};
    enemies_[1] = {2.0f, 6.0f, 1.8f, true};
    num_enemies_ = 2;
}

bool Game148WreckingCrew::IsOnLadder(float x, float y) const {
    for (int i = 0; i < num_ladders_; ++i) {
        const auto& lad = ladders_[i];
        if (std::abs(x - lad.x) < 0.8f && (y >= lad.y_top - 0.2f && y <= lad.y_bot + 0.2f)) {
            return true;
        }
    }
    return false;
}

int Game148WreckingCrew::GetNearestFloor(float y) const {
    int closest = FLOOR_Y[0];
    float min_d = std::abs(y - closest);
    for (int i = 0; i < 4; ++i) {
        float d = std::abs(y - FLOOR_Y[i]);
        if (d < min_d) {
            min_d = d;
            closest = FLOOR_Y[i];
        }
    }
    return closest;
}

void Game148WreckingCrew::StrikeHammer() {
    int target_x = static_cast<int>(std::round(px_ + facing_ * 0.8f));
    int target_y = static_cast<int>(std::round(py_));

    // Dynamite check
    for (int i = 0; i < num_dynamite_; ++i) {
        if (dynamite_[i].active && dynamite_[i].x == target_x && dynamite_[i].y == target_y) {
            dynamite_[i].active = false;
            score_ += 500;
            DetonateDynamite(target_y);
            return;
        }
    }

    // Wall check
    for (int i = 0; i < num_walls_; ++i) {
        if (walls_[i].x == target_x && walls_[i].y == target_y) {
            walls_[i].hp--;
            if (walls_[i].hp <= 0) {
                score_ += walls_[i].is_pillar ? 250 : 100;
            }
            break;
        }
    }

    // Compact alive walls
    int write_idx = 0;
    for (int i = 0; i < num_walls_; ++i) {
        if (walls_[i].hp > 0) {
            walls_[write_idx++] = walls_[i];
        }
    }
    num_walls_ = write_idx;
}

void Game148WreckingCrew::DetonateDynamite(int floor_y) {
    int write_idx = 0;
    for (int i = 0; i < num_walls_; ++i) {
        if (walls_[i].y != floor_y) {
            walls_[write_idx++] = walls_[i];
        }
    }
    num_walls_ = write_idx;

    for (int i = 0; i < num_enemies_; ++i) {
        if (static_cast<int>(std::round(enemies_[i].y)) == floor_y) {
            enemies_[i].alive = false;
            score_ += 300;
        }
    }
}

void Game148WreckingCrew::LoseLife() {
    lives_--;
    state_ = STATE_PLAYER_HIT;
    state_timer_ = 0.0f;
}

void Game148WreckingCrew::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        if (hammer_timer_ > 0.0f) hammer_timer_ -= dt;

        bool on_ladder = IsOnLadder(px_, py_);
        bool is_climbing = false;

        if (on_ladder) {
            float climb_speed = 3.5f;
            if (buttons & BTN_UP) {
                py_ = std::max(2.0f, py_ - climb_speed * dt);
                is_climbing = true;
            } else if (buttons & BTN_DOWN) {
                py_ = std::min(14.0f, py_ + climb_speed * dt);
                is_climbing = true;
            }
        }

        if (!is_climbing) {
            int nearest_floor = GetNearestFloor(py_);
            if (std::abs(py_ - nearest_floor) < 0.6f) {
                py_ = static_cast<float>(nearest_floor);
            }

            float walk_speed = 4.2f;
            float dx = 0.0f;
            if (buttons & BTN_LEFT) {
                dx -= walk_speed;
                facing_ = -1;
            } else if (buttons & BTN_RIGHT) {
                dx += walk_speed;
                facing_ = 1;
            }
            px_ = std::max(1.0f, std::min(14.0f, px_ + dx * dt));
        }

        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            hammer_timer_ = 0.25f;
            StrikeHammer();
        }

        if (num_walls_ == 0) {
            score_ += 2000;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
            return;
        }

        for (int i = 0; i < num_enemies_; ++i) {
            auto& e = enemies_[i];
            if (!e.alive) continue;

            e.x += e.vx * dt;
            if (e.x <= 1.5f) {
                e.x = 1.5f;
                e.vx = std::abs(e.vx);
            } else if (e.x >= 13.5f) {
                e.x = 13.5f;
                e.vx = -std::abs(e.vx);
            }

            if (std::abs(px_ - e.x) < 0.8f && std::abs(py_ - e.y) < 0.8f) {
                LoseLife();
                return;
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
                    px_ = 2.0f;
                    py_ = 14.0f;
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

void Game148WreckingCrew::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Scaffolding Floors
    for (int i = 0; i < 4; ++i) {
        int fy = FLOOR_Y[i];
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, fy + 1 < 16 ? fy + 1 : 15, 70, 70, 80);
        }
    }

    // 2. Ladders
    for (int i = 0; i < num_ladders_; ++i) {
        const auto& lad = ladders_[i];
        for (int ly = lad.y_top; ly <= lad.y_bot; ++ly) {
            set_pixel(lad.x, ly, 180, 160, 40);
        }
    }

    // 3. Dynamite
    for (int i = 0; i < num_dynamite_; ++i) {
        if (dynamite_[i].active) {
            set_pixel(dynamite_[i].x, dynamite_[i].y, 255, 30, 30);
        }
    }

    // 4. Walls
    for (int i = 0; i < num_walls_; ++i) {
        if (walls_[i].is_pillar) {
            set_pixel(walls_[i].x, walls_[i].y, 130, 130, 150);
        } else {
            set_pixel(walls_[i].x, walls_[i].y, 200, 100, 40);
        }
    }

    // 5. Enemies
    for (int i = 0; i < num_enemies_; ++i) {
        if (enemies_[i].alive) {
            set_pixel(static_cast<int>(std::round(enemies_[i].x)),
                      static_cast<int>(std::round(enemies_[i].y)), 180, 40, 200);
        }
    }

    // 6. Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 40, 90, 255);
        if (py - 1 >= 0) set_pixel(px, py - 1, 255, 40, 40);
        if (hammer_timer_ > 0.0f) {
            int hx = px + facing_;
            set_pixel(hx, py, 220, 180, 50);
        }
    } else if (state_ == STATE_PLAYER_HIT) {
        set_pixel(px, py, 255, 60, 30);
    }

    // 7. Lives
    for (int l = 0; l < std::min((int)lives_, 3); ++l) {
        set_pixel(1 + l * 2, 0, 255, 40, 40);
    }
}

} // namespace arcade

