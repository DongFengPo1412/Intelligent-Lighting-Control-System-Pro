#include "game_161_miner2049er.h"
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

Game161Miner2049er::Game161Miner2049er() {
    Reset();
}

void Game161Miner2049er::Init() {
    Reset();
}

void Game161Miner2049er::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

bool Game161Miner2049er::IsPlatform(int x, int y) const {
    if (x < 0 || x >= 16) return false;
    if (y == 14) return (x >= 0 && x <= 15);
    if (y == 10) return (x >= 0 && x <= 12);
    if (y == 6)  return (x >= 3 && x <= 15);
    if (y == 2)  return (x >= 0 && x <= 11);
    return false;
}

bool Game161Miner2049er::IsLadder(int x, int y) const {
    if (x == 2 && y >= 10 && y <= 13) return true;
    if (x == 11 && y >= 6 && y <= 9) return true;
    if (x == 5 && y >= 2 && y <= 5) return true;
    return false;
}

bool Game161Miner2049er::IsSlide(int x, int y) const {
    if (x == 14 && y == 6) return true;
    if (x == 13 && y >= 7 && y <= 9) return true;
    return false;
}

bool Game161Miner2049er::IsTileClaimed(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return false;
    int bit_idx = y * 16 + x;
    return (colored_tiles_[bit_idx / 8] & (1 << (bit_idx % 8))) != 0;
}

void Game161Miner2049er::ClaimTile(int x, int y) {
    if (!IsPlatform(x, y)) return;
    int bit_idx = y * 16 + x;
    if (!(colored_tiles_[bit_idx / 8] & (1 << (bit_idx % 8)))) {
        colored_tiles_[bit_idx / 8] |= (1 << (bit_idx % 8));
        claimed_count_++;
        score_ += 10;
        if (claimed_count_ >= total_claimable_) {
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 2.0f;
            score_ += 1000 * level_;
        }
    }
}

float Game161Miner2049er::GetCoveragePct() const {
    if (total_claimable_ == 0) return 100.0f;
    return (static_cast<float>(claimed_count_) / static_cast<float>(total_claimable_)) * 100.0f;
}

void Game161Miner2049er::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 1.0f;
    py_ = 13.0f;
    vx_ = 0.0f;
    vy_ = 0.0f;
    on_ground_ = true;
    on_ladder_ = false;
    sliding_ = false;

    std::memset(colored_tiles_, 0, sizeof(colored_tiles_));
    claimed_count_ = 0;
    total_claimable_ = 16 + 13 + 13 + 12; // 54 platform tiles

    mutants_[0] = {6.0f, 9.0f, 2.2f, 4.0f, 10.0f};
    mutants_[1] = {8.0f, 5.0f, -2.5f, 6.0f, 13.0f};

    ClaimTile(1, 14);
}

void Game161Miner2049er::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            level_++;
            InitLevel();
        }
        return;
    }

    if (state_ == STATE_BOB_DIED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 1.0f;
                py_ = 13.0f;
                vx_ = 0.0f;
                vy_ = 0.0f;
                on_ground_ = true;
                on_ladder_ = false;
                sliding_ = false;
            } else {
                state_ = STATE_GAME_OVER;
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    int ix = static_cast<int>(std::round(px_));
    int iy = static_cast<int>(std::round(py_));

    if (IsSlide(ix, iy) || IsSlide(ix, iy + 1)) {
        sliding_ = true;
    }

    if (sliding_) {
        vx_ = -1.5f;
        vy_ = 4.0f;
        px_ += vx_ * dt;
        py_ += vy_ * dt;
        if (py_ >= 9.0f) {
            sliding_ = false;
            py_ = 9.0f;
            vy_ = 0.0f;
        }
    } else {
        bool can_climb = IsLadder(ix, iy) || IsLadder(ix, iy + 1);

        if (can_climb && (buttons & (BTN_UP | BTN_DOWN))) {
            on_ladder_ = true;
            on_ground_ = false;
            vy_ = (buttons & BTN_UP) ? -3.5f : 3.5f;
        } else if (on_ladder_) {
            if (!can_climb) {
                on_ladder_ = false;
            } else {
                vy_ = 0.0f;
                if (buttons & BTN_UP) vy_ = -3.5f;
                else if (buttons & BTN_DOWN) vy_ = 3.5f;
            }
        }

        float walk_speed = 4.5f;
        if (buttons & BTN_LEFT) {
            vx_ = -walk_speed;
        } else if (buttons & BTN_RIGHT) {
            vx_ = walk_speed;
        } else {
            vx_ = 0.0f;
        }

        if ((buttons & BTN_A) && !(prev_buttons & BTN_A) && on_ground_ && !on_ladder_) {
            vy_ = -6.0f;
            on_ground_ = false;
        }

        if (!on_ladder_) {
            vy_ += 16.0f * dt;
            if (vy_ > 8.0f) vy_ = 8.0f;
        }

        px_ += vx_ * dt;
        py_ += vy_ * dt;

        px_ = std::max(0.0f, std::min(15.0f, px_));

        float foot_y = py_ + 1.0f;
        int cur_ix = static_cast<int>(std::round(px_));
        int floor_tile_y = static_cast<int>(std::floor(foot_y));

        if (!on_ladder_ && vy_ >= 0.0f) {
            if (IsPlatform(cur_ix, floor_tile_y) && std::abs(foot_y - static_cast<float>(floor_tile_y)) < 0.45f) {
                py_ = static_cast<float>(floor_tile_y) - 1.0f;
                vy_ = 0.0f;
                on_ground_ = true;
                ClaimTile(cur_ix, floor_tile_y);
            }
        }
    }

    for (int i = 0; i < MAX_MUTANTS; ++i) {
        mutants_[i].x += mutants_[i].vx * dt;
        if (mutants_[i].x <= mutants_[i].min_x) {
            mutants_[i].x = mutants_[i].min_x;
            mutants_[i].vx = std::abs(mutants_[i].vx);
        } else if (mutants_[i].x >= mutants_[i].max_x) {
            mutants_[i].x = mutants_[i].max_x;
            mutants_[i].vx = -std::abs(mutants_[i].vx);
        }

        if (std::hypot(mutants_[i].x - px_, mutants_[i].y - py_) < 0.85f) {
            lives_--;
            state_ = STATE_BOB_DIED;
            state_timer_ = 1.0f;
            return;
        }
    }
}

void Game161Miner2049er::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Platforms
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsPlatform(x, y)) {
                if (IsTileClaimed(x, y)) {
                    set_pixel(x, y, 0, 240, 255); // Cyan claimed
                } else {
                    set_pixel(x, y, 120, 100, 70); // Brown uncolored
                }
            }
        }
    }

    // Ladders
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsLadder(x, y)) {
                set_pixel(x, y, 220, 220, 0); // Yellow
            }
        }
    }

    // Slides
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsSlide(x, y)) {
                set_pixel(x, y, 0, 255, 60); // Green chute
            }
        }
    }

    // Mutants
    for (int i = 0; i < MAX_MUTANTS; ++i) {
        int mx = static_cast<int>(std::round(mutants_[i].x));
        int my = static_cast<int>(std::round(mutants_[i].y));
        set_pixel(mx, my, 255, 40, 40);
    }

    // Bounty Bob
    int bx = static_cast<int>(std::round(px_));
    int by = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(bx, by, 255, 255, 255);
    } else if (state_ == STATE_BOB_DIED) {
        set_pixel(bx, by, 255, 120, 0);
    }
}

} // namespace arcade
