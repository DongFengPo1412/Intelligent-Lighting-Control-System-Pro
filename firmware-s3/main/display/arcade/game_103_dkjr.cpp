#include "game_103_dkjr.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr float VINE_X[Game103DKJr::NUM_VINES] = {2.0f, 6.0f, 10.0f, 14.0f};

Game103DKJr::Game103DKJr() {
    Reset();
}

void Game103DKJr::Init() {
    Reset();
}

void Game103DKJr::Reset() {
    score_ = 0;
    lives_ = 3;
    ResetStage();
}

void Game103DKJr::ResetStage() {
    state_ = STATE_CLIMBING;
    state_timer_ = 0.0f;
    keys_inserted_ = 0;

    px_ = 2.0f;
    py_ = 13.0f;
    vx_ = 0.0f;
    vy_ = 0.0f;
    current_vine_ = 0;
    on_ground_ = true;
    gripping_two_vines_ = false;
    facing_ = 1;

    for (int k = 0; k < TOTAL_KEYS; ++k) {
        keys_unlocked_[k] = false;
    }

    // Spawn 2 fruits on vines 1 and 2
    fruits_[0].active = true;
    fruits_[0].vine_idx = 1;
    fruits_[0].x = VINE_X[1];
    fruits_[0].y = 5.0f;
    fruits_[0].falling = false;
    fruits_[0].vy = 0.0f;

    fruits_[1].active = true;
    fruits_[1].vine_idx = 2;
    fruits_[1].x = VINE_X[2];
    fruits_[1].y = 6.0f;
    fruits_[1].falling = false;
    fruits_[1].vy = 0.0f;

    // Spawn Snapjaws
    for (int i = 0; i < MAX_SNAPJAWS; ++i) {
        snapjaws_[i].active = true;
        snapjaws_[i].vine_idx = (i + 1) % NUM_VINES;
        snapjaws_[i].x = VINE_X[snapjaws_[i].vine_idx];
        snapjaws_[i].y = 2.5f + static_cast<float>(i * 3.5f);
        snapjaws_[i].vy = 2.2f + static_cast<float>(i) * 0.4f;
        snapjaws_[i].is_red = (i % 2 == 0);
    }
}

void Game103DKJr::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_FALL_DOWN) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                state_ = STATE_CLIMBING;
                state_timer_ = 0.0f;
                px_ = 2.0f;
                py_ = 13.0f;
                vx_ = 0.0f;
                vy_ = 0.0f;
                on_ground_ = true;
                gripping_two_vines_ = false;
            }
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.5f) {
            ResetStage();
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    UpdateJunior(dt, buttons, prev_buttons);
    UpdateSnapjaws(dt);
    UpdateFruits(dt);
    CheckCollisions();

    // Check cage completion
    if (keys_inserted_ >= TOTAL_KEYS && state_ != STATE_STAGE_CLEAR) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 2000;
    }
}

