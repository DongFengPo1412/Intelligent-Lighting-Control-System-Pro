#include "game_178_puzzloop.h"
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

Game178PuzzLoop::Game178PuzzLoop() {
    GenerateTrack();
    Reset();
}

void Game178PuzzLoop::Init() {
    GenerateTrack();
    Reset();
}

void Game178PuzzLoop::GenerateTrack() {
    int steps = 45;
    for (int i = 0; i < steps; ++i) {
        float theta = (steps - 1 - i) * (3.5f * 3.14159f / steps);
        float r = 1.2f + ((steps - 1 - i) / static_cast<float>(steps)) * 5.8f;
        track_[i].x = 7.5f + std::cos(theta) * r;
        track_[i].y = 7.5f + std::sin(theta) * r;
    }
    track_[45].x = 7.5f;
    track_[45].y = 7.5f;
}

void Game178PuzzLoop::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game178PuzzLoop::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    aim_angle_ = -3.14159f / 2.0f;
    cur_color_ = COLOR_RED;
    next_color_ = COLOR_BLUE;
    bullet_.active = false;

    train_len_ = 0;
    static const uint8_t pattern[] = {
        COLOR_RED, COLOR_RED, COLOR_GREEN, COLOR_GREEN, COLOR_BLUE, COLOR_BLUE, COLOR_YELLOW, COLOR_YELLOW
    };
    for (int r = 0; r < 2 + stage_; ++r) {
        for (int p = 0; p < 6; ++p) {
            if (train_len_ < MAX_TRAIN) {
                train_[train_len_++] = pattern[p];
            }
        }
    }

    train_progress_ = 0.0f;
    train_speed_ = 0.8f + stage_ * 0.15f;
}

void Game178PuzzLoop::CheckMatch3(int idx) {
    if (idx >= train_len_) return;

    uint8_t target = train_[idx];
    int left = idx;
    while (left > 0 && train_[left - 1] == target) left--;

    int right = idx;
    while (right < train_len_ - 1 && train_[right + 1] == target) right++;

    int match_count = right - left + 1;
    if (match_count >= 3) {
        int remove_len = match_count;
        for (int i = left; i + remove_len < train_len_; ++i) {
            train_[i] = train_[i + remove_len];
        }
        train_len_ -= remove_len;
        score_ += match_count * 100;

        if (left > 0 && left < train_len_) {
            if (train_[left - 1] == train_[left]) {
                train_progress_ = std::max(0.0f, train_progress_ - 2.0f);
                score_ += 300;
                CheckMatch3(left);
            }
        }

        if (train_len_ == 0) {
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 2.0f;
            score_ += 3000;
        }
    }
}

void Game178PuzzLoop::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_DRAIN_LOST) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                train_progress_ = 0.0f;
                bullet_.active = false;
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

    // Aim rotation
    float rot_speed = 4.5f;
    if (buttons & BTN_LEFT)  aim_angle_ -= rot_speed * dt;
    if (buttons & BTN_RIGHT) aim_angle_ += rot_speed * dt;

    // Swap color (Button B)
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        std::swap(cur_color_, next_color_);
    }

    // Shoot (Button A)
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A) && !bullet_.active) {
        bullet_.active = true;
        bullet_.x = 7.5f;
        bullet_.y = 7.5f;
        float b_spd = 14.0f;
        bullet_.vx = std::cos(aim_angle_) * b_spd;
        bullet_.vy = std::sin(aim_angle_) * b_spd;
        bullet_.color = cur_color_;
        cur_color_ = next_color_;
        next_color_ = (cur_color_ % 4) + 1;
    }

    // Advance Train
    train_progress_ += train_speed_ * dt;

    int head_idx = static_cast<int>(train_progress_) + train_len_ - 1;
    if (head_idx >= TRACK_STEPS - 1 && train_len_ > 0) {
        lives_--;
        state_ = STATE_DRAIN_LOST;
        state_timer_ = 1.2f;
        return;
    }

    // Update Bullet
    if (bullet_.active) {
        bullet_.x += bullet_.vx * dt;
        bullet_.y += bullet_.vy * dt;

        if (bullet_.x < 0.0f || bullet_.x > 15.0f || bullet_.y < 0.0f || bullet_.y > 15.0f) {
            bullet_.active = false;
        } else if (train_len_ > 0) {
            int hit_index = -1;
            for (int i = 0; i < train_len_; ++i) {
                int t_idx = static_cast<int>(train_progress_) + i;
                if (t_idx >= 0 && t_idx < TRACK_STEPS) {
                    if (std::hypot(track_[t_idx].x - bullet_.x, track_[t_idx].y - bullet_.y) < 0.9f) {
                        hit_index = i;
                        break;
                    }
                }
            }

            if (hit_index != -1 && train_len_ < MAX_TRAIN) {
                for (int i = train_len_; i > hit_index; --i) {
                    train_[i] = train_[i - 1];
                }
                train_[hit_index] = bullet_.color;
                train_len_++;
                bullet_.active = false;
                score_ += 20;
                CheckMatch3(hit_index);
            }
        }
    }
}

void Game178PuzzLoop::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Track groove
    for (int i = 0; i < TRACK_STEPS; ++i) {
        set_pixel(static_cast<int>(std::round(track_[i].x)),
                  static_cast<int>(std::round(track_[i].y)),
                  30, 30, 45);
    }

    // Center Drain
    set_pixel(7, 7, 255, 60, 0);
    set_pixel(8, 7, 255, 60, 0);
    set_pixel(7, 8, 255, 60, 0);
    set_pixel(8, 8, 255, 60, 0);

    auto get_color = [](uint8_t col, uint8_t& r, uint8_t& g, uint8_t& b) {
        switch (col) {
            case COLOR_RED:    r = 255; g = 30;  b = 30;  break;
            case COLOR_GREEN:  r = 40;  g = 240; b = 50;  break;
            case COLOR_BLUE:   r = 40;  g = 120; b = 255; break;
            case COLOR_YELLOW: r = 255; g = 230; b = 30;  break;
            default:           r = 255; g = 255; b = 255; break;
        }
    };

    // Marbles
    for (int i = 0; i < train_len_; ++i) {
        int t_idx = static_cast<int>(train_progress_) + i;
        if (t_idx >= 0 && t_idx < TRACK_STEPS) {
            uint8_t r, g, b;
            get_color(train_[i], r, g, b);
            set_pixel(static_cast<int>(std::round(track_[t_idx].x)),
                      static_cast<int>(std::round(track_[t_idx].y)),
                      r, g, b);
        }
    }

    // Bullet
    if (bullet_.active) {
        uint8_t r, g, b;
        get_color(bullet_.color, r, g, b);
        set_pixel(static_cast<int>(std::round(bullet_.x)),
                  static_cast<int>(std::round(bullet_.y)),
                  r, g, b);
    }

    // Turret
    uint8_t cr, cg, cb;
    get_color(cur_color_, cr, cg, cb);
    set_pixel(7, 7, cr, cg, cb);

    int ax = static_cast<int>(std::round(7.5f + std::cos(aim_angle_) * 1.5f));
    int ay = static_cast<int>(std::round(7.5f + std::sin(aim_angle_) * 1.5f));
    set_pixel(ax, ay, 240, 240, 240);
}

} // namespace arcade
