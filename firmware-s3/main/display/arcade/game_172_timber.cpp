#include "game_172_timber.h"
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

Game172Timber::Game172Timber() {
    Reset();
}

void Game172Timber::Init() {
    Reset();
}

void Game172Timber::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game172Timber::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 13.0f;
    facing_ = -1;
    axe_timer_ = 0.0f;

    max_chops_ = 5 + stage_;
    left_chops_ = max_chops_;
    right_chops_ = max_chops_;
    left_tree_state_ = TREE_STANDING;
    right_tree_state_ = TREE_STANDING;
    left_fall_timer_ = 0.0f;
    right_fall_timer_ = 0.0f;

    bear_x_ = 7.5f;
    bear_alive_ = true;
    bear_dir_ = 1.0f;
    bear_speed_ = 2.0f + stage_ * 0.3f;

    bee_x_ = 8.0f;
    bee_y_ = 2.0f;
    bee_alive_ = true;
    bee_speed_ = 2.2f + stage_ * 0.3f;
}

void Game172Timber::CheckStageClear() {
    if (left_tree_state_ == TREE_FELLED && right_tree_state_ == TREE_FELLED) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 2.0f;
        score_ += 2000;
    }
}

void Game172Timber::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_PLAYER_CRUSHED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                axe_timer_ = 0.0f;
            } else {
                state_ = STATE_GAME_OVER;
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if (((buttons & BTN_A) && !(prev_buttons & BTN_A)) ||
            ((buttons & BTN_B) && !(prev_buttons & BTN_B))) {
            Reset();
        }
        return;
    }

    // Movement
    float speed = 6.0f;
    if (buttons & BTN_LEFT) {
        px_ -= speed * dt;
        facing_ = -1;
    }
    if (buttons & BTN_RIGHT) {
        px_ += speed * dt;
        facing_ = 1;
    }
    px_ = std::max(3.0f, std::min(12.0f, px_));

    if (axe_timer_ > 0.0f) {
        axe_timer_ -= dt;
    }

    // Axe swing
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        axe_timer_ = 0.2f;
        if (px_ <= 3.6f && facing_ == -1) {
            if (left_tree_state_ == TREE_STANDING) {
                left_chops_--;
                score_ += 50;
                if (left_chops_ <= 0) {
                    left_tree_state_ = TREE_FALLING;
                    left_fall_timer_ = 1.0f;
                }
            }
        } else if (px_ >= 11.4f && facing_ == 1) {
            if (right_tree_state_ == TREE_STANDING) {
                right_chops_--;
                score_ += 50;
                if (right_chops_ <= 0) {
                    right_tree_state_ = TREE_FALLING;
                    right_fall_timer_ = 1.0f;
                }
            }
        }

        // Swat Bee
        if (bee_alive_) {
            float axe_x = px_ + facing_ * 0.8f;
            if (std::hypot(bee_x_ - axe_x, bee_y_ - py_) < 1.4f) {
                bee_alive_ = false;
                score_ += 300;
            }
        }
    }

    // Tree falling physics
    if (left_tree_state_ == TREE_FALLING) {
        left_fall_timer_ -= dt;
        if (left_fall_timer_ < 0.3f && left_fall_timer_ > 0.0f) {
            if (px_ <= 6.5f) {
                lives_--;
                state_ = STATE_PLAYER_CRUSHED;
                state_timer_ = 1.2f;
                return;
            }
            if (bear_alive_ && bear_x_ <= 6.5f) {
                bear_alive_ = false;
                score_ += 800;
            }
        }
        if (left_fall_timer_ <= 0.0f) {
            left_tree_state_ = TREE_FELLED;
            score_ += 500;
            CheckStageClear();
        }
    }

    if (right_tree_state_ == TREE_FALLING) {
        right_fall_timer_ -= dt;
        if (right_fall_timer_ < 0.3f && right_fall_timer_ > 0.0f) {
            if (px_ >= 8.5f) {
                lives_--;
                state_ = STATE_PLAYER_CRUSHED;
                state_timer_ = 1.2f;
                return;
            }
            if (bear_alive_ && bear_x_ >= 8.5f) {
                bear_alive_ = false;
                score_ += 800;
            }
        }
        if (right_fall_timer_ <= 0.0f) {
            right_tree_state_ = TREE_FELLED;
            score_ += 500;
            CheckStageClear();
        }
    }

    // Bear AI
    if (bear_alive_) {
        bear_x_ += bear_dir_ * bear_speed_ * dt;
        if (bear_x_ > 11.5f) {
            bear_x_ = 11.5f;
            bear_dir_ = -1.0f;
        } else if (bear_x_ < 3.5f) {
            bear_x_ = 3.5f;
            bear_dir_ = 1.0f;
        }

        if (std::abs(bear_x_ - px_) < 0.8f) {
            lives_--;
            state_ = STATE_PLAYER_CRUSHED;
            state_timer_ = 1.2f;
            return;
        }
    }

    // Bee AI
    if (bee_alive_) {
        float bdx = px_ - bee_x_;
        float bdy = py_ - bee_y_;
        float dist = std::hypot(bdx, bdy);
        if (dist > 0.1f) {
            bee_x_ += (bdx / dist) * bee_speed_ * dt;
            bee_y_ += (bdy / dist) * bee_speed_ * dt;
        }

        if (dist < 0.7f) {
            lives_--;
            state_ = STATE_PLAYER_CRUSHED;
            state_timer_ = 1.2f;
            return;
        }
    }
}

