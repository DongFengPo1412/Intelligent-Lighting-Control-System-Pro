#include "game_120_goldminer.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game120GoldMiner::Game120GoldMiner() {
    Reset();
}

void Game120GoldMiner::Init() {
    Reset();
}

void Game120GoldMiner::Reset() {
    score_ = 0;
    round_ = 1;
    target_quota_ = 600;
    dynamite_count_ = 2;
    InitLevel();
}

void Game120GoldMiner::InitLevel() {
    state_ = STATE_MINING;
    state_timer_ = 0.0f;
    time_remaining_ = 45.0f;

    winch_x_ = 7.5f;
    winch_y_ = 1.5f;
    winch_angle_ = 0.0f;
    swing_time_ = 0.0f;
    claw_state_ = CLAW_SWINGING;

    claw_dist_ = 1.2f;
    claw_dir_x_ = 0.0f;
    claw_dir_y_ = 1.0f;
    claw_x_ = winch_x_;
    claw_y_ = winch_y_ + claw_dist_;
    hooked_item_idx_ = -1;

    SpawnItems();
}

void Game120GoldMiner::SpawnItems() {
    // 8 Subterranean Items spread across depths y=4..14
    items_[0] = {3.0f, 5.0f, ITEM_SMALL_GOLD, 100, 1.0f, 0.7f, true};
    items_[1] = {12.0f, 6.0f, ITEM_SMALL_GOLD, 100, 1.0f, 0.7f, true};
    items_[2] = {7.5f, 9.0f, ITEM_LARGE_GOLD, 500, 3.8f, 1.2f, true};
    items_[3] = {2.5f, 11.0f, ITEM_DIAMOND, 600, 0.4f, 0.6f, true};
    items_[4] = {13.0f, 12.0f, ITEM_DIAMOND, 600, 0.4f, 0.6f, true};
    items_[5] = {5.0f, 7.5f, ITEM_ROCK, 20, 5.0f, 0.9f, true};
    items_[6] = {10.5f, 8.0f, ITEM_ROCK, 20, 5.0f, 0.9f, true};
    items_[7] = {8.0f, 13.0f, ITEM_TNT_BARREL, 0, 1.0f, 0.8f, true};
}

void Game120GoldMiner::LaunchClaw() {
    if (claw_state_ != CLAW_SWINGING || state_ != STATE_MINING) return;
    claw_state_ = CLAW_EXTENDING;
    claw_dist_ = 1.2f;
    claw_dir_x_ = std::sin(winch_angle_);
    claw_dir_y_ = std::cos(winch_angle_);
    hooked_item_idx_ = -1;
}

void Game120GoldMiner::UseDynamite() {
    if (dynamite_count_ <= 0 || claw_state_ != CLAW_RETRACTING || hooked_item_idx_ < 0) return;
    dynamite_count_--;
    items_[hooked_item_idx_].active = false;
    hooked_item_idx_ = -1;
}

void Game120GoldMiner::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_ROUND_CLEAR) {
        if (state_timer_ > 1.8f) {
            round_++;
            target_quota_ += 700;
            if (dynamite_count_ < 3) dynamite_count_++;
            InitLevel();
        }
        return;
    }

    time_remaining_ -= dt;
    if (time_remaining_ <= 0.0f) {
        time_remaining_ = 0.0f;
        if (score_ >= target_quota_) {
            state_ = STATE_ROUND_CLEAR;
            state_timer_ = 0.0f;
        } else {
            state_ = STATE_GAME_OVER;
            state_timer_ = 0.0f;
        }
        return;
    }

    UpdateWinch(dt, buttons, prev_buttons);
}

void Game120GoldMiner::UpdateWinch(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (claw_state_ == CLAW_SWINGING) {
        swing_time_ += dt;
        winch_angle_ = std::sin(swing_time_ * 2.2f) * 1.22f; // Swing arc [-70° .. +70°]

        claw_dir_x_ = std::sin(winch_angle_);
        claw_dir_y_ = std::cos(winch_angle_);
        claw_dist_ = 1.2f;
        claw_x_ = winch_x_ + claw_dir_x_ * claw_dist_;
        claw_y_ = winch_y_ + claw_dir_y_ * claw_dist_;

        // Button A or Down launches claw
        if ((buttons & (BTN_A | BTN_DOWN)) && !(prev_buttons & (BTN_A | BTN_DOWN))) {
            LaunchClaw();
        }
    } else if (claw_state_ == CLAW_EXTENDING) {
        float extend_speed = 13.0f;
        claw_dist_ += extend_speed * dt;
        claw_x_ = winch_x_ + claw_dir_x_ * claw_dist_;
        claw_y_ = winch_y_ + claw_dir_y_ * claw_dist_;

        // Wall and bottom limits
        if (claw_x_ <= 0.8f || claw_x_ >= 14.8f || claw_y_ >= 15.0f) {
            claw_state_ = CLAW_RETRACTING;
        } else {
            CheckClawCollisions();
        }
    } else if (claw_state_ == CLAW_RETRACTING) {
        // Button B uses dynamite to destroy unwanted rock
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            UseDynamite();
        }

        float retract_speed = 12.0f;
        if (hooked_item_idx_ >= 0) {
            float mass = items_[hooked_item_idx_].mass;
            retract_speed = 12.0f / (1.0f + mass * 0.8f);
            items_[hooked_item_idx_].x = claw_x_;
            items_[hooked_item_idx_].y = claw_y_;
        }

        claw_dist_ -= retract_speed * dt;
        claw_x_ = winch_x_ + claw_dir_x_ * claw_dist_;
        claw_y_ = winch_y_ + claw_dir_y_ * claw_dist_;

        if (claw_dist_ <= 1.2f) {
            claw_dist_ = 1.2f;
            claw_x_ = winch_x_ + claw_dir_x_ * claw_dist_;
            claw_y_ = winch_y_ + claw_dir_y_ * claw_dist_;

            if (hooked_item_idx_ >= 0) {
                score_ += items_[hooked_item_idx_].value;
                items_[hooked_item_idx_].active = false;
                hooked_item_idx_ = -1;
            }
            claw_state_ = CLAW_SWINGING;
        }
    }
}

