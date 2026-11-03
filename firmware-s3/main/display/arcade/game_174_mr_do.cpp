#include "game_174_mr_do.h"
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

Game174MrDo::Game174MrDo() {
    Reset();
}

void Game174MrDo::Init() {
    Reset();
}

void Game174MrDo::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

bool Game174MrDo::IsDirt(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return false;
    int idx = y * 16 + x;
    return (dirt_mask_[idx / 8] & (1 << (idx % 8))) != 0;
}

void Game174MrDo::ClearDirt(int x, int y) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = y * 16 + x;
        dirt_mask_[idx / 8] &= ~(1 << (idx % 8));
    }
}

bool Game174MrDo::IsCherry(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return false;
    int idx = y * 16 + x;
    return (cherry_mask_[idx / 8] & (1 << (idx % 8))) != 0;
}

void Game174MrDo::RemoveCherry(int x, int y) {
    if (IsCherry(x, y)) {
        int idx = y * 16 + x;
        cherry_mask_[idx / 8] &= ~(1 << (idx % 8));
        if (cherries_left_ > 0) cherries_left_--;
    }
}

void Game174MrDo::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 13.0f;
    facing_x_ = 0.0f;
    facing_y_ = -1.0f;
    speed_ = 5.0f;
    ball_.active = false;

    std::memset(dirt_mask_, 0xFF, sizeof(dirt_mask_));
    // Clear borders
    for (int i = 0; i < 16; ++i) {
        ClearDirt(i, 0);
        ClearDirt(i, 15);
        ClearDirt(0, i);
        ClearDirt(15, i);
    }
    // Starting shaft
    for (int y = 8; y <= 13; ++y) {
        ClearDirt(7, y);
        ClearDirt(8, y);
    }

    std::memset(cherry_mask_, 0, sizeof(cherry_mask_));
    cherries_left_ = 0;
    static const int cy_list[] = {3, 6, 9};
    static const int cx_list[] = {2, 3, 12, 13};
    for (int y : cy_list) {
        for (int x : cx_list) {
            int idx = y * 16 + x;
            cherry_mask_[idx / 8] |= (1 << (idx % 8));
            cherries_left_++;
        }
    }

    apples_[0] = {4.0f, 4.0f, false, 0.0f, 0.0f};
    apples_[1] = {11.0f, 4.0f, false, 0.0f, 0.0f};
    apples_[2] = {8.0f, 7.0f, false, 0.0f, 0.0f};
    for (int i = 0; i < NUM_APPLES; ++i) {
        ClearDirt(static_cast<int>(apples_[i].x), static_cast<int>(apples_[i].y));
    }

    monsters_[0] = {0, 3.0f, 2.0f, 2.2f + stage_ * 0.2f, true};
    monsters_[1] = {1, 12.0f, 2.0f, 2.2f + stage_ * 0.2f, true};
    for (int i = 0; i < NUM_MONSTERS; ++i) {
        ClearDirt(static_cast<int>(monsters_[i].x), static_cast<int>(monsters_[i].y));
    }
}

void Game174MrDo::CheckMonstersEliminated() {
    bool any_alive = false;
    for (int i = 0; i < NUM_MONSTERS; ++i) {
        if (monsters_[i].alive) { any_alive = true; break; }
    }
    if (!any_alive) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 2.0f;
        score_ += 2000;
    }
}