void Game103DKJr::UpdateJunior(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Jump Action (Button A)
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A) && (on_ground_ || !gripping_two_vines_)) {
        vy_ = -6.0f;
        if (buttons & BTN_LEFT) vx_ = -4.5f;
        else if (buttons & BTN_RIGHT) vx_ = 4.5f;
        else vx_ = static_cast<float>(facing_) * 3.0f;
        on_ground_ = false;
    }

    if (!on_ground_ && vy_ != 0.0f) {
        // Airborne jump physics
        py_ += vy_ * dt;
        px_ += vx_ * dt;
        vy_ += 14.0f * dt;

        // Catch onto vine midair (must be a different vine than launch vine)
        for (int v = 0; v < NUM_VINES; ++v) {
            if (v != current_vine_ && std::abs(px_ - VINE_X[v]) < 0.6f && py_ <= 13.0f && py_ >= 2.0f) {
                px_ = VINE_X[v];
                vx_ = 0.0f;
                vy_ = 0.0f;
                current_vine_ = v;
                gripping_two_vines_ = false;
                break;
            }
        }
        // Dual vine midpoint grab
        for (int v = 0; v < NUM_VINES - 1; ++v) {
            float mid_x = (VINE_X[v] + VINE_X[v + 1]) * 0.5f;
            if (std::abs(px_ - mid_x) < 0.6f && py_ <= 13.0f && py_ >= 2.0f) {
                px_ = mid_x;
                vx_ = 0.0f;
                vy_ = 0.0f;
                current_vine_ = v;
                gripping_two_vines_ = true;
                break;
            }
        }

        // Land on ground
        if (py_ >= 13.0f) {
            py_ = 13.0f;
            vy_ = 0.0f;
            vx_ = 0.0f;
            on_ground_ = true;
        }
    } else {
        // Ground walking or Vine Climbing
        if (py_ >= 13.0f) {
            on_ground_ = true;
            if (buttons & BTN_LEFT) {
                px_ = std::max(1.0f, px_ - 5.0f * dt);
                facing_ = -1;
            } else if (buttons & BTN_RIGHT) {
                px_ = std::min(15.0f, px_ + 5.0f * dt);
                facing_ = 1;
            }

            // Grab vine from ground
            if (buttons & BTN_UP) {
                for (int v = 0; v < NUM_VINES; ++v) {
                    if (std::abs(px_ - VINE_X[v]) < 0.8f) {
                        px_ = VINE_X[v];
                        current_vine_ = v;
                        on_ground_ = false;
                        gripping_two_vines_ = false;
                        py_ -= 0.5f;
                        break;
                    }
                }
            }
        } else {
            // On Vine(s)
            on_ground_ = false;

            // Lateral shift between single and dual vine grip
            if (buttons & BTN_LEFT) {
                facing_ = -1;
                if (gripping_two_vines_) {
                    // Shift to left single vine
                    px_ = VINE_X[current_vine_];
                    gripping_two_vines_ = false;
                } else if (current_vine_ > 0) {
                    // Shift to dual vine between current_vine_ - 1 and current_vine_
                    current_vine_--;
                    px_ = (VINE_X[current_vine_] + VINE_X[current_vine_ + 1]) * 0.5f;
                    gripping_two_vines_ = true;
                }
            } else if (buttons & BTN_RIGHT) {
                facing_ = 1;
                if (!gripping_two_vines_ && current_vine_ < NUM_VINES - 1) {
                    // Shift to dual vine to the right
                    px_ = (VINE_X[current_vine_] + VINE_X[current_vine_ + 1]) * 0.5f;
                    gripping_two_vines_ = true;
                } else if (gripping_two_vines_) {
                    // Shift to right single vine
                    current_vine_++;
                    px_ = VINE_X[current_vine_];
                    gripping_two_vines_ = false;
                }
            }

            // Climbing speed physics:
            // 2 Vines: UP is fast (6.0), DOWN is slow (2.5)
            // 1 Vine:  UP is slow (3.0), DOWN is fast (7.5)
            float climb_up_spd = gripping_two_vines_ ? 6.0f : 3.0f;
            float slide_down_spd = gripping_two_vines_ ? 2.5f : 7.5f;

            if (buttons & BTN_UP) {
                py_ = std::max(2.0f, py_ - climb_up_spd * dt);
            } else if (buttons & BTN_DOWN) {
                py_ += slide_down_spd * dt;
                if (py_ >= 13.0f) {
                    py_ = 13.0f;
                    on_ground_ = true;
                }
            }

            // Top key shackle insertion
            if (py_ <= 2.2f && !gripping_two_vines_) {
                if (!keys_unlocked_[current_vine_]) {
                    keys_unlocked_[current_vine_] = true;
                    keys_inserted_++;
                    score_ += 500;
                    py_ = 2.8f; // push back slightly
                }
            }
        }
    }
}

void Game103DKJr::UpdateSnapjaws(float dt) {
    for (int i = 0; i < MAX_SNAPJAWS; ++i) {
        if (!snapjaws_[i].active) {
            snapjaws_[i].active = true;
            snapjaws_[i].vine_idx = (i * 2 + 1) % NUM_VINES;
            snapjaws_[i].x = VINE_X[snapjaws_[i].vine_idx];
            snapjaws_[i].y = 1.5f;
            snapjaws_[i].vy = 2.4f;
            continue;
        }

        snapjaws_[i].y += snapjaws_[i].vy * dt;

        if (snapjaws_[i].y >= 14.0f) {
            if (snapjaws_[i].is_red) {
                // Red snapjaw drops off floor and respawns
                snapjaws_[i].active = false;
            } else {
                // Blue snapjaw reverses and climbs back up
                snapjaws_[i].vy = -std::abs(snapjaws_[i].vy);
            }
        } else if (snapjaws_[i].y <= 2.0f && snapjaws_[i].vy < 0.0f) {
            snapjaws_[i].vy = std::abs(snapjaws_[i].vy);
        }
    }
}