void Game120GoldMiner::CheckClawCollisions() {
    for (int i = 0; i < MAX_ITEMS; ++i) {
        if (!items_[i].active) continue;

        float dx = std::abs(claw_x_ - items_[i].x);
        float dy = std::abs(claw_y_ - items_[i].y);
        float hit_r = items_[i].radius;

        if (dx < hit_r && dy < hit_r) {
            if (items_[i].type == ITEM_TNT_BARREL) {
                // TNT Barrels explode and vaporize neighbors
                items_[i].active = false;
                for (int j = 0; j < MAX_ITEMS; ++j) {
                    if (items_[j].active) {
                        float ndx = std::abs(items_[i].x - items_[j].x);
                        float ndy = std::abs(items_[i].y - items_[j].y);
                        if (ndx < 2.8f && ndy < 2.8f) {
                            items_[j].active = false;
                        }
                    }
                }
                claw_state_ = CLAW_RETRACTING;
                hooked_item_idx_ = -1;
            } else {
                hooked_item_idx_ = i;
                claw_state_ = CLAW_RETRACTING;
            }
            break;
        }
    }
}

void Game120GoldMiner::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Earth & Dirt Cavern Strata (y = 3..15)
    for (int y = 3; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            uint8_t dirt = ((x + y) % 2 == 0) ? 60 : 50;
            set_pixel(x, y, dirt, dirt - 15, 20);
        }
    }

    // Surface platform at y=2
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 2, 80, 140, 50); // Green grass ledge
    }

    // 2. Subterranean Ore Items
    for (int i = 0; i < MAX_ITEMS; ++i) {
        if (!items_[i].active) continue;
        int ix = static_cast<int>(std::round(items_[i].x));
        int iy = static_cast<int>(std::round(items_[i].y));

        if (items_[i].type == ITEM_SMALL_GOLD) {
            set_pixel(ix, iy, 255, 210, 20); // Radiant gold
        } else if (items_[i].type == ITEM_LARGE_GOLD) {
            // Giant gold 2x2 nugget
            set_pixel(ix, iy, 255, 220, 30);
            set_pixel((ix + 1) % 16, iy, 240, 180, 20);
            set_pixel(ix, (iy + 1) % 16, 240, 180, 20);
            set_pixel((ix + 1) % 16, (iy + 1) % 16, 210, 150, 10);
        } else if (items_[i].type == ITEM_DIAMOND) {
            set_pixel(ix, iy, 120, 240, 255); // Glittering cyan diamond
        } else if (items_[i].type == ITEM_ROCK) {
            set_pixel(ix, iy, 140, 130, 120); // Dull rock
            set_pixel((ix + 1) % 16, iy, 100, 95, 90);
        } else if (items_[i].type == ITEM_TNT_BARREL) {
            set_pixel(ix, iy, 255, 40, 20); // Crimson explosive barrel
            set_pixel(ix, iy - 1, 255, 220, 0); // Yellow fuse
        }
    }

    // 3. Winch Line / Cable (drawn from cart to claw)
    int steps = static_cast<int>(claw_dist_ * 2.0f) + 1;
    for (int s = 0; s <= steps; ++s) {
        float t = static_cast<float>(s) / static_cast<float>(steps);
        int lx = static_cast<int>(std::round(winch_x_ + (claw_x_ - winch_x_) * t));
        int ly = static_cast<int>(std::round(winch_y_ + (claw_y_ - winch_y_) * t));
        set_pixel(lx, ly, 180, 180, 180);
    }

    // 4. Claw Tip
    int cx = static_cast<int>(std::round(claw_x_));
    int cy = static_cast<int>(std::round(claw_y_));
    set_pixel(cx, cy, 240, 240, 255);
    set_pixel(cx - 1, cy, 180, 180, 200);
    set_pixel(cx + 1, cy, 180, 180, 200);

    // 5. Miner Cart at Surface (x = 7..8, y = 1)
    set_pixel(7, 1, 220, 140, 40); // Wooden cart
    set_pixel(8, 1, 220, 140, 40);
    set_pixel(7, 0, 255, 200, 140); // Old miner head & beard
    set_pixel(8, 0, 255, 220, 0);   // Yellow miner helmet

    // 6. HUD: Quota Progress (x = 0..6, y = 0) and Dynamite (x = 13..15, y = 0)
    int prog_bars = std::min(6, static_cast<int>((static_cast<float>(score_) / static_cast<float>(target_quota_)) * 6.0f));
    for (int p = 0; p < prog_bars; ++p) {
        set_pixel(p, 0, 40, 220, 80);
    }

    for (int d = 0; d < std::min(dynamite_count_, 3); ++d) {
        set_pixel(15 - d, 0, 255, 40, 20); // Red dynamite sticks
    }
}

} // namespace arcade