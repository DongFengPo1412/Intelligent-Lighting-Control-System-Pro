#include "game_104_digdug2.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game104DigDug2::Game104DigDug2() {
    Reset();
}

void Game104DigDug2::Init() {
    Reset();
}

void Game104DigDug2::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitIsland();
}

void Game104DigDug2::InitIsland() {
    state_ = STATE_EXPLORING;
    state_timer_ = 0.0f;
    monsters_defeated_ = 0;
    pump_timer_ = 0.0f;
    active_peg_idx_ = -1;

    px_ = 8.0f;
    py_ = 8.0f;
    facing_x_ = 1;
    facing_y_ = 0;

    std::memset(island_grid_, false, sizeof(island_grid_));
    std::memset(collapse_mask_, false, sizeof(collapse_mask_));

    // Green tropical island from (2,2) to (13,13)
    for (int y = 2; y <= 13; ++y) {
        for (int x = 2; x <= 13; ++x) {
            island_grid_[y][x] = true;
        }
    }

    // Initialize 6 Peg Stakes
    int peg_coords[MAX_PEGS][2] = {
        {4, 4}, {8, 4}, {11, 4},
        {4, 11}, {8, 11}, {11, 11}
    };
    for (int i = 0; i < MAX_PEGS; ++i) {
        pegs_[i].x = peg_coords[i][0];
        pegs_[i].y = peg_coords[i][1];
        pegs_[i].drilled = false;
        pegs_[i].active = true;
    }

    for (int i = 0; i < MAX_CRACKS; ++i) {
        cracks_[i].active = false;
    }

    // Spawn Monsters: Pookas & Fygars
    for (int i = 0; i < MAX_MONSTERS; ++i) {
        monsters_[i].active = true;
        monsters_[i].is_fygar = (i == 1);
        monsters_[i].x = (i == 0) ? 3.0f : (i == 1 ? 12.0f : 10.0f);
        monsters_[i].y = (i == 0) ? 3.0f : (i == 1 ? 12.0f : 3.0f);
        monsters_[i].vx = (i % 2 == 0) ? 2.0f : -2.0f;
        monsters_[i].vy = 0.0f;
        monsters_[i].stun_timer = 0.0f;
    }
}

void Game104DigDug2::TriggerDrillAtNearestPeg() {
    for (int i = 0; i < MAX_PEGS; ++i) {
        if (!pegs_[i].active || pegs_[i].drilled) continue;
        float dx = std::abs(px_ - static_cast<float>(pegs_[i].x));
        float dy = std::abs(py_ - static_cast<float>(pegs_[i].y));
        if (dx < 1.4f && dy < 1.4f) {
            active_peg_idx_ = i;
            state_ = STATE_DRILLING_FAULT;
            state_timer_ = 0.0f;
            break;
        }
    }
}

void Game104DigDug2::ExecuteFaultLineBreak(int peg_idx) {
    if (peg_idx < 0 || peg_idx >= MAX_PEGS) return;
    pegs_[peg_idx].drilled = true;

    // Break off the closest coastline section corresponding to peg
    int px = pegs_[peg_idx].x;
    int py = pegs_[peg_idx].y;

    std::memset(collapse_mask_, false, sizeof(collapse_mask_));

    // Determine fault direction towards coast
    if (px <= 5) {
        // West peninsula collapse (x from 0 to 4)
        for (int y = 0; y < 16; ++y) {
            for (int x = 0; x <= 4; ++x) {
                if (island_grid_[y][x]) collapse_mask_[y][x] = true;
            }
        }
    } else if (px >= 10) {
        // East peninsula collapse (x from 11 to 15)
        for (int y = 0; y < 16; ++y) {
            for (int x = 11; x < 16; ++x) {
                if (island_grid_[y][x]) collapse_mask_[y][x] = true;
            }
        }
    } else if (py <= 6) {
        // North coast collapse (y from 0 to 4)
        for (int y = 0; y <= 4; ++y) {
            for (int x = 0; x < 16; ++x) {
                if (island_grid_[y][x]) collapse_mask_[y][x] = true;
            }
        }
    } else {
        // South coast collapse (y from 11 to 15)
        for (int y = 11; y < 16; ++y) {
            for (int x = 0; x < 16; ++x) {
                if (island_grid_[y][x]) collapse_mask_[y][x] = true;
            }
        }
    }

    state_ = STATE_ISLAND_COLLAPSE;
    state_timer_ = 0.0f;
}