void Game103DKJr::UpdateFruits(float dt) {
    for (int f = 0; f < MAX_FRUITS; ++f) {
        if (!fruits_[f].active) continue;

        if (fruits_[f].falling) {
            fruits_[f].y += fruits_[f].vy * dt;
            fruits_[f].vy += 12.0f * dt;

            // Fruit crushes snapjaws along vine
            for (int s = 0; s < MAX_SNAPJAWS; ++s) {
                if (!snapjaws_[s].active) continue;
                if (std::abs(fruits_[f].x - snapjaws_[s].x) < 0.8f &&
                    std::abs(fruits_[f].y - snapjaws_[s].y) < 1.2f) {
                    snapjaws_[s].active = false;
                    score_ += 400;
                }
            }

            if (fruits_[f].y >= 14.0f) {
                fruits_[f].active = false;
            }
        } else {
            // Junior dislodges fruit by touching it
            if (std::abs(px_ - fruits_[f].x) < 1.0f && std::abs(py_ - fruits_[f].y) < 1.0f) {
                fruits_[f].falling = true;
                fruits_[f].vy = 2.0f;
                score_ += 100;
            }
        }
    }
}

void Game103DKJr::CheckCollisions() {
    // Snapjaw vs Junior
    for (int s = 0; s < MAX_SNAPJAWS; ++s) {
        if (!snapjaws_[s].active) continue;
        float dx = std::abs(px_ - snapjaws_[s].x);
        float dy = std::abs(py_ - snapjaws_[s].y);
        if (dx < 0.9f && dy < 1.0f) {
            state_ = STATE_FALL_DOWN;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game103DKJr::Render(uint8_t* fb) {
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

    // Mario's Cage Platform at y=1
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 1, 180, 50, 40); // Mario platform red girders
    }
    // Caged Papa Donkey Kong at x=7..9, y=0
    set_pixel(7, 0, 160, 80, 40);
    set_pixel(8, 0, 180, 100, 50);
    set_pixel(9, 0, 160, 80, 40);

    // Mario standing guard at top right x=13..14
    set_pixel(13, 0, 220, 20, 20); // Mario red cap
    set_pixel(14, 0, 20, 40, 220); // Mario blue overalls

    // 4 Key Locks / Chains
    for (int k = 0; k < TOTAL_KEYS; ++k) {
        int kx = static_cast<int>(VINE_X[k]);
        if (keys_unlocked_[k]) {
            set_pixel(kx, 2, 255, 220, 0); // Golden unlocked key
        } else {
            set_pixel(kx, 2, 100, 100, 120); // Gray shackle
        }
    }

    // 4 Climbing Vines (Green foliage ropes)
    for (int v = 0; v < NUM_VINES; ++v) {
        int vx = static_cast<int>(VINE_X[v]);
        for (int y = 3; y <= 13; ++y) {
            set_pixel(vx, y, 30, (y % 2 == 0 ? 180 : 130), 40);
        }
    }

    // Ground platform at y=14, 15
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 14, 80, 140, 40);
        set_pixel(x, 15, 60, 40, 20);
    }

    // Fruits
    for (int f = 0; f < MAX_FRUITS; ++f) {
        if (!fruits_[f].active) continue;
        int fx = static_cast<int>(std::round(fruits_[f].x));
        int fy = static_cast<int>(std::round(fruits_[f].y));
        set_pixel(fx, fy, 255, 200, 20); // Yellow banana / apple
        set_pixel(fx, fy - 1, 20, 200, 40); // Stem
    }

    // Snapjaws
    for (int s = 0; s < MAX_SNAPJAWS; ++s) {
        if (!snapjaws_[s].active) continue;
        int sx = static_cast<int>(std::round(snapjaws_[s].x));
        int sy = static_cast<int>(std::round(snapjaws_[s].y));
        if (snapjaws_[s].is_red) {
            set_pixel(sx, sy, 255, 50, 40); // Red Snapjaw
            set_pixel(sx, sy - 1, 255, 255, 255); // Teeth
        } else {
            set_pixel(sx, sy, 40, 120, 255); // Blue Snapjaw
            set_pixel(sx, sy - 1, 255, 255, 255); // Teeth
        }
    }

    // Junior (Little Ape)
    int jx = static_cast<int>(std::round(px_));
    int jy = static_cast<int>(std::round(py_));

    if (state_ == STATE_FALL_DOWN) {
        set_pixel(jx, jy, 255, 80, 40);
        set_pixel(jx, jy - 1, 255, 200, 0);
    } else {
        // Fur body
        set_pixel(jx, jy, 210, 120, 40);
        set_pixel(jx, jy - 1, 230, 150, 70); // Head & white bib
        if (gripping_two_vines_) {
            // Arms stretched wide gripping dual vines!
            set_pixel(jx - 1, jy, 210, 120, 40);
            set_pixel(jx + 1, jy, 210, 120, 40);
        } else {
            // One arm raised
            set_pixel(jx + facing_, jy - 1, 210, 120, 40);
        }
    }

    // Lives
    for (int l = 0; l < std::min(lives_, 3); ++l) {
        set_pixel(l, 0, 255, 200, 50);
    }
}

} // namespace arcade
