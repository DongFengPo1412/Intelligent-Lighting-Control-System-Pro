#include "game_119_pitfall2.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr float PI = 3.1415926535f;

Game119Pitfall2::Game119Pitfall2() {
    Reset();
}

void Game119Pitfall2::Init() {
    Reset();
}

void Game119Pitfall2::Reset() {
    score_ = 0;
    lives_ = 3;
    InitCavern();
}

void Game119Pitfall2::InitCavern() {
    state_ = STATE_EXPLORING;
    state_timer_ = 0.0f;
    treasures_collected_ = 0;

    px_ = 2.0f;
    py_ = 3.0f;
    vy_ = 0.0f;
    on_ground_ = true;
    on_ladder_ = false;
    on_vine_ = false;
    on_balloon_ = false;

    checkpoint_x_ = 2.0f;
    checkpoint_y_ = 3.0f;
    checkpoint_active_ = false;

    balloon_x_ = 10.5f;
    balloon_y_ = 13.0f;
    balloon_dir_ = -1.0f;
    vine_angle_ = 0.0f;

    // Treasures
    treasures_[0] = {13.0f, 3.0f, 200, false}; // Gold Ingot (Surface)
    treasures_[1] = {1.5f, 7.0f, 300, false};  // Silver Bar (Cavern 1)
    treasures_[2] = {14.0f, 12.0f, 500, false}; // Mayan Golden Idol (Cavern 2)

    // Hazards
    hazards_[0] = {7.5f, 4.0f, 0.0f, 2, true};  // Crocodile in lagoon
    hazards_[1] = {7.0f, 7.0f, 1.8f, 0, true};  // Scorpion crawling on Floor 1
    hazards_[2] = {10.0f, 10.5f, -2.5f, 1, true}; // Vampire bat flying in cave
}

void Game119Pitfall2::SetPlayerPos(float x, float y) {
    px_ = x;
    py_ = y;
}

void Game119Pitfall2::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_EXPEDITION_CLEAR) {
        if (state_timer_ > 1.8f) {
            InitCavern();
        }
        return;
    }

    if (state_ == STATE_CHECKPOINT_RESPAWN) {
        if (state_timer_ > 0.8f) {
            state_ = STATE_EXPLORING;
            px_ = checkpoint_x_;
            py_ = checkpoint_y_;
            vy_ = 0.0f;
            on_vine_ = false;
            on_balloon_ = false;
        }
        return;
    }

    UpdateMechanisms(dt);
    UpdateHazards(dt);
    UpdatePlayer(dt, buttons, prev_buttons);
    CheckInteractions();
}

void Game119Pitfall2::UpdateMechanisms(float dt) {
    // Vine swinging harmonic motion
    vine_angle_ = std::sin(state_timer_ * 2.6f) * 0.65f;

    // Hot Air Balloon vertical floating between y=5.0 and y=13.0
    balloon_y_ += balloon_dir_ * 2.2f * dt;
    if (balloon_y_ <= 5.0f) {
        balloon_y_ = 5.0f;
        balloon_dir_ = 1.0f; // Descend
    } else if (balloon_y_ >= 13.0f) {
        balloon_y_ = 13.0f;
        balloon_dir_ = -1.0f; // Ascend
    }
}

void Game119Pitfall2::UpdateHazards(float dt) {
    // Scorpion crawling back and forth on Floor 1
    hazards_[1].x += hazards_[1].vx * dt;
    if (hazards_[1].x <= 4.0f) {
        hazards_[1].x = 4.0f;
        hazards_[1].vx = std::abs(hazards_[1].vx);
    } else if (hazards_[1].x >= 11.5f) {
        hazards_[1].x = 11.5f;
        hazards_[1].vx = -std::abs(hazards_[1].vx);
    }

    // Bat flying in Cave
    hazards_[2].x += hazards_[2].vx * dt;
    hazards_[2].y = 10.5f + std::sin(state_timer_ * 4.0f) * 0.8f;
    if (hazards_[2].x <= 1.0f) {
        hazards_[2].x = 1.0f;
        hazards_[2].vx = std::abs(hazards_[2].vx);
    } else if (hazards_[2].x >= 14.5f) {
        hazards_[2].x = 14.5f;
        hazards_[2].vx = -std::abs(hazards_[2].vx);
    }
}