void Game104DigDug2::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_PLAYER_DROWN) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                state_ = STATE_EXPLORING;
                state_timer_ = 0.0f;
                px_ = 8.0f;
                py_ = 8.0f;
            }
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.2f) {
            stage_++;
            InitIsland();
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DRILLING_FAULT) {
        if (state_timer_ > 0.4f) {
            ExecuteFaultLineBreak(active_peg_idx_);
        }
        return;
    }

    if (state_ == STATE_ISLAND_COLLAPSE) {
        UpdateCracksAndCollapse(dt);
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateMonsters(dt);
    CheckCollisions();

    // Check stage clear
    if (monsters_defeated_ >= MAX_MONSTERS && state_ != STATE_STAGE_CLEAR) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1500;
    }
}

void Game104DigDug2::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_spd = 5.0f;
    float next_x = px_;
    float next_y = py_;

    if (buttons & BTN_LEFT) {
        next_x -= move_spd * dt;
        facing_x_ = -1;
        facing_y_ = 0;
    } else if (buttons & BTN_RIGHT) {
        next_x += move_spd * dt;
        facing_x_ = 1;
        facing_y_ = 0;
    } else if (buttons & BTN_UP) {
        next_y -= move_spd * dt;
        facing_x_ = 0;
        facing_y_ = -1;
    } else if (buttons & BTN_DOWN) {
        next_y += move_spd * dt;
        facing_x_ = 0;
        facing_y_ = 1;
    }

    int check_x = static_cast<int>(std::round(next_x));
    int check_y = static_cast<int>(std::round(next_y));
    if (check_x >= 0 && check_x < 16 && check_y >= 0 && check_y < 16) {
        if (island_grid_[check_y][check_x]) {
            px_ = next_x;
            py_ = next_y;
        } else {
            // Fell off into the ocean!
            state_ = STATE_PLAYER_DROWN;
            state_timer_ = 0.0f;
            return;
        }
    }

    // Button B: Jackhammer Drill Fault line at nearest peg
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        TriggerDrillAtNearestPeg();
    }

    // Button A: Harpoon Pump stun shot
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        float pump_x = px_ + static_cast<float>(facing_x_) * 1.8f;
        float pump_y = py_ + static_cast<float>(facing_y_) * 1.8f;
        for (int m = 0; m < MAX_MONSTERS; ++m) {
            if (!monsters_[m].active) continue;
            if (std::abs(monsters_[m].x - pump_x) < 1.4f &&
                std::abs(monsters_[m].y - pump_y) < 1.4f) {
                monsters_[m].stun_timer = 2.0f;
                score_ += 50;
            }
        }
    }
}

void Game104DigDug2::UpdateMonsters(float dt) {
    for (int m = 0; m < MAX_MONSTERS; ++m) {
        if (!monsters_[m].active) continue;

        if (monsters_[m].stun_timer > 0.0f) {
            monsters_[m].stun_timer -= dt;
            continue;
        }

        // Move towards player
        float to_x = px_ - monsters_[m].x;
        float to_y = py_ - monsters_[m].y;
        float dist = std::sqrt(to_x * to_x + to_y * to_y);
        if (dist > 0.1f) {
            float spd = monsters_[m].is_fygar ? 2.2f : 2.6f;
            float next_mx = monsters_[m].x + (to_x / dist) * spd * dt;
            float next_my = monsters_[m].y + (to_y / dist) * spd * dt;

            int chk_x = static_cast<int>(std::round(next_mx));
            int chk_y = static_cast<int>(std::round(next_my));
            if (chk_x >= 0 && chk_x < 16 && chk_y >= 0 && chk_y < 16 && island_grid_[chk_y][chk_x]) {
                monsters_[m].x = next_mx;
                monsters_[m].y = next_my;
            }
        }
    }
}