void Game174MrDo::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_PLAYER_DIED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                py_ = 13.0f;
                ball_.active = false;
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

    // Controls
    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT)  { dx -= 1.0f; facing_x_ = -1.0f; facing_y_ = 0.0f; }
    if (buttons & BTN_RIGHT) { dx += 1.0f; facing_x_ = 1.0f;  facing_y_ = 0.0f; }
    if (buttons & BTN_UP)    { dy -= 1.0f; facing_x_ = 0.0f;  facing_y_ = -1.0f; }
    if (buttons & BTN_DOWN)  { dy += 1.0f; facing_x_ = 0.0f;  facing_y_ = 1.0f; }

    if (dx != 0.0f || dy != 0.0f) {
        float target_px = px_ + dx * speed_ * dt;
        float target_py = py_ + dy * speed_ * dt;

        // Push apples
        for (int i = 0; i < NUM_APPLES; ++i) {
            if (!apples_[i].falling && std::hypot(apples_[i].x - target_px, apples_[i].y - target_py) < 0.8f) {
                if (dx != 0.0f) {
                    float new_ax = apples_[i].x + dx * (speed_ * 0.6f) * dt;
                    if (new_ax >= 1.0f && new_ax <= 14.0f) apples_[i].x = new_ax;
                }
                target_px = px_;
            }
        }

        px_ = std::max(1.0f, std::min(14.0f, target_px));
        py_ = std::max(1.0f, std::min(14.0f, target_py));

        int cx = static_cast<int>(std::round(px_));
        int cy = static_cast<int>(std::round(py_));
        if (IsDirt(cx, cy)) {
            ClearDirt(cx, cy);
            score_ += 5;
        }

        if (IsCherry(cx, cy)) {
            RemoveCherry(cx, cy);
            score_ += 50;
            if (cherries_left_ == 0) {
                state_ = STATE_STAGE_CLEAR;
                state_timer_ = 2.0f;
                score_ += 3000;
                return;
            }
        }
    }

    // Power Ball throw
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A) && !ball_.active) {
        ball_.active = true;
        ball_.cooldown = 0.3f;
        ball_.x = px_;
        ball_.y = py_;
        float b_speed = 10.0f;
        ball_.vx = facing_x_ * b_speed;
        ball_.vy = facing_y_ * b_speed;
        if (ball_.vx == 0.0f && ball_.vy == 0.0f) ball_.vy = -b_speed;
    }

    if (ball_.active) {
        if (ball_.cooldown > 0.0f) ball_.cooldown -= dt;
        ball_.x += ball_.vx * dt;
        ball_.y += ball_.vy * dt;

        if (ball_.x <= 1.0f) { ball_.x = 1.0f; ball_.vx = std::abs(ball_.vx); }
        else if (ball_.x >= 14.0f) { ball_.x = 14.0f; ball_.vx = -std::abs(ball_.vx); }

        if (ball_.y <= 1.0f) { ball_.y = 1.0f; ball_.vy = std::abs(ball_.vy); }
        else if (ball_.y >= 14.0f) { ball_.y = 14.0f; ball_.vy = -std::abs(ball_.vy); }

        for (int i = 0; i < NUM_MONSTERS; ++i) {
            if (monsters_[i].alive && std::hypot(monsters_[i].x - ball_.x, monsters_[i].y - ball_.y) < 0.9f) {
                monsters_[i].alive = false;
                ball_.active = false;
                score_ += 500;
                CheckMonstersEliminated();
                break;
            }
        }

        if (ball_.active && ball_.cooldown <= 0.0f && std::hypot(px_ - ball_.x, py_ - ball_.y) < 0.8f) {
            ball_.active = false;
        }
    }

    // Apples falling
    for (int i = 0; i < NUM_APPLES; ++i) {
        int ax = static_cast<int>(std::round(apples_[i].x));
        int ay = static_cast<int>(std::round(apples_[i].y));

        if (ay + 1 < 16 && !IsDirt(ax, ay + 1)) {
            if (!apples_[i].falling) {
                apples_[i].wobble += dt;
                if (apples_[i].wobble > 0.4f) {
                    apples_[i].falling = true;
                    apples_[i].fall_vy = 8.0f;
                }
            } else {
                apples_[i].y += apples_[i].fall_vy * dt;
                for (int m = 0; m < NUM_MONSTERS; ++m) {
                    if (monsters_[m].alive && std::hypot(monsters_[m].x - apples_[i].x, monsters_[m].y - apples_[i].y) < 0.9f) {
                        monsters_[m].alive = false;
                        score_ += 1000;
                        CheckMonstersEliminated();
                    }
                }

                if (std::hypot(px_ - apples_[i].x, py_ - apples_[i].y) < 0.8f) {
                    lives_--;
                    state_ = STATE_PLAYER_DIED;
                    state_timer_ = 1.0f;
                    return;
                }

                if (apples_[i].y >= 14.0f || (static_cast<int>(apples_[i].y) + 1 < 16 && IsDirt(ax, static_cast<int>(apples_[i].y) + 1))) {
                    apples_[i].falling = false;
                    apples_[i].wobble = 0.0f;
                }
            }
        }
    }

    // Monsters AI
    for (int i = 0; i < NUM_MONSTERS; ++i) {
        if (!monsters_[i].alive) continue;
        float mdx = px_ - monsters_[i].x;
        float mdy = py_ - monsters_[i].y;
        float dist = std::hypot(mdx, mdy);
        if (dist > 0.1f) {
            monsters_[i].x += (mdx / dist) * monsters_[i].speed * dt;
            monsters_[i].y += (mdy / dist) * monsters_[i].speed * dt;
        }

        if (std::hypot(monsters_[i].x - px_, monsters_[i].y - py_) < 0.8f) {
            lives_--;
            state_ = STATE_PLAYER_DIED;
            state_timer_ = 1.0f;
            return;
        }
    }
}

void Game174MrDo::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Soil & dug paths
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsDirt(x, y)) {
                set_pixel(x, y, 100, 60, 20);
            } else {
                set_pixel(x, y, 10, 10, 15);
            }
        }
    }

    // Cherries
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsCherry(x, y)) set_pixel(x, y, 255, 30, 80);
        }
    }

    // Apples
    for (int i = 0; i < NUM_APPLES; ++i) {
        int ax = static_cast<int>(std::round(apples_[i].x));
        int ay = static_cast<int>(std::round(apples_[i].y));
        set_pixel(ax, ay, 240, 20, 20);
        set_pixel(ax, ay - 1, 40, 180, 40);
    }

    // Monsters
    for (int i = 0; i < NUM_MONSTERS; ++i) {
        if (monsters_[i].alive) {
            int mx = static_cast<int>(std::round(monsters_[i].x));
            int my = static_cast<int>(std::round(monsters_[i].y));
            set_pixel(mx, my, 220, 40, 180);
            set_pixel(mx, my - 1, 255, 200, 0);
        }
    }

    // Ball
    if (ball_.active) {
        int bx = static_cast<int>(std::round(ball_.x));
        int by = static_cast<int>(std::round(ball_.y));
        set_pixel(bx, by, 80, 255, 255);
    }

    // Mr. Do
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 255, 255, 255);
        set_pixel(px, py - 1, 255, 0, 0);
        set_pixel(px, py + 1, 255, 200, 0);
    } else if (state_ == STATE_PLAYER_DIED) {
        set_pixel(px, py, 255, 100, 0);
    }
}

} // namespace arcade