void Game119Pitfall2::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_spd = 4.2f;

    // 1. On Balloon
    if (on_balloon_) {
        px_ = balloon_x_;
        py_ = balloon_y_ + 0.6f;
        if ((buttons & (BTN_DOWN | BTN_B)) && !(prev_buttons & (BTN_DOWN | BTN_B))) {
            on_balloon_ = false;
        }
        return;
    }

    // 2. On Vine
    if (on_vine_) {
        float vine_len = 2.8f;
        px_ = vine_pivot_x_ + std::sin(vine_angle_) * vine_len;
        py_ = vine_pivot_y_ + std::cos(vine_angle_) * vine_len;

        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            on_vine_ = false;
            vy_ = -2.5f; // Jump off vine
        }
        return;
    }

    // 3. Ladder climbing check
    bool near_ladder_0 = (std::abs(px_ - 13.0f) < 0.7f && py_ >= 2.5f && py_ <= 8.5f);
    bool near_ladder_1 = (std::abs(px_ - 3.5f) < 0.7f && py_ >= 7.5f && py_ <= 13.5f);

    if (near_ladder_0 || near_ladder_1) {
        if (buttons & BTN_UP) {
            on_ladder_ = true;
            py_ -= move_spd * dt;
        } else if (buttons & BTN_DOWN) {
            on_ladder_ = true;
            py_ += move_spd * dt;
        } else if (on_ladder_) {
            vy_ = 0.0f;
        }
    } else {
        on_ladder_ = false;
    }

    if (!on_ladder_) {
        // Horizontal walk
        if (buttons & BTN_LEFT)  px_ -= move_spd * dt;
        if (buttons & BTN_RIGHT) px_ += move_spd * dt;

        // Jump
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A) && on_ground_) {
            vy_ = -4.5f;
            on_ground_ = false;
        }

        // Gravity
        vy_ += 14.0f * dt;
        py_ += vy_ * dt;

        // Floor collision snapping:
        // Floor 0: y=3.0 (except crocodile lagoon at x=6..9)
        // Floor 1: y=7.0
        // Floor 2: y=12.0
        if (py_ >= 3.0f && py_ <= 3.6f && vy_ >= 0.0f && !(px_ >= 6.0f && px_ <= 9.0f)) {
            py_ = 3.0f;
            vy_ = 0.0f;
            on_ground_ = true;
        } else if (py_ >= 7.0f && py_ <= 7.6f && vy_ >= 0.0f && !(px_ >= 12.0f && px_ <= 14.0f)) {
            py_ = 7.0f;
            vy_ = 0.0f;
            on_ground_ = true;
        } else if (py_ >= 12.0f && vy_ >= 0.0f) {
            py_ = 12.0f;
            vy_ = 0.0f;
            on_ground_ = true;
        } else {
            on_ground_ = false;
        }
    }

    px_ = std::max(1.0f, std::min(15.0f, px_));

    // Vine grab check
    if (!on_vine_ && py_ <= 4.0f && px_ >= 5.5f && px_ <= 9.5f) {
        float vx = vine_pivot_x_ + std::sin(vine_angle_) * 2.8f;
        float vy_coord = vine_pivot_y_ + std::cos(vine_angle_) * 2.8f;
        if (std::abs(px_ - vx) < 1.0f && std::abs(py_ - vy_coord) < 1.0f) {
            on_vine_ = true;
            on_ground_ = false;
        }
    }

    // Balloon grab check
    if (!on_balloon_ && std::abs(px_ - balloon_x_) < 1.0f && std::abs(py_ - balloon_y_) < 1.0f) {
        if (buttons & BTN_UP) {
            on_balloon_ = true;
            on_ground_ = false;
        }
    }
}

void Game119Pitfall2::CheckInteractions() {
    // 1. Treasures collection
    for (int i = 0; i < NUM_TREASURES; ++i) {
        if (!treasures_[i].collected) {
            float dx = std::abs(px_ - treasures_[i].x);
            float dy = std::abs(py_ - treasures_[i].y);
            if (dx < 0.9f && dy < 0.9f) {
                treasures_[i].collected = true;
                score_ += treasures_[i].value;
                treasures_collected_++;

                if (treasures_collected_ >= NUM_TREASURES) {
                    state_ = STATE_EXPEDITION_CLEAR;
                    state_timer_ = 0.0f;
                    score_ += 1000; // Quest Bonus!
                }
            }
        }
    }

    // 2. Red Checkpoint Cross activation at (5.0, 12.0)
    float cdx = std::abs(px_ - 5.0f);
    float cdy = std::abs(py_ - 12.0f);
    if (cdx < 0.9f && cdy < 0.9f && !checkpoint_active_) {
        checkpoint_active_ = true;
        checkpoint_x_ = 5.0f;
        checkpoint_y_ = 12.0f;
        score_ += 100;
    }

    // 3. Hazards collision -> Checkpoint Respawn!
    for (int i = 0; i < NUM_HAZARDS; ++i) {
        if (!hazards_[i].active) continue;
        if (hazards_[i].type == 2 && on_vine_) continue; // Vine swing safely clears the crocodile pit!
        float dx = std::abs(px_ - hazards_[i].x);
        float dy = std::abs(py_ - hazards_[i].y);
        if (dx < 0.8f && dy < 0.8f) {
            // Hazard touched!
            state_ = STATE_CHECKPOINT_RESPAWN;
            state_timer_ = 0.0f;
            score_ = std::max(0, score_ - 100);
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
            }
            break;
        }
    }
}