void Game104DigDug2::UpdateCracksAndCollapse(float dt) {
    if (state_timer_ > 0.6f) {
        // Complete the island collapse: land mass turns to ocean
        int drowned_count = 0;

        for (int y = 0; y < 16; ++y) {
            for (int x = 0; x < 16; ++x) {
                if (collapse_mask_[y][x]) {
                    island_grid_[y][x] = false;
                }
            }
        }

        // Check if monsters drowned
        for (int m = 0; m < MAX_MONSTERS; ++m) {
            if (!monsters_[m].active) continue;
            int mx = static_cast<int>(std::round(monsters_[m].x));
            int my = static_cast<int>(std::round(monsters_[m].y));
            if (collapse_mask_[my][mx]) {
                monsters_[m].active = false;
                monsters_defeated_++;
                drowned_count++;
            }
        }

        // Multi-kill bonus points
        if (drowned_count == 1) score_ += 400;
        else if (drowned_count == 2) score_ += 1000;
        else if (drowned_count >= 3) score_ += 2000;

        // Check if Taizo was on the collapsing land!
        int px = static_cast<int>(std::round(px_));
        int py = static_cast<int>(std::round(py_));
        if (collapse_mask_[py][px]) {
            state_ = STATE_PLAYER_DROWN;
            state_timer_ = 0.0f;
            return;
        }

        state_ = STATE_EXPLORING;
        state_timer_ = 0.0f;
    }
}

void Game104DigDug2::CheckCollisions() {
    for (int m = 0; m < MAX_MONSTERS; ++m) {
        if (!monsters_[m].active || monsters_[m].stun_timer > 0.0f) continue;
        float dx = std::abs(px_ - monsters_[m].x);
        float dy = std::abs(py_ - monsters_[m].y);
        if (dx < 0.9f && dy < 0.9f) {
            state_ = STATE_PLAYER_DROWN;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game104DigDug2::Render(uint8_t* fb) {
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

    // Ocean Background & Island Terrain
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (island_grid_[y][x]) {
                if (state_ == STATE_ISLAND_COLLAPSE && collapse_mask_[y][x]) {
                    // Shaking / crumbling sandy land
                    set_pixel(x, y, 220, 160, 60);
                } else {
                    // Lush green tropical island grass
                    set_pixel(x, y, 40, 160, 50);
                }
            } else {
                // Azure Ocean
                set_pixel(x, y, 10, 60, 160);
            }
        }
    }

    // Peg Stakes
    for (int i = 0; i < MAX_PEGS; ++i) {
        if (!pegs_[i].active) continue;
        if (pegs_[i].drilled) {
            // Cracked fault peg
            set_pixel(pegs_[i].x, pegs_[i].y, 140, 80, 20);
        } else {
            // Solid wooden/iron stake
            set_pixel(pegs_[i].x, pegs_[i].y, 240, 220, 120);
        }
    }

    // Drilling Crack FX
    if (state_ == STATE_DRILLING_FAULT && active_peg_idx_ >= 0) {
        int ax = pegs_[active_peg_idx_].x;
        int ay = pegs_[active_peg_idx_].y;
        set_pixel(ax, ay, 255, 255, 255);
        set_pixel(ax + 1, ay, 255, 200, 0);
        set_pixel(ax - 1, ay, 255, 200, 0);
    }

    // Monsters: Red Pooka & Green Fygar
    for (int m = 0; m < MAX_MONSTERS; ++m) {
        if (!monsters_[m].active) continue;
        int mx = static_cast<int>(std::round(monsters_[m].x));
        int my = static_cast<int>(std::round(monsters_[m].y));

        if (monsters_[m].stun_timer > 0.0f) {
            // Stunned / inflating in white/yellow
            set_pixel(mx, my, 255, 255, 200);
            set_pixel(mx, my - 1, 255, 255, 100);
        } else if (monsters_[m].is_fygar) {
            // Fygar (Green Dragon)
            set_pixel(mx, my, 30, 220, 60);
            set_pixel(mx + 1, my, 255, 100, 20); // Wings
        } else {
            // Pooka (Red round goggles)
            set_pixel(mx, my, 240, 40, 30);
            set_pixel(mx, my - 1, 255, 240, 50); // Yellow goggles
        }
    }

    // Taizo Hori
    int tx = static_cast<int>(std::round(px_));
    int ty = static_cast<int>(std::round(py_));

    if (state_ == STATE_PLAYER_DROWN) {
        set_pixel(tx, ty, 80, 140, 255); // Splash bubbles
        set_pixel(tx - 1, ty, 200, 240, 255);
        set_pixel(tx + 1, ty, 200, 240, 255);
    } else {
        // Taizo in white suit & red helmet
        set_pixel(tx, ty, 240, 240, 250); // White suit
        set_pixel(tx, ty - 1, 230, 40, 30); // Red helmet
        set_pixel(tx + facing_x_, ty + facing_y_, 255, 220, 60); // Jackhammer/drill tip
    }

    // HUD: Lives on top left
    for (int l = 0; l < std::min(lives_, 3); ++l) {
        set_pixel(l, 0, 255, 220, 0);
    }
}

} // namespace arcade