void Game172Timber::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Ground
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 14, 20, 100, 20);
        set_pixel(x, 15, 80, 50, 20);
    }

    // Left tree
    if (left_tree_state_ == TREE_STANDING) {
        for (int y = 0; y < 14; ++y) set_pixel(2, y, 120, 70, 30);
        for (int y = 0; y < 4; ++y) {
            set_pixel(1, y, 10, 140, 20);
            set_pixel(3, y, 10, 140, 20);
        }
        if (left_chops_ < max_chops_) set_pixel(3, 12, 255, 200, 50);
    } else if (left_tree_state_ == TREE_FALLING) {
        float progress = 1.0f - left_fall_timer_;
        int crash_x = static_cast<int>(2.0f + progress * 5.0f);
        for (int x = 2; x <= std::min(15, crash_x); ++x) {
            set_pixel(x, 13, 160, 90, 40);
        }
    } else if (left_tree_state_ == TREE_FELLED) {
        set_pixel(2, 13, 100, 50, 20);
    }

    // Right tree
    if (right_tree_state_ == TREE_STANDING) {
        for (int y = 0; y < 14; ++y) set_pixel(13, y, 120, 70, 30);
        for (int y = 0; y < 4; ++y) {
            set_pixel(12, y, 10, 140, 20);
            set_pixel(14, y, 10, 140, 20);
        }
        if (right_chops_ < max_chops_) set_pixel(12, 12, 255, 200, 50);
    } else if (right_tree_state_ == TREE_FALLING) {
        float progress = 1.0f - right_fall_timer_;
        int crash_x = static_cast<int>(13.0f - progress * 5.0f);
        for (int x = std::max(0, crash_x); x <= 13; ++x) {
            set_pixel(x, 13, 160, 90, 40);
        }
    } else if (right_tree_state_ == TREE_FELLED) {
        set_pixel(13, 13, 100, 50, 20);
    }

    // Bear
    if (bear_alive_) {
        int bx = static_cast<int>(std::round(bear_x_));
        set_pixel(bx, 13, 100, 40, 20);
        set_pixel(bx, 12, 140, 60, 30);
    }

    // Bee
    if (bee_alive_) {
        int beex = static_cast<int>(std::round(bee_x_));
        int beey = static_cast<int>(std::round(bee_y_));
        set_pixel(beex, beey, 255, 240, 30);
    }

    // Lumberjack
    int px = static_cast<int>(std::round(px_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, 13, 30, 80, 200);
        set_pixel(px, 12, 220, 40, 30);
        set_pixel(px, 11, 240, 180, 140);
        if (axe_timer_ > 0.0f) {
            set_pixel(px + facing_, 12, 220, 220, 230);
        }
    } else if (state_ == STATE_PLAYER_CRUSHED) {
        set_pixel(px, 13, 255, 100, 0);
        set_pixel(px, 12, 255, 0, 0);
    }
}

} // namespace arcade