void Game119Pitfall2::Render(uint8_t* fb) {
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

    // 1. Cavern Cross-Section Platforms
    // Floor 0: Jungle surface with Crocodile lagoon
    for (int x = 0; x < 16; ++x) {
        if (x >= 6 && x <= 9) {
            set_pixel(x, 4, 30, 80, 220); // Deep blue crocodile water
        } else {
            set_pixel(x, 4, 40, 140, 50); // Jungle green turf
        }
    }

    // Floor 1: Middle Cavern ledge (y = 8, gap at x=12..14 for ladder)
    for (int x = 0; x < 16; ++x) {
        if (x < 12 || x > 14) {
            set_pixel(x, 8, 140, 90, 40); // Brown rock ledge
        }
    }

    // Floor 2: Deep Abyss (y = 13)
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 13, 90, 60, 40);
        set_pixel(x, 14, 50, 30, 20);
        set_pixel(x, 15, 30, 20, 10);
    }

    // Ladders (golden wooden rungs)
    for (int y = 4; y <= 8; ++y) set_pixel(13, y, 220, 180, 60);
    for (int y = 8; y <= 13; ++y) set_pixel(3, y, 220, 180, 60);

    // 2. Swinging Vine
    float vx = vine_pivot_x_ + std::sin(vine_angle_) * 2.8f;
    float vy = vine_pivot_y_ + std::cos(vine_angle_) * 2.8f;
    set_pixel(static_cast<int>(std::round(vine_pivot_x_)), static_cast<int>(std::round(vine_pivot_y_)), 80, 180, 60);
    set_pixel(static_cast<int>(std::round(vx)), static_cast<int>(std::round(vy)), 60, 220, 40);

    // 3. Floating Hot Air Balloon
    int bx = static_cast<int>(std::round(balloon_x_));
    int by = static_cast<int>(std::round(balloon_y_));
    set_pixel(bx, by - 1, 255, 60, 40); // Red balloon canopy
    set_pixel(bx - 1, by - 1, 255, 200, 30);
    set_pixel(bx + 1, by - 1, 255, 200, 30);
    set_pixel(bx, by, 180, 120, 60);    // Basket ring

    // 4. Treasures
    for (int i = 0; i < NUM_TREASURES; ++i) {
        if (treasures_[i].collected) continue;
        int tx = static_cast<int>(std::round(treasures_[i].x));
        int ty = static_cast<int>(std::round(treasures_[i].y));
        if (i == 0) set_pixel(tx, ty, 255, 220, 0); // Gold Ingot
        else if (i == 1) set_pixel(tx, ty, 220, 220, 255); // Silver Bar
        else set_pixel(tx, ty, 255, 140, 20); // Mayan Idol
    }

    // 5. Red Checkpoint Cross at (5, 12)
    if (checkpoint_active_) {
        set_pixel(5, 12, 255, 240, 80); // Activated bright golden cross
        set_pixel(5, 11, 255, 240, 80);
    } else {
        set_pixel(5, 12, 255, 40, 30); // Dormant red cross
        set_pixel(5, 11, 255, 40, 30);
    }

    // 6. Hazards
    // Crocodile at (7.5, 4.0)
    set_pixel(7, 4, 30, 160, 40);
    set_pixel(8, 4, 30, 160, 40);
    // Scorpion at hazards_[1]
    int sx = static_cast<int>(std::round(hazards_[1].x));
    set_pixel(sx, 7, 255, 80, 0); // Amber poison scorpion
    // Bat at hazards_[2]
    int btx = static_cast<int>(std::round(hazards_[2].x));
    int bty = static_cast<int>(std::round(hazards_[2].y));
    set_pixel(btx, bty, 200, 60, 255); // Purple vampire bat

    // 7. Pitfall Harry
    int px = static_cast<int>(std::round(px_));
    int py_int = static_cast<int>(std::round(py_));

    if (state_ == STATE_CHECKPOINT_RESPAWN) {
        // Teleportation flash
        set_pixel(px, py_int, 255, 255, 255);
        set_pixel(px, py_int - 1, 255, 220, 80);
    } else {
        set_pixel(px, py_int, 40, 120, 240); // Blue trousers
        set_pixel(px, py_int - 1, 255, 200, 140); // Head & Safari hat
        set_pixel(px, py_int - 2, 180, 140, 60); // Khaki explorer shirt
    }

    // 8. Lives HUD (Top row x=0..2)
    for (int l = 0; l < lives_; ++l) {
        set_pixel(l * 2, 0, 40, 220, 80);
    }
}

} // namespace arcade